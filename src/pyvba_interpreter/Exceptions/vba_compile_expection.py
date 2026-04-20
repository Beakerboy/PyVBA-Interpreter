from .vba_exception import VbaException
from typing import TypeVar


T = TypeVar('T', bound='VbaCompileException')


class VbaCompileException(VbaException):

    def __init__(self: T, msg: str) -> None:
          super().__init__("Compile error:\n" + msg)
