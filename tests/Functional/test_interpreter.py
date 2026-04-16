import os
import pytest
from antlr4 import CommonTokenStream, FileStream
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.vba_visitor import VbaVisitor
from typing import Any
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


@patch('builtins.print')
@pytest.mark.parametrize(
    "input, expected", [
        ('Call MsgBox("Hello World")', "Hello World"),
        ('MsgBox "Hello World"', "Hello World"),
        ('MsgBox 1', 1),
    ])
def test_msgbox(mock_print, input: str, expected: Any) -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "HelloWorld"\n')
        file.write('Function hello()\n')
        file.write('    ' + input + '\n')
        file.write('End Function\n')
    input_stream = FileStream(file_path)
    lexer = Lexer(input_stream)
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()  # or module?
    interpreter = VbaVisitor()
    interpreter.visit(tree)
    ctx = interpreter.functions["hello"]
    interpreter.visitChildren(ctx)
    mock_print.assert_called_with(expected)
