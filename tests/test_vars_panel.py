"""Tests del panel de variables/funciones (lógica y render sin curses)."""

from calculator import Parser, tokenize
from models.functions import Functions
from models.variables import Variables
from tui.vars_panel import VarsPanel


class FakeWin:
    def __init__(self, h: int, w: int) -> None:
        self.h, self.w = h, w
        self.calls: list[tuple[int, int, str, int]] = []

    def getmaxyx(self) -> tuple[int, int]:
        return (self.h, self.w)

    def erase(self) -> None:
        pass

    def addstr(self, y: int, x: int, s: str, attr: int = 0) -> None:
        self.calls.append((y, x, s, attr))

    def addnstr(self, y: int, x: int, s: str, n: int, attr: int = 0) -> None:
        self.calls.append((y, x, s[:n], attr))

    def noutrefresh(self) -> None:
        pass


def _panel(glyphs: dict | None = None, attrs: dict | None = None) -> VarsPanel:
    variables = Variables()
    variables.load_user_vars({"x": 5.0})
    functions = Functions()
    functions.define(
        "regla3",
        ["a", "b", "c"],
        Parser(tokenize("b*c/a")).parse(),
        "b*c/a",
    )
    return VarsPanel(
        FakeWin(12, 40),
        variables,
        str,
        attrs or {},
        glyphs or {},
        True,
        functions=functions,
    )


def _sel_name(panel: VarsPanel) -> str:
    entry = panel.selected_entry()
    assert entry is not None
    return entry.name


def test_entradas_variables_luego_funciones() -> None:
    panel = _panel()
    assert [e.kind for e in panel._entries()] == [
        "var",
        "var",
        "var",
        "func",
    ]
    assert [e.name for e in panel._entries()] == [
        "pi",
        "e",
        "x",
        "regla3",
    ]
    assert _sel_name(panel) == "regla3"  # última entrada


def test_movimiento_seleccion() -> None:
    panel = _panel()
    panel.move(-1)
    assert _sel_name(panel) == "x"
    panel.move(1)
    assert _sel_name(panel) == "regla3"
    panel.to_first()
    assert _sel_name(panel) == "pi"
    panel.to_last()
    assert _sel_name(panel) == "regla3"


def test_delete_funcion() -> None:
    panel = _panel()
    panel.selected = len(panel._entries()) - 1
    assert panel.delete_selected() is True
    assert [e.name for e in panel._entries()] == ["pi", "e", "x"]
    assert _sel_name(panel) == "x"


def test_delete_variable() -> None:
    panel = _panel()
    names = [e.name for e in panel._entries()]
    panel.selected = names.index("x")
    assert panel.delete_selected() is True
    assert "x" not in [e.name for e in panel._entries()]


def test_delete_builtin_no_borra() -> None:
    panel = _panel()
    panel.selected = 0  # pi, constante
    assert panel.delete_selected() is False
    assert len(panel._entries()) == 4


def test_seleccion_por_defecto_sin_datos_usuario() -> None:
    panel = VarsPanel(FakeWin(12, 40), Variables(), str, {}, {}, True)
    assert [e.name for e in panel._entries()] == ["pi", "e"]
    assert _sel_name(panel) == "e"  # última (builtin)
    panel.move(1)
    assert _sel_name(panel) == "e"


def test_render_marca_seleccion() -> None:
    panel = _panel({"cursor": "▶", "up": "↑", "down": "↓"}, {"selection": 1})
    panel.selected = len(panel._entries()) - 1
    panel.render()
    marked = [s for (_, _, s, _) in panel.win.calls if "▶" in s]
    assert len(marked) == 1
    assert "regla3" in marked[0]
    assert "pi = " in [s for (_, _, s, _) in panel.win.calls if "pi" in s][0]
