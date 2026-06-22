from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ExitForException')


class ExitForException(VbaCompileException):

    def __init__(self: T) -> None:
        self.msg = "Exit For not within For...Next"
        super().__init__(self.msg)
