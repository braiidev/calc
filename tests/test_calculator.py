"""Tests del motor de cálculo: aritmética, científica, raíz y división entera."""

import pytest

from calculator import CalcMathError, CalcSyntaxError, Calculator


@pytest.fixture
def calc() -> Calculator:
    return Calculator()


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("2 + 3 * 4", 14.0),
        ("(2 + 3) * 4", 20.0),
        ("2 ** 3", 8.0),
        ("2 ** 3 ** 2", 512.0),  # asociativa a la derecha
        ("5!", 120.0),
        ("2 ** 3!", 64.0),
        ("sqrt(9)", 3.0),
        ("10 % 3", 1.0),
    ],
)
def test_basicas(calc: Calculator, expr: str, expected: float) -> None:
    assert calc.evaluate(expr) == expected


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("8//3", 2.0),  # raíz cúbica
        ("27//3", 3.0),
        ("16//2", 4.0),  # raíz cuadrada
        ("16//4", 2.0),
        ("-8//3", -2.0),  # índice impar sobre negativo
        ("4 + 8//3", 6.0),
    ],
)
def test_raiz_nesima(calc: Calculator, expr: str, expected: float) -> None:
    assert calc.evaluate(expr) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("expr", "message"),
    [
        ("8//0", "Índice de raíz cero"),
        ("-16//2", "Raíz de índice par sobre número negativo"),
        ("-8//2.5", "Raíz de número negativo con índice fraccionario"),
    ],
)
def test_raiz_errores(calc: Calculator, expr: str, message: str) -> None:
    with pytest.raises(CalcMathError, match=message):
        calc.evaluate(expr)


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("5:2", 2.0),
        ("7:3", 2.0),
        ("9:3", 3.0),
    ],
)
def test_division_entera(calc: Calculator, expr: str, expected: float) -> None:
    assert calc.evaluate(expr) == expected


def test_division_entera_requiere_enteros(calc: Calculator) -> None:
    with pytest.raises(CalcMathError):
        calc.evaluate("5.5:2")


def test_errores_sintaxis_siguen_siendo_errores(calc: Calculator) -> None:
    with pytest.raises(CalcSyntaxError):
        calc.evaluate("2 +")
    with pytest.raises(CalcSyntaxError):
        calc.evaluate("2(")
    with pytest.raises(CalcSyntaxError):
        calc.evaluate("sqrt")  # falta '('
