import os
import pytest
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor
from pyvba_interpreter.Exceptions.vba_compile_exception import (
    VbaCompileException
)


def build_interp(name: str, code: str, table: SymbolTable) -> None:
    code = f'Attribute VB_NAME = "{name}"\n{code}'
    file_path = f'tests/files/{name}.bas'
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
    listener = VbaListener("vbaproject", table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)


@pytest.mark.parametrize(
    "code1, code2", [
        ('Function Foo()\n'
         '    Foo = Bar()\n'
         'End Function\n',
         'Function Bar()\n'
         '    Bar = 42\n'
         'End Function\n'),
        ('Function Foo()\n'
         '    Foo = Bar()\n'
         'End Function\n'
         'Function Bar()\n'
         '    Bar = 42\n'
         'End Function\n',
         'Function Bar()\n'
         '    Bar = 24\n'
         'End Function\n'),
        ('Function Foo()\n'
         '    Foo = BarModule.Bar()\n'
         'End Function\n'
         'Function Bar()\n'
         '    Bar = 24\n'
         'End Function\n',
         'Function Bar()\n'
         '    Bar = 42\n'
         'End Function\n'),
    ])
def test_two_files(code1: str, code2: str) -> None:
    table = SymbolTable()
    build_interp("FooModule", code1, table)
    build_interp("BarModule", code2, table)
    visitor = VbaVisitor(table)
    modules = table.definitions["vbaproject"]["modules"]
    func = modules["foomodule"]["functions"]["foo"]
    result = visitor.run_function(func, [])
    expected = 42
    assert result == expected


@pytest.mark.parametrize(
    "code1, code2", [
        ('Function Foo()\n'
         '    Foo = BarModule.Baz()\n'
         'End Function\n',
         ''),
    ])
def test_member_not_found(code1: str, code2: str) -> None:
    table = SymbolTable()
    build_interp("FooModule", code1, table)
    build_interp("BarModule", code2, table)
    visitor = VbaVisitor(table)
    modules = table.definitions["vbaproject"]["modules"]
    func = modules["foomodule"]["functions"]["foo"]
    with pytest.raises(VbaCompileException) as e:
        visitor.run_function(func, [])
    assert str(e.value) == "Compile error:\nMethod or data member not found"


@pytest.mark.parametrize(
    "code1, code2", [
        ('Function Foo()\n'
         '    Foo = Bar()\n'
         'End Function\n',
         ''),
    ])
def test_call_module_name(code1: str, code2: str) -> None:
    table = SymbolTable()
    build_interp("FooModule", code1, table)
    build_interp("Bar", code2, table)
    visitor = VbaVisitor(table)
    modules = table.definitions["vbaproject"]["modules"]
    func = modules["foomodule"]["functions"]["foo"]
    with pytest.raises(VbaCompileException) as e:
        visitor.run_function(func, [])
    expected = "Compile error:\nExpected variable or procedure, not module"
    assert str(e.value) == expected
