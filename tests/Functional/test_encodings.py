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
        ("'x²\n    hello = 1", 1),
    ])
def test_encoding(input: str, expected: Any) -> None:
    code = ('Function hello()\n'
            '    ' + input + '\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    func = modules["helloworld"]["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert result == expected
