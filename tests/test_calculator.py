"""Tests del motor de cálculo: aritmética, científica, raíz, división entera y variables."""

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
        ("root(8, 3)", 2.0),  # raíz cúbica
        ("root(27, 3)", 3.0),
        ("root(16, 2)", 4.0),  # raíz cuadrada
        ("root(16, 4)", 2.0),
        ("root(-8, 3)", -2.0),  # índice impar sobre negativo
        ("4 + root(8, 3)", 6.0),
    ],
)
def test_raiz_nesima(calc: Calculator, expr: str, expected: float) -> None:
    assert calc.evaluate(expr) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("expr", "message"),
    [
        ("root(8, 0)", "Índice de raíz cero"),
        ("root(-16, 2)", "Raíz de índice par sobre número negativo"),
        ("root(-8, 2.5)", "Raíz de número negativo con índice fraccionario"),
    ],
)
def test_raiz_errores(calc: Calculator, expr: str, message: str) -> None:
    with pytest.raises(CalcMathError, match=message):
        calc.evaluate(expr)


def test_raiz_aridad(calc: Calculator) -> None:
    with pytest.raises(CalcSyntaxError):
        calc.evaluate("root(8)")
    with pytest.raises(CalcSyntaxError):
        calc.evaluate("root(8, 3, 2)")


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("9 // 4", 2.0),
        ("7 // 3", 2.0),
        ("9 // 3", 3.0),
        ("7.5 // 2", 3.0),  # semántica Python: acepta decimales
        ("-9 // 4", -3.0),  # redondeo hacia abajo
    ],
)
def test_division_entera(calc: Calculator, expr: str, expected: float) -> None:
    assert calc.evaluate(expr) == expected


def test_division_entera_por_cero(calc: Calculator) -> None:
    with pytest.raises(CalcMathError, match="División por cero"):
        calc.evaluate("9 // 0")


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("9 // 4", "[floor]"),
        ("sqrt(9)", "[sqrt]"),
        ("root(8, 3)", "[cbrt]"),
        ("root(16, 2)", "[sqrt]"),
        ("root(32, 5)", "[nroot]"),
        ("root(8, 3) + 9 // 4", "[cbrt] [floor]"),
        ("9 // 4 + 8 // 3", "[floor]"),  # sin repetir
        ("2 + 3", ""),  # básicas sin notación
        ("2 +", ""),  # expresión inválida
    ],
)
def test_notacion(calc: Calculator, expr: str, expected: str) -> None:
    assert calc.notation(expr) == expected


def test_variables_builtin(calc: Calculator) -> None:
    assert calc.evaluate("pi") == pytest.approx(3.141592653589793)
    assert calc.evaluate("e") == pytest.approx(2.718281828459045)


def test_asignacion_y_uso(calc: Calculator) -> None:
    assert calc.evaluate("x = 5") == 5.0
    assert calc.evaluate("x * 2") == 10.0
    assert calc.evaluate("x = y = 3") == 3.0
    assert calc.evaluate("x + y") == 6.0


def test_no_sobreescribir_builtin(calc: Calculator) -> None:
    with pytest.raises(CalcMathError, match="builtin"):
        calc.evaluate("pi = 3")


def test_variable_indefinida(calc: Calculator) -> None:
    with pytest.raises(CalcSyntaxError, match="Variable indefinida"):
        calc.evaluate("zzz + 1")


def test_errores_sintaxis_siguen_siendo_errores(calc: Calculator) -> None:
    with pytest.raises(CalcSyntaxError):
        calc.evaluate("2 +")
    with pytest.raises(CalcSyntaxError):
        calc.evaluate("2(")
    with pytest.raises(CalcSyntaxError):
        calc.evaluate("sqrt")  # falta '('
