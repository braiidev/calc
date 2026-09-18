"""Widget de teclado: grid de botones por bloques, navegable con flechas."""

import curses
from dataclasses import dataclass
from typing import Optional

_ACTIONS = ("insert", "clear", "back", "eval", "ans")
_GRID_COLS = 6
_BUTTON_W = 5  # ancho de cada celda: "[XXX]"

# Celdas None = espacios (fila en blanco o huecos del bloque numérico).


@dataclass(frozen=True)
class KeyDef:
    label: str
    action: str = "insert"
    char: Optional[str] = None
    desc: Optional[str] = None
    glyph: Optional[str] = None


_KEYS: list[list[Optional[KeyDef]]] = [
    # Bloque funciones
    [
        KeyDef("sqr", char="sqrt(", desc="raíz cuadrada", glyph="sqrt"),
        KeyDef("nrt", char="root(", desc="raíz n-ésima", glyph="nroot"),
        KeyDef("**", char="**", desc="potencia", glyph="pow"),
        KeyDef("//", desc="división entera"),
        KeyDef("%", desc="módulo"),
        KeyDef("!", char="!", desc="factorial"),
    ],
    # Bloque memoria + números + operadores
    [
        KeyDef("ANS", "ans", desc="traer último resultado"),
        KeyDef("7", desc="número"),
        KeyDef("8", desc="número"),
        KeyDef("9", desc="número"),
        KeyDef("C", "clear", desc="limpiar"),
        KeyDef("DEL", "back", desc="borrar", glyph="backspace"),
    ],
    [
        KeyDef("(", desc="paréntesis"),
        KeyDef("4", desc="número"),
        KeyDef("5", desc="número"),
        KeyDef("6", desc="número"),
        KeyDef("+", desc="sumar"),
        KeyDef("-", char="-", desc="restar", glyph="minus"),
    ],
    [
        KeyDef(")", desc="paréntesis"),
        KeyDef("1", desc="número"),
        KeyDef("2", desc="número"),
        KeyDef("3", desc="número"),
        KeyDef("*", char="*", desc="multiplicar", glyph="times"),
        KeyDef("/", char="/", desc="dividir", glyph="divide"),
    ],
    [
        None,
        KeyDef("0", desc="número"),
        KeyDef(".", desc="decimal"),
        KeyDef("=", "eval", desc="evaluar"),
        None,
        None,
    ],
]
_BUTTON_IDS: dict[str, tuple[int, int]] = {}
for _r, _row in enumerate(_KEYS):
    for _c, _key in enumerate(_row):
        if _key is not None:
            _BUTTON_IDS[_key.label] = (_r, _c)


class Keyboard:
    """Grid de botones con navegación por flechas y resaltado de tecla."""

    def __init__(
        self, window, attrs: Optional[dict[str, int]] = None, glyphs=None
    ) -> None:
        self.win = window
        self.attrs = attrs or {}
        self.glyphs = glyphs or {}
        self.row = 0
        self.col = 0

    def render(self, highlight: Optional[str] = None) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 1 or width < 1:
            self.win.noutrefresh()
            return

        # Barra divisoria: separa la sección del teclado del resto de la app.
        if height >= 1:
            try:
                self.win.addstr(
                    0,
                    0,
                    self.glyphs.get("h", "-") * width,
                    self.attrs.get("separator", 0),
                )
            except curses.error:
                pass

        grid_w = _GRID_COLS * _BUTTON_W
        # Todos los bloques comparten el mismo offset para quedar alineados.
        x_offset = max((width - grid_w) // 2, 0)

        for r, row in enumerate(_KEYS):
            if 1 + r >= height:
                break
            for c, key in enumerate(row):
                if key is None:
                    continue
                x = x_offset + c * _BUTTON_W
                if x + _BUTTON_W > width:
                    continue
                attrs = self._attrs_for(key, r == self.row and c == self.col, highlight)
                cell = f"[{self._label(key):^{_BUTTON_W - 2}}]"[:_BUTTON_W]
                try:
                    self.win.addstr(1 + r, x, cell, attrs)
                except curses.error:
                    pass
        self.win.noutrefresh()

    def _label(self, key: KeyDef) -> str:
        """Etiqueta visible: glifo Unicode si está disponible, si no el fallback."""
        if key.glyph and self.glyphs.get(key.glyph):
            return self.glyphs[key.glyph]
        return key.label

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
        inserted = key.char if key.char is not None else key.label
        if focused or (highlight is not None and inserted == highlight):
            attrs |= curses.A_REVERSE
        return attrs

    # ----- navegación -----

    def _focused(self) -> KeyDef:
        row = _KEYS[self.row]
        current = row[self.col] if 0 <= self.col < len(row) else None
        if current is not None:
            return current
        for key in row:
            if key is not None:
                return key
        return KeyDef("?")

    def move(self, dr: int, dc: int) -> None:
        if dc:
            self._move_horizontal(dc)
        if dr:
            self._move_vertical(dr)

    def _move_horizontal(self, dc: int) -> None:
        row = _KEYS[self.row]
        col = self.col + dc
        while 0 <= col < len(row):
            if row[col] is not None:
                self.col = col
                return
            col += dc

    def _move_vertical(self, dr: int) -> None:
        row = self.row + dr
        while 0 <= row < len(_KEYS):
            if any(key is not None for key in _KEYS[row]):
                self.row = row
                self.col = self._nearest_col(row, self.col)
                return
            row += dr

    @staticmethod
    def _nearest_col(row: int, col: int) -> int:
        keys = _KEYS[row]
        col = max(0, min(len(keys) - 1, col))
        for delta in range(len(keys)):
            for candidate in (col - delta, col + delta):
                if 0 <= candidate < len(keys) and keys[candidate] is not None:
                    return candidate
        return 0

    def focused_action(self) -> tuple[str, str]:
        """Retornar (action, char). Si no hay char, usamos el label."""
        key = self._focused()
        return key.action, key.char if key.char is not None else key.label

    def focused_description(self) -> Optional[str]:
        """Descripción de la tecla enfocada, o None."""
        return self._focused().desc

    def find_char(self, ch: str) -> Optional[tuple[int, int]]:
        """Resaltar botón cuyo label coincida con la tecla pulsada."""
        if ch not in _BUTTON_IDS:
            return None
        return _BUTTON_IDS[ch]

    @staticmethod
    def get_all_keys() -> list[KeyDef]:
        return [
            key
            for row in _KEYS
            for key in row
            if key is not None and key.action == "insert"
        ]
