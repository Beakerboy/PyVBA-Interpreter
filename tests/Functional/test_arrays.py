import pytest
from tests.Functional.build import build_interp
from vba_types import VBAInteger, VBALong


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
