"""Tests de la leyenda de ayuda: render sin curses real."""

from tui.help_panel import HelpPanel


class StubWin:
    def __init__(self, height: int, width: int) -> None:
        self.height = height
        self.width = width
        self.lines: list[str] = []

    def getmaxyx(self) -> tuple[int, int]:
        return self.height, self.width

    def erase(self) -> None:
        self.lines = []

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        self.lines.append(text)

    def refresh(self) -> None:
        pass

    def noutrefresh(self) -> None:
        pass


def test_render_muestra_secciones() -> None:
    win = StubWin(20, 60)
    HelpPanel(win).render()  # type: ignore[arg-type]
    text = "\n".join(win.lines)
    assert "OPERADORES" in text
    assert "TECLAS" in text
    assert "root(x,n)" in text


def test_render_trunca_si_es_bajo() -> None:
    win = StubWin(3, 60)
    HelpPanel(win).render()  # type: ignore[arg-type]
    assert len(win.lines) <= 3


def test_render_muestra_indicador_con_overflow() -> None:
    win = StubWin(3, 60)
    panel = HelpPanel(win)
    panel.render()  # type: ignore[arg-type]
    assert any("desplazar" in line for line in win.lines)


def test_scroll_respeta_limites() -> None:
    win = StubWin(4, 60)
    panel = HelpPanel(win)
    panel.scroll(-1)
    assert panel.offset == 0
    panel.scroll(100)
    panel.render()  # type: ignore[arg-type]
    assert panel.offset > 0
    panel.scroll_to_top()
    assert panel.offset == 0
