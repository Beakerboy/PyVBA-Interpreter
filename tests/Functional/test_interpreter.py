import pytest
from antlr4 import CommonTokenStream, FileStream
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pathlib import Path
from pyvba_interpreter.vba_visitor import VbaVisitor


@pytest.fixture(autouse=True)
def test_interpreter() -> None:
    path = Path(args.module).resolve()
    function_to_run = "hello()"
    if Path(path).exists():
        input_stream = FileStream('tests/files/HelloWorld.bas')
        lexer = Lexer(input_stream)
    else:
        raise Exception('file does not exist:')
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()  # or module?
    interpreter = VbaVisitor()
    interpreter.visit(tree)
