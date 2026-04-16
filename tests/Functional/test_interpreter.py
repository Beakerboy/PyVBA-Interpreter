import pytest
from antlr4 import CommonTokenStream, FileStream
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.vba_visitor import VbaVisitor
from unittest.mock import patch


@patch('builtins.print')
def test_interpreter(mock_print) -> None:
    function_to_run = "hello()"
    input_stream = FileStream('tests/files/HelloWorld.bas')
    lexer = Lexer(input_stream)
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()  # or module?
    interpreter = VbaVisitor()
    interpreter.visit(tree)
    assert len(interpreter.functions) == 1
    ctx = interpreter.functions["hello"]
    interpreter.visitChildren(ctx)
    mock_print.assert_called_with("Hello World")
