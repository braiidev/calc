"""Widget de teclado: grid de botones navegable con flechas."""

import curses
from dataclasses import dataclass
from typing import Optional

# Pares de color (inicializados desde la app)
PAIR_NUM = 1
PAIR_OP = 2
PAIR_ACTION = 3

_ACTIONS = ("insert", "clear", "back", "eval", "ans")


@dataclass(frozen=True)
class KeyDef:
    label: str
    action: str = "insert"
    char: Optional[str] = None


_KEYS = [
    [KeyDef("√", char="sqrt("), KeyDef("**"), KeyDef("%"), KeyDef("!"), KeyDef("ANS", "ans")],
    [KeyDef("7"), KeyDef("8"), KeyDef("9"), KeyDef("C", "clear"), KeyDef("DEL", "back")],
    [KeyDef("4"), KeyDef("5"), KeyDef("6"), KeyDef("+"), KeyDef("-")],
    [KeyDef("1"), KeyDef("2"), KeyDef("3"), KeyDef("*"), KeyDef("/")],
    [KeyDef("0"), KeyDef("."), KeyDef("("), KeyDef(")"), KeyDef("=", "eval")],
]
_BUTTON_IDS: dict[str, tuple[int, int]] = {}
for _row in range(len(_KEYS)):
    for _col in range(len(_KEYS[_row])):
        _button = _KEYS[_row][_col]
        _BUTTON_IDS[_button.label] = (_row, _col)


class Keyboard:
    """Grid de botones con navegación por flechas y resaltado de tecla."""

    def __init__(self, window) -> None:
        self.win = window
        self.row = 0
        self.col = 0
        self.use_colors = curses.has_colors()

    def render(self, highlight: Optional[str] = None) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 1 or width < 1:
            return

        # Centrar el grid horizontalmente
        button_w = 5
        grid_w = len(_KEYS[0]) * button_w
        x_offset = max((width - grid_w) // 2, 0)

        for r, row in enumerate(_KEYS):
            y = r
            if y >= height:
                break
            x = x_offset
            for c, key in enumerate(row):
                focused = (r == self.row and c == self.col)
                attrs = self._attrs_for(key, focused, highlight)
                try:
                    self.win.addstr(y, x, f"[{key.label}]".center(button_w), attrs)
                except curses.error:
                    pass
                x += button_w
        self.win.refresh()

    def _attrs_for(self, key: KeyDef, focused: bool, highlight: Optional[str] = None) -> int:
        """Atributos del botón: A_REVERSE + color (A_REVERSE funciona sin soporte de color)."""
        attrs = 0
        if focused or (highlight is not None and key.label == highlight):
            attrs |= curses.A_REVERSE
        if self.use_colors:
            if key.action == "insert":
                if key.label.isdigit() or key.label == ".":
                    pair = PAIR_NUM
                else:
                    pair = PAIR_OP
            else:
                pair = PAIR_ACTION
            attrs |= curses.color_pair(pair)
        return attrs

    # ----- navegación -----

    def move(self, dr: int, dc: int) -> None:
        rows, cols = len(_KEYS), len(_KEYS[0])
        self.row = max(0, min(rows - 1, self.row + dr))
        self.col = max(0, min(cols - 1, self.col + dc))

    def focused_action(self) -> tuple[str, str]:
        """Retornar (action, char). Si no hay char, usamos el label."""
        key = _KEYS[self.row][self.col]
        return key.action, key.char if key.char is not None else key.label

    def find_char(self, ch: str) -> Optional[int]:
        """Resaltar botón cuyo label coincida con la tecla pulsada."""
        if ch not in _BUTTON_IDS:
            return None
        return _BUTTON_IDS[ch]

    @staticmethod
    def get_all_keys() -> list[KeyDef]:
        return [key for row in _KEYS for key in row if key.action == "insert"]