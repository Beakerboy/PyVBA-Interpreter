import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("function",
                        help="The function or call statement to execute.")
    parser.add_argument("directory",
                        help="The directory that contains your files.")
    args = parser.parse_args()
    if Path(path).exists():
        input_stream = FileStream(path)
        lexer = Lexer(input_stream)
    else:
        raise Exception('file does not exist: ' + path)
    ts = CommonTokenStream(lexer)
    parser = Parser(ts)
    program = parser.startRule()  # or module?
    interpreter = VbaInterpreter()
    interpreter.visit(tree)
    if function_to_run in interpreter.functions:
        target_node = interpreter.functions[function_to_run]
        interpreter.visitChildren(target_node)
    else:
        print(f"error:")
