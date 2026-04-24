from typing import Any, TypeVar
from antlr4_vba.vbaParser import ParserRuleContext, vbaParser as Parser
from antlr4_vba.vbaParserVisitor import vbaParserVisitor as Visitor
from vba_stdlib.literal_factory import literal_from_string
from .symbol_table import SymbolTable
from .Exceptions.vba_compile_exception import VbaCompileException


T = TypeVar('T', bound='VbaVisitor')


class VbaVisitor(Visitor):

    def __init__(self: T, table: SymbolTable) -> None:
        self.table = table
        self.env_stack: list[dict[str, Any]] = []

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
        value = self.visit(ctx.expression())
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
                self.execute_function(command, [], False)
            elif ctx.indexExpression() is not None:
                self.visit(ctx.indexExpression())
            else:
                raise Exception("Unsupported")
        else:
            command = first_child.getText().lower()
            args = []
            if ctx.argumentList() is not None:
                args = self.visit(ctx.argumentList())
            self.execute_function(command, args, False)

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
        n = self.visit(ctx.forClause().boundVariableExpression())
        start = self.visit(ctx.forClause().startValue())
        end = self.visit(ctx.forClause().endValue())
        step = 1
        if ctx.forClause().stepClause() os not None:
            step = self.visit(ctx.forClause().stepClause().stepIncrement())
        for i in range(start, end, step):
            # set n to i
            # visit internals
            pass

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
        return literal_from_string(ctx.getText())

    def visitAmbiguousIdentifier(                                  # noqa: N802
            self: T,
            ctx: Parser.AmbiguousIdentifierContext) -> Any:
        current_env = self.env_stack[-1]
        var_name = ctx.getText().lower()
        return current_env[var_name]

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

    # Can be an Array() or a function call because expressions are assigned
    # in Let Statements
    def visitIndexExpress(                                       # noqa: N802
            self: T,
            ctx: Parser.IndexExpressContext) -> Any:
        return self._visit_shared_index_expression(ctx, True)

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
        command_child = ctx.getChild(0)
        assert command_child is not None
        command = command_child.getText().lower()
        args = []
        if ctx.argumentList() is not None:
            args = self.visit(ctx.argumentList())
        return self.execute_function(command, args, no_sub)

    def execute_function(self: T, command: str,
                         args: list, no_sub: bool) -> Any:
        command = command.lower()
        if command == "array":
            return args
        if (
            command not in self.table.definitions and
            command not in self.table.library_definitions
        ):
            raise VbaCompileException("Sub or Function not defined")
        if command not in self.table.definitions:
            lib_def = self.table.library_definitions[command]
            if no_sub and lib_def["type"] == "sub":
                raise VbaCompileException("Unexpected Function or variable")
            try:
                output = lib_def["handle"](*args)
            except Exception as e:
                if str(e) != "":
                    raise VbaCompileException("Argument not optional")
            return output
        else:
            mod_def = self.table.definitions[command]
            if no_sub and mod_def["type"] == "sub":
                raise VbaCompileException("Unexpected Function or variable")
            current_env = {
                command: None
            }
            i = 0
            for param in mod_def["params"]:
                if not param["optional"]:
                    current_env[param["name"]] = args[i]
                    i += 1
            self.env_stack.append(current_env)
            ctx = mod_def["handle"]
            if ctx is not None:
                self.visitChildren(ctx)
            output = current_env[command]
            self.env_stack.pop()
            return output
