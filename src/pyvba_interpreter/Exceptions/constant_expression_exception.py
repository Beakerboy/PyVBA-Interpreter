from .vba_compile_exception import VbaCompileException
from typing import TypeVar


T = TypeVar('T', bound='ConstantExpressionException')


class ConstantExpressionException(VbaCompileException):

    def __init__(self: T) -> None:
        self.msg = "Constant expression required"
        super().__init__(self.msg)
