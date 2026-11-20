from pyvba_interpreter.Exceptions.vba_compile_exception import (
    VbaCompileException,
)
from vba_types import VBAArray
import pytest
from tests.Functional.build import build_interp
from vba_types import VBAInteger, VBALong
from vba_types.exceptions import SubscriptOutOfRangeError, TypeMismatchError


def test_dim_array_bounds() -> None:
    code = ('Function hello()\n'
            '    Dim Results(1 To 2) As Variant\n'
            '    Results(1) = 10\n'
            '    Results(2) = 32\n'
            '    hello = Results(1) + Results(2)\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert int(result) == 42


def test_dim_array_default_lower_bound() -> None:
    code = ('Function hello()\n'
            '    Dim Values(2) As Integer\n'
            '    Values(0) = 5\n'
            '    Values(2) = 7\n'
            '    hello = Values(0) + Values(2)\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert int(result) == 12


def test_dim_multidimensional_array() -> None:
    code = ('Function hello()\n'
            '    Dim Grid(1 To 2, 1 To 2) As Integer\n'
            '    Grid(1, 2) = 99\n'
            '    hello = Grid(1, 2)\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert int(result) == 99


@pytest.mark.parametrize(
    "expr, expected", [
        ("LBound(Grid)", 2),
        ("UBound(Grid)", 5),
        ("LBound(Grid, 1)", 2),
        ("UBound(Grid, 1)", 5),
        ("LBound(Grid, 2)", 1),
        ("UBound(Grid, 2)", 3),
    ]
)
def test_array_ubound_lbound(expr: str, expected: int) -> None:
    code = ('Function hello()\n'
            '    Dim Grid(2 To 5, 1 To 3) As Integer\n'
            f'    hello = {expr}\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["hello"]
    result = interpreter.run_function(func, [])
    assert isinstance(result, VBALong)
    assert int(result) == expected


def test_array_index_with_variable() -> None:
    code = ('Function Foo()\n'
            '    Bar = Array(42, 37, 73)\n'
            '    i = 1\n'
            '    Foo = Bar(i)\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["foo"]
    result = interpreter.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert int(result) == 37


def test_array_index_with_string_raises_error() -> None:
    code = ('Function Foo()\n'
            '    Bar = Array(42, 37, 73)\n'
            '    Foo = Bar("baz")\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["foo"]
    with pytest.raises(TypeMismatchError) as e:
        interpreter.run_function(func, [])
    assert "Type mismatch" in str(e.value)


@pytest.mark.parametrize("invalid_index", [99, -2])
def test_array_index_out_of_bounds(invalid_index: int) -> None:
    code = ('Function Foo()\n'
            '    Bar = Array(42, 37, 73)\n'
            f'    Foo = Bar({invalid_index})\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["foo"]
    with pytest.raises(SubscriptOutOfRangeError) as e:
        interpreter.run_function(func, [])
    assert "Subscript out of range" in str(e.value)


def test_redim_after_scalar_dim() -> None:
    code = ('Function Foo(NumPoints)\n'
            '    Dim ReturnVector As Double\n'
            '    ReDim ReturnVector(1 To NumPoints, 1 To 2)\n'
            '    ReturnVector(1,1) = 1.0\n'
            '    Foo = ReturnVector\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["foo"]
    result = interpreter.run_function(func, [VBAInteger(3)])
    assert isinstance(result, VBAArray)
    assert result[(1, 1)].value == 1.0


def test_dim_non_constant_bounds_raises_compile_error() -> None:
    code = ('Function Foo(NumPoints)\n'
            '    Dim ReturnVector(1 To NumPoints, 1 To 2) as Double\n'
            '    Foo = ReturnVector\n'
            '    ReturnVector(1,1) = 1.0\n'
            '    Foo = ReturnVector\n'
            'End Function\n')
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["foo"]
    with pytest.raises(VbaCompileException) as exc_info:
        interpreter.run_function(func, [VBAInteger(3)])
    assert str(exc_info.value) == (
        "Compile error:\nConstant expression required"
    )


def test_redim_preserve_1d_expand_and_shrink() -> None:
    code = (
        "Function Foo()\n"
        "    Dim Arr() As Integer\n"
        "    ReDim Arr(1 To 2)\n"
        "    Arr(1) = 10\n"
        "    Arr(2) = 20\n"
        "    ReDim Preserve Arr(1 To 4)\n"
        "    Arr(3) = 30\n"
        "    Foo = Arr(1) + Arr(2) + Arr(3)\n"
        "End Function\n"
    )
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["foo"]
    result = interpreter.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert int(result) == 60


def test_redim_preserve_2d_last_dimension() -> None:
    code = (
        "Function Foo()\n"
        "    Dim Grid() As Integer\n"
        "    ReDim Grid(1 To 2, 1 To 2)\n"
        "    Grid(1, 1) = 5\n"
        "    Grid(2, 2) = 7\n"
        "    ReDim Preserve Grid(1 To 2, 1 To 3)\n"
        "    Grid(2, 3) = 8\n"
        "    Foo = Grid(1, 1) + Grid(2, 2) + Grid(2, 3)\n"
        "End Function\n"
    )
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["foo"]
    result = interpreter.run_function(func, [])
    assert isinstance(result, VBAInteger)
    assert int(result) == 20


def test_redim_preserve_invalid_dimension_raises_error() -> None:
    code = (
        "Function Foo()\n"
        "    Dim Grid() As Integer\n"
        "    ReDim Grid(1 To 2, 1 To 2)\n"
        "    ReDim Preserve Grid(1 To 3, 1 To 2)\n"
        "    Foo = 1\n"
        "End Function\n"
    )
    interpreter = build_interp(code)
    modules = interpreter.table.definitions["vbaproject"]["modules"]
    module = next(iter(modules.values()))
    func = module["functions"]["foo"]
    with pytest.raises(SubscriptOutOfRangeError):
        interpreter.run_function(func, [])
