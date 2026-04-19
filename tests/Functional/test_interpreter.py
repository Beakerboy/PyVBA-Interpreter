import os
import pytest
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor
from typing import Any
from unittest.mock import patch


@patch('builtins.print')
def test_interpreter(mock_print: str) -> None:
    input_stream = FileStream('tests/files/HelloWorld.bas')
    lexer = Lexer(input_stream)
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()  # or module?
    table = SymbolTable()
    listener = VbaListener(table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)
    assert len(table.definitions) == 1


@patch('builtins.print')
@pytest.mark.parametrize(
    "input, expected", [
        ('Call MsgBox("Hello World")', "Hello World"),
        ('MsgBox "Hello World"', "Hello World"),
        ('MsgBox 2', "2"),
        ('MsgBox (2 ^ 2)', "4"),
        ('MsgBox (6 * 4)', "18"),
        ('MsgBox (10 / 2)', "5"),
        ('MsgBox (4 + 6)', "10"),
        ('MsgBox (6 - 1)', "5"),
    ])
def test_msgbox(mock_print: str, input: str, expected: Any) -> None:
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
    tree = vbaparser.module()
    table = SymbolTable()
    listener = VbaListener(table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)
    interpreter = VbaVisitor(table)
    interpreter.visit(tree)
    ctx = table.definitions["hello"]
    interpreter.visitChildren(ctx)
    mock_print.assert_called_with(expected)
