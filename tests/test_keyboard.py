"""Tests del teclado: descripción de la tecla enfocada."""

from tui.keyboard import Keyboard


def make_kb() -> Keyboard:
    return Keyboard(None, {})  # type: ignore[arg-type]


def test_descripcion_primera_tecla() -> None:
    assert make_kb().focused_description() == "raíz cuadrada"


def test_descripcion_segun_posicion() -> None:
    kb = make_kb()
    kb.col = 2
    assert kb.focused_description() == "potencia"
    kb.row = 4
    kb.col = 3
    assert kb.focused_description() == "evaluar"


def test_descripcion_acota_columna() -> None:
    kb = make_kb()
    kb.row = 4
    kb.col = 99
    assert kb.focused_description() == "evaluar"
