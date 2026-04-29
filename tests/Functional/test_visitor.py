import os
import pytest
from vba_stdlib.interaction import Interaction
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import FunctionType, SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor
from pyvba_interpreter.Exceptions.vba_compile_exception import (
    VbaCompileException
)
from pyvba_interpreter.Exceptions.vba_exception import (
    VbaException
)
from typing import Any
from unittest.mock import patch


def build_interp(code: str) -> VbaVisitor:
    code = 'Attribute VB_NAME = "HelloWorld"\n' + code
    file_path = 'tests/files/test.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write(code)
    input_stream = FileStream(file_path)
    lexer = Lexer(input_stream)
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()
    table = SymbolTable()
    listener = VbaListener(table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)
    return VbaVisitor(table)


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
    code = ('Function hello()\n'
            '    ' + input + '\n'
            'End Function\n')
    interpreter = build_interp(code)
    interpreter.table.library_definitions["vba"] = {
        "type": FunctionType.MODULE,
        "functions": {
            "msgbox": {
                "type": FunctionType.FUNCTION,
                "handle": getattr(Interaction, "MsgBox"),
                "module": "vba"
            }
        }
    }
    interpreter.execute_function("hello", [])
    mock_print.assert_called_with(expected)


@pytest.mark.parametrize(
    "input, expected", [
        ('hello = 1', 1),
        ('hello = "1"', "1"),
        ('hello = 1 + 1', 2),
        ('hello = True', True),
        ('hello = False', False),
        ('hello = Array(1)', [1]),
        ('hello = Array(1, 2)', [1, 2]),
        ('hello = 1\n'
         'Exit Function\n'
         'hello = 2\n', 1),
    ])
def test_function(input: str, expected: Any) -> None:
    code = ('Function hello()\n'
            '    ' + input + '\n'
            'End Function\n')
    interpreter = build_interp(code)
    result = interpreter.execute_function("hello", [])
    assert result == expected


@pytest.mark.parametrize(
    "arg_list, input, args, expected", [
        ('Arg', 'hello = Arg', [1], 1),
    ])
def test_function_arguments(
        arg_list: str, input: str, args: list, expected: Any) -> None:
    code = ('Function hello(' + arg_list + ')\n'
            '    ' + input + '\n'
            'End Function\n')
    visitor = build_interp(code)
    result = visitor.execute_function("hello", args)
    assert result == expected


def test_function_not_defined() -> None:
    code = ('Function Foo()\n'
            '    Bar\n'
            'End Function\n')
    visitor = build_interp(code)
    with pytest.raises(VbaCompileException) as e:
        visitor.execute_function("foo", [])
    assert str(e.value) == "Compile error:\nSub or Function not defined"


@patch('builtins.print')
def test_override(mock_print: str) -> None:
    code = ('Function hello()\n'
            '     MsgBox "HelloWorld"\n'
            'End Function\n'
            'Function MsgBox(temp)\n'
            'End Function\n')
    visitor = build_interp(code)
    visitor.table.library_definitions["vba"] = {"msgbox": {
        "type": FunctionType.FUNCTION,
        "handle": getattr(Interaction, "MsgBox"),
        "module": "vba"
    }}
    visitor.execute_function("hello", [])
    mock_print.assert_not_called()


def test_missing_argument() -> None:
    code = ('Function hello()\n'
            '    MsgBox\n'
            'End Function\n')
    visitor = build_interp(code)
    interpreter.table.library_definitions["vba"] = {
        "type": FunctionType.MODULE,
        "functions": {
            "msgbox": {
                "type": FunctionType.FUNCTION,
                "handle": getattr(Interaction, "MsgBox"),
                "module": "vba"
            }
        }
    }
    with pytest.raises(VbaCompileException) as e:
        visitor.execute_function("hello", [])
    assert str(e.value) == "Compile error:\nArgument not optional"


def test_two_functions() -> None:
    """
    Test that one function can pass its result to another.
    """
    code = ('Function Foo()\n'
            '    Foo = Bar()\n'
            'End Function\n'
            'Function Bar()\n'
            '    Bar = 2\n'
            'End Function\n')
    visitor = build_interp(code)
    result = visitor.execute_function("foo", [])
    assert result == 2


@pytest.mark.parametrize(
    "code", [
        ('Function Foo()\n'
         '    Bar = 1\n'
         '    Foo = Bar\n'
         'End Function\n'
         'Sub Bar()\n'
         'End Sub\n'),
        ('Function Foo()\n'
         '    Bar\n'
         '    Foo = 2\n'
         'End Function\n'
         'Sub Bar()\n'
         '    Bar = 2\n'
         'End Sub\n'),
        ('Function Foo()\n'
         '    Foo = Bar()\n'
         'End Function\n'
         'Sub Bar()\n'
         'End Sub\n'),
        ('Function Foo()\n'
         '    Foo = Bar\n'
         'End Function\n'
         'Sub Bar()\n'
         'End Sub\n'),
    ])
def test_sub_as_variable(code: str) -> None:
    visitor = build_interp(code)
    with pytest.raises(VbaCompileException) as e:
        visitor.execute_function("foo", [])
    assert str(e.value) == "Compile error:\nExpected Function or variable"


def test_func_as_variable() -> None:
    code = ('Function Foo()\n'
            '    Bar = 1\n'
            '    Foo = Bar\n'
            'End Function\n'
            'Function Bar()\n'
            'End Function\n')
    visitor = build_interp(code)
    with pytest.raises(VbaException):
        visitor.execute_function("foo", [])
