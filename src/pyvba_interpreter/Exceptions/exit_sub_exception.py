from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ExitSubException')


class ExitSubException(VbaCompileException):

    def __init__(self: T) -> None:
        self.msg = "Exit Sub not allowed in Function or Property"
        super().__init__(self.msg)
