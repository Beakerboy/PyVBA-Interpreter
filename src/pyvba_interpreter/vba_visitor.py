import vba_stdlib
from typing import Any, TypeVar
from antlr4_vba.vba_Parser import vba_Parser as Parser
from antlr4_vba.vba_ParserVisitor import vbaParserVisitor as Visitor


T = TypeVar('T', bound='VbaVisitor')


class VbaVisitor(Visitor):

    def __init__(self: T) -> None:
        self.functions = {}

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
