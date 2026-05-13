import vba_types
from typing import Any, Callable, TypeVar
from antlr4_vba.vbaParser import ParserRuleContext, vbaParser as Parser
from antlr4_vba.vbaParserVisitor import vbaParserVisitor as Visitor
from .symbol_table import (
    FunctionDefinition, LibraryDefinition, SymbolTable
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

    def visitFunctionDeclaration(                                  # noqa: N802
            self: T,
            ctx: Parser.FunctionDeclarationContext) -> Any:
        self.env_stack[-1][self.context[2]] = None
        if ctx.procedureBody() is not None:
            try:
                self.visit(ctx.procedureBody())
                return self.env_stack[-1][self.context[2]]
            except (ExitDoException, ExitForException, ExitPropertyException,
                    ExitSubException) as e:
                raise VbaCompileException(e.msg)
            except ExitFunctionException:
                return self.env_stack[-1][self.context[2]]

    def visitSubroutineDeclaration(                                # noqa: N802
            self: T,
            ctx: Parser.SubroutineDeclarationContext) -> None:
        if ctx.procedureBody() is not None:
            try:
                self.visit(ctx.procedureBody())
            except (ExitDoException, ExitForException, ExitPropertyException,
                    ExitFunctionException) as e:
                raise VbaCompileException(e.msg)
            except ExitSubException:
                pass

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
                defn = self.visit(ctx.lExpression())
                assert defn is not None
                if defn["type"] == "sub":
                    raise VbaCompileException("Expected Function or variable")
                else:
                    raise VbaException(f"Error On Line {ctx.start.line}, {var_name}")
        value = self.visit(ctx.expression())
        if isinstance(value, tuple):
            value = value[1]
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
                command = self.visit(ctx.simpleNameExpression())
                self.run_function(command, [])
            elif ctx.indexExpression() is not None:
                self.visit(ctx.indexExpression())
            else:
                raise Exception("Unsupported")
        else:
            try:
                command = self.visit(first_child)
            except VbaCompileException:
                raise VbaCompileException("Sub or Function not defined")
            args = []
            if ctx.argumentList() is not None:
                args = self.visit(ctx.argumentList())
            self.run_function(command, args)

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
        current_env[n] = start
        while (
                (step < vba_types.VBAInteger(0) and current_env[n] < end_value) !=
                (step >= vba_types.VBAInteger(0) and current_env[n] > end_value)
        ):
            if stmt.statementBlock() is not None:
                try:
                    self.visit(stmt.statementBlock())
                except ExitForException:
                    break
            current_env[n] += step

    def visitLocalVariableDeclaration(                             # noqa: N802
            self: T,
            ctx: Parser.LocalVariableDeclarationContext) -> None:
        current_env = self.env_stack[-1]
        if ctx.variableDeclarationList() is not None:
            dcl = self.visit(ctx.variableDeclarationList())
            if dcl is not None:
                current_env[dcl[0]] = dcl[1]

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

    def visitLiteralExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.LiteralExpressionContext) -> Any:
        return vba_types.literal_from_string(ctx.getText())

    def visitUntypedVariableDcl(                                   # noqa: N802
            self: T,
            ctx: Parser.UntypedVariableDclContext) -> tuple[str, Any]:
        name = ctx.ambiguousIdentifier().getText().lower()
        type = self.visit(ctx.asClause())
        return (name, type)

    def visitArithmeticExpression(                                 # noqa: N802
            self: T,
            ctx: Parser.ArithmeticExpressionContext) -> Any:
        left_child = ctx.getChild(0)
        assert left_child is not None
        left = self.visit(left_child)
        if isinstance(left, tuple):
            left = left[1]
        assert left is not None
        last = ctx.getChildCount() - 1
        right_child = ctx.getChild(last)
        assert right_child is not None
        right = self.visit(right_child)
        if isinstance(right, tuple):
            right = right[1]
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
        if isinstance(value, tuple):
            value = value[1]
        return -1 * value

    def visitParenthesizedExpress(                                 # noqa: N802
            self: T,
            ctx: Parser.ParenthesizedExpressContext
    ) -> Any:
        value = self.visit(ctx.parenthesizedExpression().expression())
        assert value is not None
        if isinstance(value, tuple):
            value = value[1]
        return value

    def visitRelationExpression(                                   # noqa: N802
            self: T,
            ctx: Parser.RelationExpressionContext
    ) -> bool:
        left_child = ctx.getChild(0)
        assert left_child is not None
        left = self.visit(left_child)
        if isinstance(left, tuple):
            left = left[1]
        last = ctx.getChildCount() - 1
        right_child = ctx.getChild(last)
        assert right_child is not None
        right = self.visit(right_child)
        if isinstance(right, tuple):
            right = right[1]
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
        if isinstance(left, tuple):
            left = left[1]
        assert right is not None
        if isinstance(right, tuple):
            right = right[1]
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
        if l_express["type"] == "project":
            if name in l_express["modules"]:
                return l_express["modules"][name]
            for mod in l_express["modules"].values():
                if name in mod["functions"]:
                    return mod["functions"][name]
            raise VbaCompileException("Method or data member not found")
        if l_express["type"] == "module":
            if name in l_express["functions"]:
                return l_express["functions"][name]
            raise VbaCompileException("Method or data member not found")
        raise VbaException("Not Supported")

    # Can be an Array() or a function call because expressions are assigned
    # in Let Statements
    def visitIndexExpress(                                       # noqa: N802
            self: T,
            ctx: Parser.IndexExpressContext) -> Any:
        defn = self.visit(ctx.lExpression())
        assert defn is not None
        if isinstance(defn, tuple):
            defn = defn[0]
        if isinstance(defn, dict):
            if defn["type"] == "sub":
                raise VbaCompileException("Expected Function or variable")
            if defn["type"] == "module":
                msg = "Expected variable or procedure, not module"
                raise VbaCompileException(msg)
            if defn["type"] == "project":
                msg = "Expected variable or procedure, not project"
                raise VbaCompileException(msg)

        args: list[Any] = []
        if ctx.argumentList() is not None:
            args = self.visit(ctx.argumentList())
        if isinstance(defn, Callable):
            return vba_types.array.VBAArray(*args)
        if isinstance(defn,  vba_types.array.VBAArray):
            return defn[int(args[0])]
        return self.run_function(defn, args)

    # Only used within implicit call statement.
    # Must be a Function or Sub
    def visitIndexExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.IndexExpressionContext) -> None:
        defn = self.visit(ctx.lExpression())
        assert defn is not None
        if isinstance(defn, tuple):
            defn = defn[0]
        if defn["type"] == "module":
            msg = "Expected variable or procedure, not module"
            raise VbaCompileException(msg)
        if defn["type"] == "project":
            msg = "Expected variable or procedure, not project"
            raise VbaCompileException(msg)

        args: list[Any] = []
        if ctx.argumentList() is not None:
            args = self.visit(ctx.argumentList())
        return self.run_function(defn, args)

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
            return self.table.definitions[name]
        if name in self.table.library_definitions:
            return self.table.library_definitions[name]
        for lib_proj in self.table.library_definitions.values():
            if name in lib_proj["modules"]:
                return lib_proj["modules"][name]
        for lib_proj in self.table.library_definitions.values():
            if "classes" in lib_proj and name in lib_proj["classes"]:
                return lib_proj["classes"][name]
        for proj in self.table.definitions.values():
            if name in proj["modules"]:
                return proj["modules"][name]
        raise VbaCompileException(f"Method or data member not found {name}")

    def visitSpecialForm(                                          # noqa: N802
            self: T,
            ctx: Parser.SpecialFormContext) -> Callable:
        # name = ctx.getText().lower()
        # if name == "array":
        return getattr(vba_types.array.VBAArray, "__init__")

    def visitTypeSpec(                                             # noqa: N802
            self: T,
            ctx: Parser.TypeSpecContext) -> Any:
        if ctx.typeExpression().builtinType() is not None:
            type_name = ctx.typeExpression().builtinType().getText().lower()
            return self._new_type_from_string(type_name)

    def run_function(self: T,
                     defn: FunctionDefinition | LibraryDefinition,
                     args: list[Any]) -> Any:
        ctx = defn["handle"]
        if (
                isinstance(ctx, Parser.FunctionDeclarationContext) or
                isinstance(ctx, Parser.SubroutineDeclarationContext)
        ):
            previous_context = self.context.copy()
            self.context = [defn["project"], defn["module"], defn["name"]]
            current_env = {}
            min = 0
            max = len(defn["params"])
            for param in defn["params"]:
                if not param["optional"]:
                    min += 1
            if len(args) < min:
                raise VbaCompileException("Argument not optional")
            if len(args) > max:
                msg = ("Wrong number of arguments or invalid property"
                       " assignment")
                raise VbaCompileException(msg)
            i = 0
            for param in defn["params"]:
                if not param["optional"]:
                    current_env[param["name"]] = args[i]
                else:
                    if len(args) > i:
                        current_env[param["name"]] = args[i]
                i += 1
            self.env_stack.append(current_env)
            try:
                output = self.visit(ctx)
            finally:
                self.env_stack.pop()
                self.context = previous_context
        elif ctx is not None:
            min = 0
            max = len(defn["params"])
            for param in defn["params"]:
                if not param["optional"]:
                    min += 1
            if len(args) < min:
                raise VbaCompileException("Argument not optional")
            if len(args) > max:
                msg = ("Wrong number of arguments or invalid property"
                       " assignment")
                raise VbaCompileException(msg)
            output = ctx(*args)
        else:
            raise Exception("Unknown Function Type")
        if defn["type"] == "function":
            return output

    def _find_function_in_definition(
            self: T, command: str, cur_module: str
    ) -> FunctionDefinition | LibraryDefinition:
        for proj in self.table.definitions.values():
            if (
                    cur_module != "" and
                    cur_module in proj["modules"] and
                    command in proj["modules"][cur_module]["functions"]
            ):
                return proj["modules"][cur_module]["functions"][command]
        for key, proj in self.table.definitions.items():
            if key == command:
                msg = "Expected variable or procedure, not project"
                raise VbaCompileException(msg)
            if command in proj["modules"]:
                msg = "Expected variable or procedure, not module"
                raise VbaCompileException(msg)
            for mod in proj["modules"].values():
                if command in mod["functions"]:
                    return mod["functions"][command]
        for key, lib_proj in self.table.library_definitions.items():
            if key == command:
                msg = "Expected variable or procedure, not project"
                raise VbaCompileException(msg)
            if command in lib_proj["modules"]:
                msg = "Expected variable or procedure, not module"
                raise VbaCompileException(msg)
            for lib_mod in lib_proj["modules"].values():
                if command in lib_mod["functions"]:
                    return lib_mod["functions"][command]
        raise VbaCompileException("Sub or Function not defined")

    def _function_in_module(self: T, module: str, function: str) -> bool:
        return function in self.table.definitions[module]

    def _function_in_project(self: T, function: str) -> bool:
        """
        Does a function exist in any project.
        """
        for project in self.table.definitions.values():
            for mod in project["modules"].values():
                if function in mod["functions"]:
                    return True
        for libproject in self.table.library_definitions.values():
            for libmod in libproject["modules"].values():
                if function in libmod["functions"]:
                    return True
        return False

    @staticmethod
    def _new_type_from_string(type_name: str) -> Any:
        if type_name == "integer":
            return vba_types.VBAInteger()
        if type_name == "variant":
            return vba_types.VBAEmpty()
