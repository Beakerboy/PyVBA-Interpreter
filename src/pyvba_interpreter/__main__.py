import argparse
from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4_vba.vbaLexer import vbaLexer as Lexer
from antlr4_vba.vbaParser import vbaParser as Parser
from pathlib import Path
from .symbol_table import SymbolTable
from .vba_listener import VbaListener
from .vba_visitor import VbaVisitor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("function",
                        help="The function or call statement to execute.")
    parser.add_argument("module",
                        help="The module that contains your code.")
    parser.add_argument("project",
                        help="The project that contains your code.")
    args = parser.parse_args()
    function_to_run = args.function
    path = Path(args.module).resolve()
    if Path(path).exists():
        input_stream = FileStream(args.module)
        lexer = Lexer(input_stream)
    else:
        raise Exception('file does not exist: ' + args.module)
    ts = CommonTokenStream(lexer)
    vbaparser = Parser(ts)
    tree = vbaparser.module()
    table = SymbolTable()
    listener = VbaListener(args.project, table)
    walker = ParseTreeWalker()
    walker.walk(listener, tree)

    interpreter = VbaVisitor(table)
    interpreter.visit(tree)
    project = table.definitions[args.project]
    module = project["modules"][args.module]
    if function_to_run in module["functions"]:
        target_node = module["functions"][function_to_run]
        interpreter.visitChildren(target_node)
    else:
        print("error:")
