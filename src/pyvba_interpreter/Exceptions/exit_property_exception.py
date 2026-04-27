from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ExitPropertyException')


class ExitPropertyException(VbaCompileException):

    def __init__(self: T) -> None:
        self.msg = "Exit Property not allowed in Function or Sub"
        super().__init__(self.msg)
