import os
import pytest
import vba_types
from vba_stdlib.interaction import Interaction
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pytest_mock import MockerFixture
from pyvba_interpreter.symbol_table import SymbolTable
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


vba_project = {
    "name": "vba",
    "type": "project",
    "modules": {
        "interaction": {
            "name": "interaction",
            "type": "module",
            "functions": {
                "msgbox": {
                    "name": "msgbox",
                    "type": "function",
                    "handle": getattr(Interaction, "msgbox"),
                    "project": "vba",
                    "module": "interaction",
                    "params": [{
                            "name": "prompt",
                            "optional": False,
                            "default": ""
                    }]
                }
            }
        }
    }
}


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
    listener = VbaListener("vbaproject", table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)
    return VbaVisitor(table)


@pytest.mark.parametrize(
    "input, expected", [
        ('Call MsgBox("Hello World")', "Hello World"),
        ('Call VBA.MsgBox("Hello World")', "Hello World"),
        ('Call VBA.Interaction.MsgBox("Hello World")', "Hello World"),
        ('Call Interaction.MsgBox("Hello World")', "Hello World"),
        ('MsgBox "Hello World"', "Hello World"),
        ('VBA.MsgBox "Hello World"', "Hello World"),
        ('VBA.Interaction.MsgBox "Hello World"', "Hello World"),
        ('Interaction.MsgBox "Hello World"', "Hello World"),
    ])
def test_msgbox(input: str, expected: Any, mocker: MockerFixture) -> None:
    mock_print = mocker.patch('builtins.print')
    mocker.patch('builtins.input', return_value="")
    code = ('Function hello()\n'
            '    ' + input + '\n'
            'End Function\n')
    visitor = build_interp(code)
    visitor.table.library_definitions["vba"] = vba_project
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    visitor.run_function(func, [])
    mock_print.assert_called_with(f"Microsoft Excel\n\n{expected}\nOK")


@pytest.mark.parametrize(
    "input, expected", [
        ('hello = 1', 1),
        ('hello = -2', -2),
        ('hello = "1"', "1"),
        ('hello = 1 + 1', 2),
        ('hello = 6 - 1', 5),
        ('hello = 6 * 4', 24),
        ('hello = (6 * 4)', 24),
        ('hello = 10 / 2', 5.0),
        ('hello = 10 Mod 3', 1),
        ('hello = 10 \\ 3', 3),
        ('hello = 2 ^ 2', 4),
        ('N = 10\n    hello = (N - 1) / N ^ .5', 2.846049894151541),
        ('hello = "Hello" & " World"', "Hello World"),
        ('hello = 1 & 2 & "Hello"', "12Hello"),
        ('hello = 1\n'
         'Exit Function\n'
         'hello = 2\n', 1),
        ('Dim Temp as Integer\n'
         'hello = Temp\n', 0),
    ])
