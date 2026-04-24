import os
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.vba_visitor import VbaVisitor
from unittest.mock import patch


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
        file.write('    While Num > 1\n')
        file.write('        Fact = Num * Fact\n')
        file.write('        Num = Num - 1\n')
        file.write('    Wend\n')
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


def test_for() -> None:
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
        file.write('    For i = 1 To Num\n')
        file.write('        Fact = Num * Fact\n')
        file.write('    Next i\n')
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
