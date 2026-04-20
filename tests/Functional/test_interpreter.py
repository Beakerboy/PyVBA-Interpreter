import os
import pytest
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor
from pyvba_interpreter.Exceptions.vba_compile_exception import VbaCompileException
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
        ('MsgBox -2', "-2"),
        ('Call MsgBox(2 ^ 2)', "4"),
        ('Call MsgBox(6 * 4)', "24"),
        ('Call MsgBox(10 / 2)', "5.0"),
        ('Call MsgBox(4 + 6)', "10"),
        ('Call MsgBox(6 - 1)', "5"),
        ('Call MsgBox(10 Mod 3)', "1"),
        ('Call MsgBox(10 \\ 3)', "3"),
        ('MsgBox True', "True"),
        ('MsgBox False', "False"),
        ('Call MsgBox(True And False)', "False"),
        ('Call MsgBox(True Or False)', "True"),
        ('Call MsgBox(True Xor False)', "True"),
        ('Call MsgBox(True Imp False)', "False"),
        ('Call MsgBox(True Eqv False)', "False"),
        ('Call MsgBox(1 < 2)', "True"),
        ('Call MsgBox(1 <= 2)', "True"),
        ('Call MsgBox(1 > 2)', "False"),
        ('Call MsgBox(1 >= 2)', "False"),
        ('Call MsgBox(1 = 2)', "False"),
        ('Call MsgBox(1 <> 2)', "True"),
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
    ctx = table.definitions["hello"]
    interpreter.visit(ctx)
    mock_print.assert_called_with(expected)

def test_function_not_defined() -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "HelloWorld"\n')
        file.write('Function hello()\n')
        file.write('    MsgBox hello1()\n')
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
    ctx = table.definitions["hello"]
    with pytest.raises(VbaCompileException):
        interpreter.visitChildren(ctx)
