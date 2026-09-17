"""Tests del teclado: descripción, navegación por bloques y glifos."""

from tui.keyboard import Keyboard


class StubWin:
    def __init__(self, height: int, width: int) -> None:
        self.height = height
        self.width = width
        self.lines: list[str] = []
        self.cells: list[tuple[int, int, str]] = []

    def getmaxyx(self) -> tuple[int, int]:
        return self.height, self.width

    def erase(self) -> None:
        self.lines = []
        self.cells = []

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        self.lines.append(text)
        self.cells.append((y, x, text))

    def noutrefresh(self) -> None:
        pass


def make_kb(glyphs=None) -> Keyboard:
    return Keyboard(None, {}, glyphs)  # type: ignore[arg-type]


def test_descripcion_primera_tecla() -> None:
    assert make_kb().focused_description() == "raíz cuadrada"


def test_descripcion_segun_posicion() -> None:
    kb = make_kb()
    kb.col = 2
    assert kb.focused_description() == "potencia"
    kb.row = 5
    kb.col = 3
    assert kb.focused_description() == "evaluar"


def test_descripcion_acota_columna() -> None:
    kb = make_kb()
    kb.row = 5
    kb.col = 99
    assert kb.focused_description() == "número"  # cae a la primera válida


def test_navegacion_salta_fila_en_blanco() -> None:
    kb = make_kb()
    kb.move(1, 0)  # fila 1 está vacía -> baja a la 2
    assert kb.row == 2
    assert kb.focused_description() == "traer último resultado"


def test_navegacion_ignora_huecos() -> None:
    kb = make_kb()
    kb.row = 5
    kb.col = 1
    kb.move(0, -1)  # col 0 es hueco: no se mueve
    assert kb.col == 1
    kb.move(0, 1)
    assert kb.col == 2


def test_accion_de_boton_con_glifo() -> None:
    kb = make_kb()
    kb.row = 4
    kb.col = 4  # × -> inserta "*"
    assert kb.focused_action() == ("insert", "*")
    kb.col = 5  # ÷ -> inserta "/"
    assert kb.focused_action() == ("insert", "/")


def test_render_usa_glifos_unicode() -> None:
    win = StubWin(6, 80)
    Keyboard(win, {}, {"times": "×", "divide": "÷"}).render()  # type: ignore[arg-type]
    text = " ".join(win.lines)
    assert "×" in text
    assert "÷" in text


def test_render_fallback_ascii() -> None:
    win = StubWin(6, 80)
    Keyboard(win, {}, {"times": "*", "divide": "/"}).render()  # type: ignore[arg-type]
    text = " ".join(win.lines)
    assert "×" not in text
    assert "*" in text


def test_get_all_keys() -> None:
    assert len(Keyboard.get_all_keys()) == 23


def test_bloques_alineados_al_mismo_offset() -> None:
    win = StubWin(6, 80)
    Keyboard(win, {}).render()  # type: ignore[arg-type]
    xs = {text: x for _, x, text in win.cells}
    assert xs["[sqr]"] == xs["[ANS]"]  # funciones y pad comparten offset
