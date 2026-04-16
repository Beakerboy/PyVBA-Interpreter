from typing import Any, TypeVar
from antlr4.ParserRuleContext import ParserRuleContext
from antlr4_vba.vbaParser import vbaParser as Parser
from antlr4_vba.vbaParserVisitor import vbaParserVisitor as Visitor
from vba_stdlib.literal_factory import literal_from_string


T = TypeVar('T', bound='VbaVisitor')


class VbaVisitor(Visitor):

    def __init__(self: T) -> None:
        self.functions: dict[str, 'ParserRuleContext'] = {}

    def visitFunctionDeclaration(                                  # noqa: N802
            self: T,
            ctx: Parser.FunctionDeclarationContext) -> None:
        func_name = self.visit(ctx.functionName())
        self.functions[func_name] = ctx

    def visitFunctionName(                                         # noqa: N802
            self: T,
            ctx: Parser.FunctionNameContext) -> str:
        return ctx.getText()

    def visitCallStatement(                                        # noqa: N802
            self: T,
            ctx: Parser.CallStatementContext) -> None:
        command = ''
        if ctx.getChild(0).getText().lower() == "call":
            command = ctx.indexExpression().lExpression().getText()
            args = self.visit(ctx.indexExpression().argumentList())
        else:
            command = ctx.getChild(0).getText()
            args = self.visit(ctx.argumentList())
        if command.lower() == "msgbox":
            print(args[0])

    def visitArgumentList(                                         # noqa: N802
            self: T,
            ctx: Parser.ArgumentListContext) -> list[Any]:
        args = []
        for i in range(ctx.getChildCount()):
            args += [self.visit(ctx.getChild(i))]
        return args

    def visitLiteralExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.LiteralExpressionContext) -> Any:
        return literal_from_string(ctx.getText())
