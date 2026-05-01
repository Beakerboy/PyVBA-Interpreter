from typing import Any, TypeVar
from antlr4_vba.vbaParser import ParserRuleContext, vbaParser as Parser
from antlr4_vba.vbaParserVisitor import vbaParserVisitor as Visitor
from vba_stdlib.literal_factory import literal_from_string
from .symbol_table import (
    FunctionDefinition, FunctionType, LibModuleDefinition, LibraryDefinition,
    ModuleDefinition, SymbolTable
)
from .Exceptions.vba_compile_exception import VbaCompileException
from .Exceptions.exit_do_exception import ExitDoException
from .Exceptions.exit_for_exception import ExitForException
from .Exceptions.exit_function_exception import ExitFunctionException
from .Exceptions.exit_property_exception import ExitPropertyException
from .Exceptions.exit_sub_exception import ExitSubException
from .Exceptions.vba_exception import VbaException


T = TypeVar('T', bound='VbaVisitor')


class VbaVisitor(Visitor):

    def __init__(self: T, table: SymbolTable) -> None:
        self.table = table

        # Instead of a list, this could probably be chaged to just
        # a dictionary of the current scope. The previous scope could
        # be retained like done with context. In theory this could
        # help with debugging.
        self.env_stack: list[dict[str, Any]] = []

        # The current project, module, and function context
        self.context = ["vbaproject", "", ""]

    @staticmethod
    def _get_op(ctx: ParserRuleContext) -> str:
        i = 1
        if isinstance(ctx.getChild(1), Parser.WscContext):
            i = 2
        child = ctx.getChild(i)
        assert child is not None
        return child.symbol.text

    def visitLetStatement(                                         # noqa: N802
            self: T,
            ctx: Parser.LetStatementContext) -> None:
        current_env = self.env_stack[-1]
        var_name = ctx.lExpression().getText().lower()
        if var_name not in current_env:
            if self._function_in_project(var_name):
                defn = self._find_function_in_definition(var_name, "")
                if defn["type"] == FunctionType.SUB:
                    raise VbaCompileException("Expected Function or variable")
                else:
                    raise VbaException()
        value = self.visit(ctx.expression())
        if isinstance(value, dict):
            raise VbaCompileException("Expected Function or variable")
        current_env[var_name] = value

    def visitCallStatement(                                        # noqa: N802
            self: T,
            ctx: Parser.CallStatementContext) -> None:
        command = ''
        # Either CALL or simpleNameExpression
        first_child = ctx.getChild(0)
        assert first_child is not None
        if first_child.getText().lower() == "call":
            # If no arguments, then it's just a simple name expression
            if ctx.simpleNameExpression() is not None:
                command = ctx.simpleNameExpression().getText().lower()
                self.execute_function(command, [], "", False)
            elif ctx.indexExpression() is not None:
                self.visit(ctx.indexExpression())
            else:
                raise Exception("Unsupported")
        else:
            command = first_child.getText().lower()
            args = []
            if ctx.argumentList() is not None:
                args = self.visit(ctx.argumentList())
            self.execute_function(command, args, "", False)

    def visitDoStatement(                                          # noqa: N802
            self: T,
            ctx: Parser.DoStatementContext) -> None:
        condition = True
        run_while = False
        if ctx.conditionClause(0) is not None:
            if ctx.conditionClause(1) is not None:
                raise VbaCompileException("Loop without Do")
            cond_clau = ctx.conditionClause(0)
            cond = self.visit(cond_clau.getChild(0).booleanExpression())
            condition = cond == (cond_clau.whileClause() is not None)
            run_while = True
        elif ctx.conditionClause(1) is not None:
            cond_clau = ctx.conditionClause(1)
            run_while = True
        else:
            while True:
                if ctx.statementBlock() is not None:
                    try:
                        self.visit(ctx.statementBlock())
                    except ExitDoException:
                        break

        if run_while:
            if cond_clau.whileClause() is not None:
                type = "while"
            else:
                type = "until"
            while condition:
                if ctx.statementBlock() is not None:
                    try:
                        self.visit(ctx.statementBlock())
                    except ExitDoException:
                        break
                cond = self.visit(cond_clau.getChild(0).booleanExpression())
                condition = cond == (type == "while")

    def visitIfStatement(                                          # noqa: N802
            self: T,
            ctx: Parser.IfStatementContext) -> None:
        condition = self.visit(ctx.booleanExpression())
        if condition:
            if ctx.statementBlock() is not None:
                self.visit(ctx.statementBlock())
        else:
            if ctx.elseBlock() is not None:
                self.visit(ctx.elseBlock().statementBlock())

    def visitSingleLineIfStatement(                                # noqa: N802
            self: T,
            ctx: Parser.SingleLineIfStatementContext) -> None:
        stmt = ctx.getChild(0)
        assert stmt is not None
        condition = self.visit(stmt.booleanExpression())
        if condition:
            if hasattr(type(stmt), "listOrLabel"):
                self.visit(stmt.listOrLabel())
        else:
            if stmt.singleLineElseClause() is not None:
                self.visit(stmt.singleLineElseClause())

    def visitWhileStatement(                                       # noqa: N802
            self: T,
            ctx: Parser.WhileStatementContext) -> None:
        condition = self.visit(ctx.booleanExpression())
        while condition:
            if ctx.statementBlock() is not None:
                self.visit(ctx.statementBlock())
            condition = self.visit(ctx.booleanExpression())

    def visitForStatement(                                         # noqa: N802
            self: T,
            ctx: Parser.ForStatementContext) -> None:
        if ctx.explicitForStatement() is None:
            stmt = ctx.simpleForStatement()
        else:
            stmt = ctx.explicitForStatement()
        clause = stmt.forClause()
        n = clause.boundVariableExpression().getText().lower()
        start = self.visit(clause.startValue())
        end_value = self.visit(clause.endValue())
        assert end_value is not None
        stop = end_value + 1
        step = 1
        if clause.stepClause() is not None:
            step = self.visit(clause.stepClause().stepIncrement())
        current_env = self.env_stack[-1]
        self.raise_for_except = False
        for i in range(start, stop, step):
            current_env[n] = i
            if stmt.statementBlock() is not None:
                try:
                    self.visit(stmt.statementBlock())
                except ExitForException:
                    break

    def visitArgumentList(                                         # noqa: N802
            self: T,
            ctx: Parser.ArgumentListContext) -> list[Any]:
        args = []
        if ctx.positionalOrNamedArgumentList() is not None:
            for child in ctx.positionalOrNamedArgumentList().children:
                if not (
                    isinstance(child, Parser.WscContext) or
                    child.getText() == ','
                ):
                    args += [self.visit(child)]
        return args

    def visitExpression(                                           # noqa: N802
            self: T,
            ctx: Parser.ExpressionContext) -> Any:
        """
        An LExpression can still be undecided if it's a function or value. By
        The time it rolls up to expression, it's been evaluated.
        """
        result = self.visitChildren(ctx)
        if isinstance(result, tuple):
            return result[1]

    def visitLiteralExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.LiteralExpressionContext) -> Any:
        return literal_from_string(ctx.getText())

    def visitArithmeticExpression(                                 # noqa: N802
            self: T,
            ctx: Parser.ArithmeticExpressionContext) -> Any:
        left_child = ctx.getChild(0)
        assert left_child is not None
        left = self.visit(left_child)
        assert left is not None
        last = ctx.getChildCount() - 1
        right_child = ctx.getChild(last)
        assert right_child is not None
        right = self.visit(right_child)
        assert right is not None
        op = self._get_op(ctx)
        if op == '*':
            return left * right
        elif op == '/':
            return left / right
        elif op == '+':
            return left + right
        elif op == '-':
            return left - right
        elif op == '^':
            return left ** right
        elif op.upper() == 'MOD':
            return left % right
        else:  # op == '\\':
            return left // right

    def visitExitDoStatement(                                      # noqa: N802
            self: T,
            ctx: Parser.ExitDoStatementContext) -> None:
        raise ExitDoException()

    def visitExitForStatement(                                     # noqa: N802
            self: T,
            ctx: Parser.ExitForStatementContext) -> None:
        raise ExitForException()

    def visitExitFunctionStatement(                                # noqa: N802
            self: T,
            ctx: Parser.ExitFunctionStatementContext) -> None:
        raise ExitFunctionException()

    def visitExitPropertyStatement(                                # noqa: N802
            self: T,
            ctx: Parser.ExitPropertyStatementContext) -> None:
        raise ExitPropertyException()

    def visitExitSubStatement(                                     # noqa: N802
            self: T,
            ctx: Parser.ExitSubStatementContext) -> None:
        raise ExitSubException()

    def visitUnaryMinusExpression(                                 # noqa: N802
            self: T,
            ctx: Parser.UnaryMinusExpressionContext) -> int | float:
        value = self.visit(ctx.expression())
        assert value is not None
        return -1 * value

    def visitRelationExpression(                                   # noqa: N802
            self: T,
            ctx: Parser.RelationExpressionContext
    ) -> bool:
        left_child = ctx.getChild(0)
        assert left_child is not None
        left = self.visit(left_child)
        last = ctx.getChildCount() - 1
        right_child = ctx.getChild(last)
        assert right_child is not None
        right = self.visit(right_child)
        assert left is not None
        assert right is not None
        op = self._get_op(ctx)
        if op == '<':
            return left < right
        elif op == '>':
            return left > right
        elif op == '=':
            return left == right
        elif op == '<>' or op == '><':
            return left != right
        elif op == '>=' or op == '=>':
            return left >= right
        elif op == '<=' or op == '=<':
            return left <= right
        else:  # LIKE
            raise Exception("Currently Unsupported")

    def visitBooleanExpress(                                    # noqa: N802
            self: T,
            ctx: Parser.BooleanExpressContext) -> bool:
        left_child = ctx.getChild(0)
        assert left_child is not None
        left = self.visit(left_child)
        last = ctx.getChildCount() - 1
        right_child = ctx.getChild(last)
        assert right_child is not None
        right = self.visit(right_child)
        assert left is not None
        assert right is not None
        op = self._get_op(ctx).upper()
        if op == "AND":
            return left and right
        elif op == "OR":
            return left or right
        elif op == "XOR":
            return left != right
        elif op == "IMP":
            return not left or right
        else:  # op == "EQV":
            return left == right

    def visitMemberAccessExpress(                                # noqa N802
            self: T,
            ctx: Parser.MemberAccessExpressContext
    ) -> FunctionDefinition | LibraryDefinition:
        l_express = self.visit(ctx.lExpression())
        assert l_express is not None
        name = ctx.unrestrictedName().getText().lower()
        if l_express["type"] == FunctionType.MODULE:
            if name in l_express["functions"]:
                return l_express["functions"][name]
            raise VbaCompileException("Method or data member not found")

    # Can be an Array() or a function call because expressions are assigned
    # in Let Statements
    def visitIndexExpress(                                       # noqa: N802
            self: T,
            ctx: Parser.IndexExpressContext) -> Any:
        defn = self.visit(ctx.lExpression())
        assert defn is not None
        if isinstance(defn, tuple):
            defn = defn[0]
        if defn["type"] == FunctionType.SUB:
            raise VbaCompileException("Expected Function or variable")
        if defn["type"] == FunctionType.MODULE:
            msg = "Expected variable or procedure, not module"
            raise VbaCompileException(msg)
        args: list[Any] = []
        if ctx.argumentList() is not None:
            args = self.visit(ctx.argumentList())
        return self.run_function(defn, args)

    # Only used within implicit call statement.
    # Must be a Function or Sub
    def visitIndexExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.IndexExpressionContext) -> None:
        self._visit_shared_index_expression(ctx)

    def _visit_shared_index_expression(
            self: T,
            ctx: (
                Parser.IndexExpressContext |
                Parser.IndexExpressionContext
            ),
            no_sub: bool = False) -> Any:
        module = ""
        if hasattr(ctx.lExpression(), "memberAccessExpress"):
            raise Exception()
        l_express = ctx.lExpression()
        if (
                hasattr(type(l_express), "unrestrictedName")
        ):
            command = l_express.unrestrictedName().getText().lower()
            module = self.visitLExpress(l_express.lExpression())["name"]
        else:
            command = l_express.getText().lower()
        args: list[Any] = []
        if ctx.argumentList() is not None:
            args = self.visit(ctx.argumentList())
        return self.execute_function(command, args, module, no_sub)

    def visitAmbiguousIdentifier(                                  # noqa: N802
            self: T,
            ctx: Parser.AmbiguousIdentifierContext) -> Any:
        """
        If a function is calling itself, there will be a function and a value
        in the current scope. The let statement will need to decide if it wants
        to use the value or call the function.
        Function Foo(I)
            Foo = 1
            Bar = Foo
            ' Versus
            Baz = Foo(I - 1)
        End Function

        An indexExpression will choose the function, while a the letStatement
        would choose the value.
        """

        current_env = self.env_stack[-1]
        name = ctx.getText().lower()
        if name in current_env:
            if self._function_in_project(name):
                return (
                    self._find_function_in_definition(name, self.context[1]),
                    current_env[name]
                )
            return current_env[name]

        if self._function_in_project(name):
            return self._find_function_in_definition(name, self.context[1])
        if name in self.table.definitions:
            record = self.table.definitions[name]
            return record
        if name in self.table.library_definitions:
            lib_record = self.table.library_definitions[name]
            return lib_record
        raise VbaCompileException("Method or data member not found")

    def execute_function(self: T, command: str,
                         args: list[Any], module: str = "",
                         no_sub: bool = True) -> Any:
        command = command.lower()
        if command == "array":
            return args
        mod_defn: ModuleDefinition | LibModuleDefinition
        if module != "":
            if module in self.table.definitions:
                mod_defn = self.table.definitions[module]
            elif module in self.table.library_definitions:
                mod_defn = self.table.library_definitions[module]
            else:
                raise VbaException()
            if command in mod_defn["functions"]:
                defn = mod_defn["functions"][command]
            else:
                raise VbaCompileException("Method or data member not found")
        else:
            defn = self._find_function_in_definition(command, self.context[1])
            module = defn["module"]

        return self.run_function(defn, args)

    def run_function(self: T,
                     defn: FunctionDefinition | LibraryDefinition,
                     args: list[Any]) -> Any:
        previous_context = self.context
        self.context[1] = defn["module"]
        self.context[2] = defn["name"]

        ctx = defn["handle"]
        if isinstance(ctx, Parser.ProcedureBodyContext):
            current_env = {}
            i = 0
            for param in defn["params"]:
                if not param["optional"]:
                    current_env[param["name"]] = args[i]
                else:
                    if len(args) > i:
                        current_env[param["name"]] = args[i]
                i += 1
            self.env_stack.append(current_env)
            if defn["type"] == FunctionType.FUNCTION:
                current_env[defn["name"]] = None
            try:
                self.visitChildren(ctx)
            except ExitDoException as e:
                raise VbaCompileException(e.msg)
            except ExitForException as e:
                raise VbaCompileException(e.msg)
            except ExitFunctionException as e:
                if (
                        defn["type"] == FunctionType.SUB or
                        defn["type"] == FunctionType.PROPERTY
                ):
                    raise VbaCompileException(e.msg)
            except ExitPropertyException as e:
                if (
                        defn["type"] == FunctionType.FUNCTION or
                        defn["type"] == FunctionType.SUB
                ):
                    raise VbaCompileException(e.msg)
            except ExitSubException as e:
                if (
                        defn["type"] == FunctionType.FUNCTION or
                        defn["type"] == FunctionType.PROPERTY
                ):
                    raise VbaCompileException(e.msg)
            output = current_env[defn["name"]]
            self.env_stack.pop()
            self.context = previous_context
        elif ctx is not None:
            try:
                output = ctx(*args)
            except Exception as e:
                if str(e) != "":
                    raise VbaCompileException("Argument not optional")
        else:
            output = None
        if defn["type"] == FunctionType.FUNCTION:
            return output

    def _find_function_in_definition(
            self: T, command: str, cur_module: str
    ) -> FunctionDefinition | LibraryDefinition:
        if cur_module != "" and command in self.table.definitions[cur_module]:
            return self.table.definitions[cur_module]["functions"][command]
        for _, mod in self.table.definitions.items():
            if command in mod["functions"]:
                return mod["functions"][command]
        for _, lib_mod in self.table.library_definitions.items():
            if command in lib_mod["functions"]:
                return lib_mod["functions"][command]
        if command in self.table.definitions:
            msg = "Expected variable or procedure, not module"
            raise VbaCompileException(msg)
            # Need one more level, project, module, function.
            msg = "Expected variable or procedure, not project"
            raise VbaCompileException(msg)

        raise VbaCompileException("Sub or Function not defined")

    def _function_in_module(self: T, module: str, function: str) -> bool:
        return function in self.table.definitions[module]

    def _function_in_project(self: T, function: str) -> bool:
        for key, mod in self.table.definitions.items():
            if function in mod["functions"]:
                return True
        return False
