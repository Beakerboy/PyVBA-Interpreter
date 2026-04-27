import os
import pytest
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor


def build_interp(name: str, code: str, table: SymbolTable) -> VbaVisitor:
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
    listener = VbaListener(table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)
    return table


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
    result = visitor.execute_function("foo", [], True)
    expected = 42
    assert result == expected
