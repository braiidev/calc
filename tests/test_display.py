"""Tests del display: barra de estado, prompt, notación y resultado."""

import curses

from tui.display import Display

_GLYPHS = {"prompt": "›", "h": "─", "warn": "⚠"}


class StubWin:
    def __init__(self, height: int, width: int) -> None:
        self.height = height
        self.width = width
        self.writes: list[tuple[int, int, str]] = []
        self.attr_writes: list[tuple[int, int, str, int]] = []

    def getmaxyx(self) -> tuple[int, int]:
        return self.height, self.width

    def erase(self) -> None:
        self.writes = []
        self.attr_writes = []

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        self.writes.append((y, x, text))
        self.attr_writes.append((y, x, text, attr))

    def refresh(self) -> None:
        pass

    def noutrefresh(self) -> None:
        pass


def _text(win: StubWin) -> str:
    return " ".join(text for _, _, text in win.writes)


def test_render_muestra_prompt_notacion_y_resultado() -> None:
    win = StubWin(5, 40)
    Display(win, {}, _GLYPHS).render(  # type: ignore[arg-type]
        "9 // 4", "2", hint="› teclado", notation="[floor]"
    )
    text = _text(win)
    assert "› 9 // 4" in text
    assert "[floor]" in text
    assert "2" in text
    assert "─" in text  # separador del tema


def test_render_error() -> None:
    win = StubWin(5, 40)
    Display(win, {}, _GLYPHS).render(  # type: ignore[arg-type]
        "1/0", "", error="División por cero"
    )
    assert "⚠ División por cero" in _text(win)


def _reversed(win: StubWin) -> list[str]:
    return [t for _, _, t, a in win.attr_writes if a & curses.A_REVERSE]


def test_render_cursor_marca_caracter() -> None:
    win = StubWin(5, 40)
    Display(win, {}, _GLYPHS).render("ab", "", cursor=1)  # type: ignore[arg-type]
    assert _reversed(win) == ["b"]


def test_render_cursor_al_final_marca_espacio() -> None:
    win = StubWin(5, 40)
    Display(win, {}, _GLYPHS).render("ab", "", cursor=2)  # type: ignore[arg-type]
    assert _reversed(win) == [" "]


def test_render_sin_cursor_no_marca() -> None:
    win = StubWin(5, 40)
    Display(win, {}, _GLYPHS).render("ab", "")  # type: ignore[arg-type]
    assert _reversed(win) == []
