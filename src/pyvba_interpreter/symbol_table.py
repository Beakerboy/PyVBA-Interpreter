from typing import TypeVar


T = TypeVar('T', bound='SymbolTable')


class SymbolTable:
    def __init__(self: T) -> None:
        # Maps name -> the actual ParseTree node for that sub/function
        self.definitions = {}
