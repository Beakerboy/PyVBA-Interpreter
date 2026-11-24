from pyvba_interpreter.Exceptions.vba_compile_exception import (
    VbaCompileException
)
import pytest
from tests.Functional.build import build_interp
from vba_types import VBAInteger, VBADouble


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
         'End Sub\n', 10),
        ('Function Foo()\n'
         '    Bar 10.5\n'
         '    Foo = 1\n'
         'End Function\n'
         'Sub Bar(ByRef Num1 As Integer)\n'
         '    Num1 = 11\n'
         'End Sub\n', 1),
    ])
def test_byref(code: str, expected: int) -> None:
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["module1"]["functions"]["foo"]
    result = visitor.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert int(result) == expected


@pytest.mark.parametrize(
    "code", [
        pytest.param('Function Foo()\n'
         '    Bar 10.5\n'
         '    Foo = 1\n'
         'End Function\n'
         'Sub Bar(Num1 As Integer)\n'
         '    Num1 = 11\n'
         'End Sub\n', id="Implicit Byref"),
        pytest.param('Function Foo()\n'
         '    Dim Num As Double\n'
         '    Num = 10.5\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(ByRef Num1 As Integer)\n'
         '    Num1 = 11\n'
         'End Sub\n', id="Explicit Byref"),
    ])
def test_byref_type_mismatch_compile_error(code: str) -> None:
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["module1"]["functions"]["foo"]
    with pytest.raises(VbaCompileException) as e:
        visitor.run_function(func, [])
    assert str(e.value) == "Compile error:\nByRef argument type mismatch"


@pytest.mark.parametrize(
    "code, expected", [
        ('Function Foo()\n'
         '    Dim Num As Integer\n'
         '    Num = 10\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(ByRef Num1 As Integer)\n'
         '    Num1 = 11\n'
         'End Sub\n', 11),
        ('Function Foo()\n'
         '    Dim Num\n'
         '    Num = 10\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(ByRef Num1 As Integer)\n'
         '    Num1 = 11\n'
         'End Sub\n', 11),
        ('Function Foo()\n'
         '    Dim Num As Integer\n'
         '    Num = 10\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(ByRef Num1 As Variant)\n'
         '    Num1 = 11\n'
         'End Sub\n', 11),
    ])
def test_byref_compatible_types(code: str, expected: int) -> None:
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["module1"]["functions"]["foo"]
    result = visitor.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert result.value == expected


@pytest.mark.parametrize(
    "code, expected", [
        ('Function Foo()\n'
         '    Dim Num As Double\n'
         '    Num = 10.5\n'
         '    Bar Num\n'
         '    Foo = Num\n'
         'End Function\n'
         'Sub Bar(ByVal Num1 As Integer)\n'
         '    Num1 = 11\n'
         'End Sub\n', 10.5),
    ])
def test_byref_compatible_types_double(code: str, expected: int) -> None:
    visitor = build_interp(code)
    modules = visitor.table.definitions["vbaproject"]["modules"]
    func = modules["module1"]["functions"]["foo"]
    result = visitor.run_function(func, [])
    assert isinstance(result, VBADouble)
    assert result.value == expected
