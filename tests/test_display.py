"""Tests del display: barra de estado, prompt, notación y resultado."""

from tui.display import Display

_GLYPHS = {"prompt": "›", "h": "─", "warn": "⚠"}


class StubWin:
    def __init__(self, height: int, width: int) -> None:
        self.height = height
        self.width = width
        self.writes: list[tuple[int, int, str]] = []

    def getmaxyx(self) -> tuple[int, int]:
        return self.height, self.width

    def erase(self) -> None:
        self.writes = []

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        self.writes.append((y, x, text))

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
