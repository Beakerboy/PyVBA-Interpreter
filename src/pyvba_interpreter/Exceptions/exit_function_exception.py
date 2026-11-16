from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ExitFunctionException')


class ExitFunctionException(VbaCompileException):

    def __init__(self: T) -> None:
        self.msg = "Exit Function not allowed in Sub or Property"
        super().__init__(self.msg)
