import argparse
from antlr4 import CommonTokenStream, FileStream
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pathlib import Path
from .vba_visitor import VbaVisitor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("function",
                        help="The function or call statement to execute.")
    parser.add_argument("module",
                        help="The module that contains your code.")
    args = parser.parse_args()
    path = Path(args.module).resolve()
    function_to_run = args.function
    if Path(path).exists():
        input_stream = FileStream(args.module)
        lexer = Lexer(input_stream)
    else:
        raise Exception('file does not exist: ' + args.module)
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()  # or module?
    interpreter = VbaVisitor()
    interpreter.visit(tree)
    if function_to_run in interpreter.functions:
        target_node = interpreter.functions[function_to_run]
        interpreter.visitChildren(target_node)
    else:
        print("error:")
