from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ExitSubException')


class ExitSubException(VbaCompileException):

    def __init__(self: T) -> None:
        super().__init__("Exit Sub not allowed in Function or Property")
