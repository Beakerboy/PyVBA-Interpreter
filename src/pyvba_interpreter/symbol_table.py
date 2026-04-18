class SymbolTable:
    def __init__(self):
        # Maps name -> the actual ParseTree node for that sub/function
        self.definitions = {}
