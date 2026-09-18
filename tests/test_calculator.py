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


# ---------------- funciones de usuario ----------------


def test_define_y_usa_funcion(calc: Calculator) -> None:
    assert calc.define("regla3(a,b,c) = b*c/a") == "regla3"
    assert calc.evaluate("regla3(10, 48, 5)") == pytest.approx(24.0)


def test_define_no_es_evaluacion(calc: Calculator) -> None:
    assert calc.define("2 + 2") is None
    assert calc.define("x = 5") is None


def test_is_definition(calc: Calculator) -> None:
    assert calc.is_definition("f(x) = x * 2")
    assert not calc.is_definition("f(x) * 2")
    assert not calc.is_definition("2 + 2")


def test_funcion_en_expresion(calc: Calculator) -> None:
    calc.define("regla3(a,b,c) = b*c/a")
    assert calc.evaluate("regla3(100, 20, 4) * 2") == pytest.approx(1.6)


def test_funcion_usa_variables_y_constantes(calc: Calculator) -> None:
    calc.evaluate("x = 2")
    calc.define("doble(z) = z * x")
    assert calc.evaluate("doble(5)") == pytest.approx(10.0)


def test_funcion_compone_otras_funciones(calc: Calculator) -> None:
    calc.define("regla3(a,b,c) = b*c/a")
    calc.define("iva(m) = regla3(100, m, 121)")
    assert calc.evaluate("iva(1000)") == pytest.approx(1210.0)


def test_redefinir_funcion(calc: Calculator) -> None:
    calc.define("f(x) = x + 1")
    assert calc.evaluate("f(1)") == pytest.approx(2.0)
    calc.define("f(x) = x * 10")
    assert calc.evaluate("f(1)") == pytest.approx(10.0)


def test_reservados_no_redefinibles(calc: Calculator) -> None:
    for name in ("sqrt", "root", "pi", "e"):
        with pytest.raises(CalcSyntaxError, match="redefinir"):
            calc.define(f"{name}(x) = x")
    with pytest.raises(CalcSyntaxError, match="reservado"):
        calc.define("f(pi) = pi")
    with pytest.raises(CalcSyntaxError, match="duplicado"):
        calc.define("f(x,x) = x")


def test_aridad_incorrecta(calc: Calculator) -> None:
    calc.define("regla3(a,b,c) = b*c/a")
    with pytest.raises(CalcMathError, match="3 argumento"):
        calc.evaluate("regla3(1, 2)")


def test_recursion_con_limite(calc: Calculator) -> None:
    calc.define("loop(n) = loop(n + 1)")
    with pytest.raises(CalcMathError, match="Recursi"):
        calc.evaluate("loop(0)")


def test_funcion_desconocida(calc: Calculator) -> None:
    with pytest.raises(CalcMathError, match="desconocida"):
        calc.evaluate("nope(3)")


def test_persistencia_roundtrip(calc: Calculator) -> None:
    calc.define("regla3(a,b,c) = b*c/a")
    data = calc.functions.user_functions()
    assert data == [{"name": "regla3", "params": ["a", "b", "c"], "body": "b*c/a"}]
    otro = Calculator()
    otro.functions.load_user_functions(data)
    assert otro.evaluate("regla3(10, 48, 5)") == pytest.approx(24.0)


def test_load_ignora_invalidos() -> None:
    from models.functions import Functions

    store = Functions()
    store.load_user_functions(
        [
            {"name": "ok", "params": ["x"], "body": "x * 2"},
            {"name": "bad", "params": ["x"], "body": "x +"},  # cuerpo inválido
            {"name": "sqrt", "params": ["x"], "body": "x"},
            "basura",  # type: ignore[list-item]
        ]
    )
    assert [f.signature() for f in store.list_functions()] == ["ok(x)"]
