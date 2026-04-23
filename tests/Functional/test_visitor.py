import os
import pytest
from vba_stdlib.interaction import Interaction
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor
from pyvba_interpreter.Exceptions.vba_compile_exception import (
    VbaCompileException
)
from typing import Any
from unittest.mock import patch


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
    table.library_definitions["msgbox"] = {
        "type": "builtin",
        "handle": getattr(Interaction, "MsgBox")
    }
    interpreter.execute_function("hello", [], True)
    mock_print.assert_called_with(expected)


@pytest.mark.parametrize(
    "input, expected", [
        ('hello = 1', 1),
        ('hello = "1"', "1"),
        ('hello = 1 + 1', 2),
    ])
def test_function(input: str, expected: Any) -> None:
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
    result = interpreter.execute_function("hello", [], True)
    assert result == expected


@pytest.mark.parametrize(
    "arg_list, input, args, expected", [
        ('Arg', 'hello = Arg', [1], 1),
    ])
def test_function_arguments(
        arg_list: str, input: str, args: list, expected: Any) -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "HelloWorld"\n')
        file.write('Function hello(' + arg_list + ')\n')
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
    result = interpreter.execute_function("hello", args, True)
    assert result == expected


def test_factorial() -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "Factorial"\n')
        file.write('Function Fact(num)\n')
        file.write('    If Num = 1 Then\n')
        file.write('        Fact = 1\n')
        file.write('    Else\n')
        file.write('        Fact = Num * Fact(Num - 1)\n')
        file.write('    End If\n')
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
    result = interpreter.execute_function("fact", [5], True)
    expected = 120
    assert result == expected


def test_no_else() -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "Factorial"\n')
        file.write('Function Fact(num)\n')
        file.write('    Fact = 1\n')
        file.write('    If Num > 1 Then\n')
        file.write('        Fact = Num * Fact(Num - 1)\n')
        file.write('    End If\n')
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
    result = interpreter.execute_function("fact", [5], True)
    expected = 120
    assert result == expected


def test_while() -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "Factorial"\n')
        file.write('Function Fact(Num)\n')
        file.write('    Fact = 1\n')
        file.write('    \'While Num > 1 \n')
        file.write('        Fact = Num * Fact\n')
        file.write('.       Num = Num - 1\n')
        file.write('    \'Wend\n')
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
    result = interpreter.execute_function("fact", [5], True)
    expected = 120
    assert result == expected


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
        file.write('    Hello1\n')
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
    table.library_definitions["msgbox"] = {
        "type": "builtin",
        "handle": getattr(Interaction, "MsgBox")
    }
    ctx = table.definitions["hello"]["handle"]
    with pytest.raises(VbaCompileException):
        interpreter.visit(ctx)


@patch('builtins.print')
def test_override(mock_print: str) -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "HelloWorld"\n')
        file.write('Function hello()\n')
        file.write('    MsgBox "HelloWorld"\n')
        file.write('End Function\n')
        file.write('Function MsgBox(temp)\n')
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
    assert len(table.definitions) == 2
    interpreter = VbaVisitor(table)
    table.library_definitions["msgbox"] = {
        "type": "builtin",
        "handle": getattr(Interaction, "MsgBox")
    }
    interpreter.execute_function("hello", [], True)
    mock_print.assert_not_called()


def test_missing_argument() -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "HelloWorld"\n')
        file.write('Function hello()\n')
        file.write('    MsgBox\n')
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
    table.library_definitions["msgbox"] = {
        "type": "builtin",
        "handle": getattr(Interaction, "MsgBox")
    }
    with pytest.raises(VbaCompileException) as e:
        interpreter.execute_function("hello", [], True)
    assert str(e.value) == "Compile error:\nArgument not optional"


def test_two_functions() -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "HelloWorld"\n')
        file.write('Function hello()\n')
        file.write('    hello = Hello1()\n')
        file.write('End Function\n')
        file.write('Function Hello1()\n')
        file.write('    Hello = 1\n')
        file.write('    Hello1 = Hello + 1()\n')
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
    result = interpreter.execute_function("hello", [], True)
    assert result == 2


def futuretest_use_sub_as_function() -> None:
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write('Attribute VB_NAME = "HelloWorld"\n')
        file.write('Function hello()\n')
        file.write('    Foo = Hello1\n')
        file.write('End Function\n')
        file.write('Sub Hello1()\n')
        file.write('End Sub\n')
    input_stream = FileStream(file_path)
    lexer = Lexer(input_stream)
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()
    table = SymbolTable()
    listener = VbaListener(table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)
    assert len(table.definitions) == 2
    interpreter = VbaVisitor(table)
    with pytest.raises(VbaCompileException) as e:
        interpreter.execute_function("hello", [], True)
    assert str(e.value) == "Unexpected Function or variable"
