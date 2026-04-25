from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ExitDoException')


class ExitDoException(VbaCompileException):

    def __init__(self: T) -> None:
        super().__init__("Exit Do not within Do...Loop")
