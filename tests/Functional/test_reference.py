import os
import pytest
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor
from vba_types import VBAInteger


def build_interp(code: str) -> VbaVisitor:
    code = 'Attribute VB_NAME = "Factorial"\n' + code
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
    "code, expected", [
        ('Function Foo()\n'
         '    Num = 10\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Function Bar(Num1)\n'
         '    Num1 = 11\n'
         'End Function\n', 11),
        ('Function Foo()\n'
         '    Num = 10\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(ByRef Num1)\n'
         '    Num1 = 11\n'
         'End Sub\n', 10)
    ])
def test_byref(code: str, expected: int) -> None:
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["factorial"]["functions"]["foo"]
    result = visitor.run_function(func, [VBAInteger(5)])
    expected = 120
    assert isinstance(result, VBAInteger)
    assert int(result) == expected
