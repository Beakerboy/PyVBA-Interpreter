from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ExitDoException')


class ExitDoException(VbaCompileException):

    def __init__(self: T) -> None:
        self.msg = "Exit Do not within Do...Loop"
        super().__init__(self.msg)
