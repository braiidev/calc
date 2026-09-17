"""Tests del panel de historial: formato crudo + notación semántica."""

from models.history import History
from tui.history_panel import HistoryPanel


class StubWin:
    """Ventana mínima que captura lo escrito, sin curses real."""

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


def test_render_incluye_notacion() -> None:
    win = StubWin(10, 40)
    hist = History()
    hist.add("9 // 4", "2", "[floor]")
    HistoryPanel(win, hist).render()  # type: ignore[arg-type]
    text = " ".join(win.lines)
    assert "9 // 4 = 2" in text
    assert "[floor]" in text


def test_render_sin_notacion() -> None:
    win = StubWin(10, 40)
    hist = History()
    hist.add("2+3", "5")
    HistoryPanel(win, hist).render()  # type: ignore[arg-type]
    text = " ".join(win.lines)
    assert "2+3 = 5" in text


def test_render_muestra_overflow() -> None:
    win = StubWin(5, 30)
    hist = History()
    for i in range(10):
        hist.add(f"{i}+1", str(i + 1))
    HistoryPanel(win, hist).render()  # type: ignore[arg-type]
    text = " ".join(win.lines)
    assert "más" in text


class StubBoxWin(StubWin):
    def __init__(self, height: int, width: int) -> None:
        super().__init__(height, width)
        self.boxed = False

    def box(self) -> None:
        self.boxed = True


def test_render_bordered_dibuja_caja_y_titulo() -> None:
    win = StubBoxWin(10, 40)
    hist = History()
    hist.add("2+3", "5")
    HistoryPanel(win, hist, bordered=True, title="HISTORIAL").render()  # type: ignore[arg-type]
    text = " ".join(win.lines)
    assert win.boxed is True
    assert "HISTORIAL" in text
    assert "2+3 = 5" in text
