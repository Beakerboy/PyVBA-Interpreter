import argparse
from pathlib import Path
from pyvba_interpreter.vba_visitor import VbaVisitor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("function",
                        help="The function or call statement to execute.")
    parser.add_argument("directory",
                        help="The directory that contains your files.")
    args = parser.parse_args()
    path = Path(args.directory).resolve()
    function_to_run = args.function
    if Path(path).exists():
        input_stream = FileStream(path)
        lexer = Lexer(input_stream)
    else:
        raise Exception('file does not exist: ' + path)
    ts = CommonTokenStream(lexer)
    tree = Parser(ts)
    tree.startRule()  # or module?
    interpreter = VbaVisitor()
    interpreter.visit(tree)
    if function_to_run in interpreter.functions:
        target_node = interpreter.functions[function_to_run]
        interpreter.visitChildren(target_node)
    else:
        print("error:")