def test_int_function(input: str, expected: Any) -> None:
    code = ('Function hello()\n'
            '    ' + input + '\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert result.value == expected


@pytest.mark.parametrize(
    "input, expected", [
        ('hello = True', True),
        ('hello = False', False),
        ('hello = True And False', False),
        ('hello = True Or False', True),
        ('hello = True Xor False', True),
        ('hello = True Imp False', False),
        ('hello = True Eqv False', False),
        ('hello = 1 < 2', True),
        ('hello = 1 <= 2', True),
        ('hello = 1 > 2', False),
        ('hello = 1 >= 2', False),
        ('hello = 1 = 2', False),
        ('hello = 1 <> 2', True),
    ])
def test_bool_function(input: str, expected: Any) -> None:
    code = ('Function hello()\n'
            '    ' + input + '\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert bool(result) == expected
    assert isinstance(result, vba_types.boolean.VBABoolean)


def test_array() -> None:
    code = ('Function hello()\n'
            '    hello = Array(1, 2, 3)\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert int(result[0]) == 1
    assert int(result[1]) == 2
    assert int(result[2]) == 3


def test_array_index() -> None:
    code = ('Function hello()\n'
            '    Temp = Array(1, 2, 3)\n'
            '    hello = Temp(0)\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert result.value == 1


@pytest.mark.parametrize(
    "arg_list, input, args, expected", [
        ('Arg', 'hello = Arg', [1], 1),
        ('Arg As Integer', 'hello = Arg', [1], 1),
    ])
def test_function_arguments(
        arg_list: str, input: str, args: list, expected: Any) -> None:
    code = ('Function hello(' + arg_list + ')\n'
            '    ' + input + '\n'
            'End Function\n')
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    result = visitor.run_function(func, args)
    assert result == expected


def test_function_not_defined() -> None:
    code = ('Function Foo()\n'
            '    Bar\n'
            'End Function\n')
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["foo"]
    with pytest.raises(VbaCompileException) as e:
        visitor.run_function(func, [])
    assert str(e.value) == "Compile error:\nSub or Function not defined"


@patch('builtins.print')
def test_override(mock_print: str) -> None:
    code = ('Function hello()\n'
            '     MsgBox "HelloWorld"\n'
            'End Function\n'
            'Function MsgBox(temp)\n'
            'End Function\n')
    visitor = build_interp(code)
    visitor.table.library_definitions["vba"] = vba_project
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    visitor.run_function(func, [])
    mock_print.assert_not_called()


def test_missing_argument() -> None:
    code = ('Function hello()\n'
            '    MsgBox\n'
            'End Function\n')
    visitor = build_interp(code)
    visitor.table.library_definitions["vba"] = vba_project
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    with pytest.raises(VbaCompileException) as e:
        visitor.run_function(func, [])
    assert str(e.value) == "Compile error:\nArgument not optional"


def test_extra_argument() -> None:
    code = ('Function Foo()\n'
            '    Foo = Bar(1, 2)\n'
            'End Function\n'
            'Function Bar(Num)\n'
            '    Bar = Num\n'
            'End Function\n')
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["foo"]
    with pytest.raises(VbaCompileException) as e:
        visitor.run_function(func, [])
    msg = ("Compile error:\nWrong number of arguments or invalid property"
           " assignment")
    assert str(e.value) == msg


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
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["foo"]
    result = visitor.run_function(func, [])
    assert result.value == 2


@pytest.mark.parametrize(
    "statement", [
        ('True Or Bar()'),
        ('False And Bar()'),
    ])
def test_no_short_circuit(statement: str, mocker: MockerFixture) -> None:
    """
    Boolean Expressions do not short circuit
    """
    mock_print = mocker.patch('builtins.print')
    mocker.patch('builtins.input', return_value="")
    code = ('Function Foo()\n'
            '    Foo = ' + statement + '\n'
            'End Function\n'
            'Function Bar()\n'
            '    Bar = False\n'
            '    MsgBox "Bar is Called"\n'
            'End Function\n')
    visitor = build_interp(code)
    visitor.table.library_definitions["vba"] = vba_project
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["foo"]
    visitor.run_function(func, [])
    expected = "Bar is Called"
    mock_print.assert_called_with(f"Microsoft Excel\n\n{expected}\nOK")


def test_default_arg() -> None:
    code = ('Function hello(Optional Temp = 5)\n'
            '    hello = Temp\n'
            'End Function\n')
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    result = visitor.run_function(func, [])
    assert result.value == 5


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
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["foo"]
    with pytest.raises(VbaCompileException) as e:
        visitor.run_function(func, [])
    assert str(e.value) == "Compile error:\nExpected Function or variable"


def test_func_as_variable() -> None:
    code = ('Function Foo()\n'
            '    Bar = 1\n'
            '    Foo = Bar\n'
            'End Function\n'
            'Function Bar()\n'
            'End Function\n')
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["foo"]
    with pytest.raises(VbaException):
        visitor.run_function(func, [])


@pytest.mark.parametrize(
    "code1", [
        ('Function Foo()\n'
         '    Foo = VBA()\n'
         'End Function\n'),
    ])
def test_call_module_name(code1: str) -> None:
    visitor = build_interp(code1)
    visitor.table.library_definitions["vba"] = vba_project
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["foo"]
    with pytest.raises(VbaCompileException) as e:
        visitor.run_function(func, [])
    expected = "Compile error:\nExpected variable or procedure, not project"
    assert str(e.value) == expected
