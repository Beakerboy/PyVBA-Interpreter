from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ExitFunctionException')


class ExitFunctionException(VbaCompileException):

    def __init__(self: T) -> None:
        super().__init__("Exit Function not allowed in Sub or Property")
