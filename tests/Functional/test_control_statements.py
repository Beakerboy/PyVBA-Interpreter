import os
import pytest
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor


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
    listener = VbaListener(table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)
    return VbaVisitor(table)


@pytest.mark.parametrize(
    "code", [
        ('Function Fact(num)\n'
         '    If Num = 1 Then\n'
         '        Fact = 1\n'
         '    Else\n'
         '        Fact = Num * Fact(Num - 1)\n'
         '    End If\n'
         'End Function\n'),
        ('Function Fact(num)\n'
         '    Fact = 1\n'
         '    If Num > 1 Then\n'
         '        Fact = Num * Fact(Num - 1)\n'
         '    End If\n'
         'End Function\n'),
        ('Function Fact(num)\n'
         '    If Num = 1 Then Fact = 1 Else Fact = Num * Fact(Num - 1)\n'
         'End Function\n'),
        ('Function Fact(num)\n'
         '    Fact = 1\n'
         '    If Num > 1 Then Fact = Num * Fact(Num - 1)\n'
         'End Function\n'),
        ('Function Fact(num)\n'
         '    Fact = 1\n'
         '    If Num <= 1 Then Else Fact = Num * Fact(Num - 1)\n'
         'End Function\n'),
        ('Function Fact(Num)\n'
         '    Fact = 1\n'
         '    While Num > 1\n'
         '        Fact = Num * Fact\n'
         '        Num = Num - 1\n'
         '    Wend\n'
         'End Function\n'),
        ('Function Fact(Num)\n'
         '    Fact = 1\n'
         '    For I = 1 To Num\n'
         '        Fact = I * Fact\n'
         '    Next I\n'
         'End Function\n'),
        ('Function Fact(Num)\n'
         '    Fact = 1\n'
         '    For I = 1 To Num + 2\n'
         '        Fact = I * Fact\n'
         '        If I = Num Then Exit For\n'
         '    Next I\n'
         'End Function\n'),
    ])
def test_factorial(code: str) -> None:
    interpreter = build_interp(code)
    result = interpreter.execute_function("fact", [5], True)
    expected = 120
    assert result == expected
