import os
import pytest
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pyvba_interpreter.symbol_table import SymbolTable
from pyvba_interpreter.vba_listener import VbaListener
from pyvba_interpreter.Exceptions.vba_compile_exception import (
    VbaCompileException
)


def test_interpreter() -> None:
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


def test_exception() -> None:
    code = ('Attribute VB_NAME = "FooModule"\n'
            'Function Hello()\n'
            '    Hello = 0\n'
            'End Function\n'
            'Sub Hello()\n'
            'End Sub\n')
    file_path = 'tests/files/Foo.bas'
    try:
        os.remove(file_path)
    except FileNotFoundError:
        # File did not exist; ignore the error
        pass
    with open(file_path, "w", newline='\r\n') as file:
        file.write(code)
    table = SymbolTable()
    input_stream = FileStream(file_path)
    lexer = Lexer(input_stream)
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()
    listener = VbaListener(table)
    walker = ParseTreeWalker()
    with pytest.raises(VbaCompileException) as e:
        walker.walk(listener, tree)
    assert str(e.value) == "Ambiguous name detected: Hello"
