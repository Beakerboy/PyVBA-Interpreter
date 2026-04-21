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

    @staticmethod
    def _get_op(ctx: ParserRuleContext) -> str:
        i = 1
        if isinstance(ctx.getChild(1), Parser.WscContext):
            i = 2
        child = ctx.getChild(i)
        assert child is not None
        return child.symbol.text

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
                if command not in self.table.definitions:
                    raise VbaCompileException("Sub or Function not defined")
                func_info = self.table.definitions.get(command)
                if func_info and func_info["type"] == "builtin":
                    func_info["handle"]
                else:
                    self.visit(func_info["handle"])
            elif ctx.indexExpression() is not None:
                self.visit(ctx.indexExpression())
        else:
            command = first_child.getText().lower()
            if ctx.argumentList() is not None:
                args = self.visit(ctx.argumentList())
            if command not in self.table.definitions:
                raise VbaCompileException("Sub or Function not defined")
            func_info = self.table.definitions.get(command)
            if func_info and func_info["type"] == "builtin":
                func_info["handle"](*args)

    def visitArgumentList(                                         # noqa: N802
            self: T,
            ctx: Parser.ArgumentListContext) -> list[Any]:
        args = []
        if ctx.children is not None:
            for child in ctx.children:
                if child is not None:
                    args += [self.visit(child)]
        return args

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
    def vistIndexExpress(                                       # noqa: N802
            self: T,
            ctx: Parser.IndexExpressContext) -> Any:
        raise VbaCompileException("")
        return self._visit_shared_index_expression(ctx)

    # Only used within implicit call statement.
    # Must be a Function or Sub
    def vistIndexExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.IndexExpressionContext) -> Any:
        return self._visit_shared_index_expression(ctx)

    def _visit_shared_index_expression(
            self: T,
            ctx: (
                Parser.IndexExpressContext |
                Parser.IndexExpressionContext
            )) -> Any:
        command_child = ctx.getChild(0)
        assert command_child is not None
        command = command_child.getText().lower()
        args = []
        if ctx.argumentList() is not None:
            args = self.visit(ctx.argumentList())
        if command not in self.table.definitions:
            raise VbaCompileException("Sub or Function not defined")
        definition = self.table.definitions[command]
        if definition["type"] == "sub":
            raise VbaCompileException("Unexpected Function or variable")
        func_info = self.table.definitions.get(command)
        if func_info and func_info["type"] == "builtin":
            func_info["handle"](*args)
        else:
            self.visit(func_info["handle"])
