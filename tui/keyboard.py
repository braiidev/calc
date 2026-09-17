"""Widget de teclado: grid de botones navegable con flechas."""

import curses
from dataclasses import dataclass
from typing import Optional

_ACTIONS = ("insert", "clear", "back", "eval", "ans")
_GRID_COLS = 6


@dataclass(frozen=True)
class KeyDef:
    label: str
    action: str = "insert"
    char: Optional[str] = None
    desc: Optional[str] = None


_KEYS = [
    [
        KeyDef("√", char="sqrt(", desc="raíz cuadrada"),
        KeyDef("root", char="root(", desc="raíz n-ésima"),
        KeyDef("**", desc="potencia"),
        KeyDef("//", desc="división entera"),
        KeyDef("%", desc="módulo"),
        KeyDef("!", desc="factorial"),
    ],
    [
        KeyDef("ANS", "ans", desc="traer último resultado"),
        KeyDef("7", desc="número"),
        KeyDef("8", desc="número"),
        KeyDef("9", desc="número"),
        KeyDef("C", "clear", desc="limpiar"),
        KeyDef("DEL", "back", desc="borrar"),
    ],
    [
        KeyDef("(", desc="paréntesis"),
        KeyDef("4", desc="número"),
        KeyDef("5", desc="número"),
        KeyDef("6", desc="número"),
        KeyDef("+", desc="sumar"),
        KeyDef("-", desc="restar"),
    ],
    [
        KeyDef(")", desc="paréntesis"),
        KeyDef("1", desc="número"),
        KeyDef("2", desc="número"),
        KeyDef("3", desc="número"),
        KeyDef("*", desc="multiplicar"),
        KeyDef("/", desc="dividir"),
    ],
    [
        KeyDef("0", desc="número"),
        KeyDef(".", desc="decimal"),
        KeyDef(",", desc="separador de argumentos"),
        KeyDef("=", "eval", desc="evaluar"),
    ],
]
_BUTTON_IDS: dict[str, tuple[int, int]] = {}
for _row in range(len(_KEYS)):
    for _col in range(len(_KEYS[_row])):
        _button = _KEYS[_row][_col]
        _BUTTON_IDS[_button.label] = (_row, _col)


class Keyboard:
    """Grid de botones con navegación por flechas y resaltado de tecla."""

    def __init__(self, window, attrs: Optional[dict[str, int]] = None) -> None:
        self.win = window
        self.attrs = attrs or {}
        self.row = 0
        self.col = 0

    def render(self, highlight: Optional[str] = None) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 1 or width < 1:
            self.win.noutrefresh()
            return

        # Centrar el grid horizontalmente
        button_w = 5
        grid_w = _GRID_COLS * button_w
        x_offset = max((width - grid_w) // 2, 0)

        for r, row in enumerate(_KEYS):
            y = r
            if y >= height:
                break
            x = x_offset
            for c, key in enumerate(row):
                focused = r == self.row and c == self.col
                attrs = self._attrs_for(key, focused, highlight)
                try:
                    self.win.addstr(y, x, f"[{key.label}]".center(button_w), attrs)
                except curses.error:
                    pass
                x += button_w
        self.win.noutrefresh()

    def _attrs_for(
        self, key: KeyDef, focused: bool, highlight: Optional[str] = None
    ) -> int:
        """Atributos del botón: color por rol + A_REVERSE si está enfocado."""
        if key.action != "insert":
            role = "action"
        elif key.label.isdigit() or key.label in (".", ","):
            role = "number"
        else:
            role = "operator"
        attrs = self.attrs.get(role, 0)
        if focused or (highlight is not None and key.label == highlight):
            attrs |= curses.A_REVERSE
        return attrs

    # ----- navegación -----

    def move(self, dr: int, dc: int) -> None:
        rows = len(_KEYS)
        cols = len(_KEYS[self.row])
        self.row = max(0, min(rows - 1, self.row + dr))
        self.col = max(0, min(cols - 1, self.col + dc))

    def focused_action(self) -> tuple[str, str]:
        """Retornar (action, char). Si no hay char, usamos el label."""
        row = _KEYS[self.row]
        key = row[min(self.col, len(row) - 1)]
        return key.action, key.char if key.char is not None else key.label

    def focused_description(self) -> Optional[str]:
        """Descripción de la tecla enfocada, o None."""
        row = _KEYS[self.row]
        key = row[min(self.col, len(row) - 1)]
        return key.desc

    def find_char(self, ch: str) -> Optional[tuple[int, int]]:
        """Resaltar botón cuyo label coincida con la tecla pulsada."""
        if ch not in _BUTTON_IDS:
            return None
        return _BUTTON_IDS[ch]

    @staticmethod
    def get_all_keys() -> list[KeyDef]:
        return [key for row in _KEYS for key in row if key.action == "insert"]
