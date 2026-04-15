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
        command = ctx.getChild(0).getText()
        args = []
        for i in range(ctx.getChildCount()):
            args += [self.visit(ctx.getChild(i))]
        if command.lower() == "msgbox":
            print(args[0])

    def visitLiteralExpression(                                    # noqa: N802
            self: T,
            ctx: Parser.LiteralExpressionContext) -> Any:
        return vba_stdlib.literal_from_string(ctx.getText())
