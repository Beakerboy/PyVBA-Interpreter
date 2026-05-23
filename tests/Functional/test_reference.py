import pytest
from .build import build_interp
from vba_types import VBAInteger


@pytest.mark.parametrize(
    "code, expected", [
        ('Function Foo()\n'
         '    Num = 10\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(Num1)\n'
         '    Num1 = 11\n'
         'End Sub\n', 11),
        ('Function Foo()\n'
         '    Num = 10\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(ByRef Num1)\n'
         '    Num1 = 11\n'
         'End Sub\n', 11),
        ('Function Foo()\n'
         '    Num = 10\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(ByVal Num1)\n'
         '    Num1 = 11\n'
         'End Sub\n', 10)
    ])
def test_byref(code: str, expected: int) -> None:
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["factorial"]["functions"]["foo"]
    result = visitor.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert int(result) == expected
