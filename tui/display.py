"""Widget de display: muestra la expresión, el resultado y la notación."""

import curses
from typing import Optional

_FALLBACK_GLYPHS = {"prompt": ">", "h": "-", "warn": "!"}


class Display:
    """Zona superior: barra de estado, expresión, resultado y errores."""

    def __init__(
        self,
        window,
        attrs: Optional[dict[str, int]] = None,
        glyphs: Optional[dict[str, str]] = None,
    ) -> None:
        self.win = window
        self.attrs = attrs or {}
        self.glyphs = {**_FALLBACK_GLYPHS, **(glyphs or {})}

    def _attr(self, role: str) -> int:
        return self.attrs.get(role, 0)

    def _glyph(self, name: str) -> str:
        return self.glyphs.get(name, _FALLBACK_GLYPHS.get(name, ""))

    def render(
        self,
        expression: str,
        result: str,
        error: str = "",
        hint: str = "",
        notation: str = "",
        cursor: Optional[int] = None,
    ) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()

        # Barra de estado (fila 0)
        self._draw_left_aligned(
            self.win,
            0,
            hint if hint else "q salir · esc limpiar",
            width,
            attr=self._attr("hint"),
        )

        # Divisor: separa la barra de estado del display (fila 1)
        if height >= 2:
            try:
                self.win.addstr(1, 0, self._glyph("h") * width, self._attr("separator"))
            except curses.error:
                pass

        # Expresión (fila 2, alineada a la derecha, con cursor opcional)
        self._draw_expression(expression, width, cursor, row=2)

        # Separador (fila 3)
        if height >= 4:
            try:
                self.win.addstr(3, 0, self._glyph("h") * width, self._attr("separator"))
            except curses.error:
                pass

        # Notación (dim, a la izquierda) y resultado/error (derecha), fila 4
        if height >= 5:
            if notation:
                self._draw_left_aligned(
                    self.win, 3, notation, width, attr=self._attr("hint")
                )
            if error:
                self._draw_right_aligned(
                    self.win,
                    3,
                    f"{self._glyph('warn')} {error}",
                    width,
                    attr=self._attr("error"),
                )
            else:
                self._draw_right_aligned(
                    self.win, 3, result, width, attr=self._attr("result")
                )

        self.win.noutrefresh()

    def _draw_expression(
        self,
        expression: str,
        width: int,
        cursor: Optional[int],
        row: int = 1,
    ) -> None:
        """Dibujar la expresión con prompt; si `cursor` no es None, marcarlo."""
        pad = 1
        prefix = f"{self._glyph('prompt')} "
        expr = expression if expression else " "
        full = prefix + expr
        max_len = max(width - (pad * 2), 0)
        if len(full) <= max_len:
            shown = full
            dropped = 0
        else:
            kept = max(max_len - 3, 0)
            shown = f"...{full[-kept:]}" if kept else "..."
            dropped = len(full) - len(shown)
        x = max(width - pad - len(shown), pad)
        attr = self._attr("expression")
        try:
            self.win.addstr(row, x, shown, attr)
        except curses.error:
            pass
        if cursor is None:
            return
        text_idx = len(prefix) + min(max(cursor, 0), len(expr))
        shown_idx = text_idx - dropped
        if shown_idx < 0 or x + shown_idx >= width:
            return
        char = expr[cursor] if 0 <= cursor < len(expr) else " "
        try:
            self.win.addstr(row, x + shown_idx, char, attr | curses.A_REVERSE)
        except curses.error:
            pass

    @staticmethod
    def _draw_left_aligned(
        win, row: int, text: str, width: int, pad: int = 1, attr: int = 0
    ) -> None:
        """Dibujar texto alineado a la izquierda, recortado y con padding."""
        max_len = max(width - (pad * 2), 0)
        shown = text if len(text) <= max_len else f"{text[:max_len - 3]}..."
        try:
            win.addstr(row, pad, shown, attr)
        except curses.error:
            pass

    @staticmethod
    def _draw_right_aligned(
        win, row: int, text: str, width: int, pad: int = 1, attr: int = 0
    ) -> None:
        """Dibujar texto alineado a la derecha, recortado y con padding."""
        max_len = max(width - (pad * 2), 0)
        shown = text if len(text) <= max_len else f"...{text[-(max_len - 3):]}"
        x = max(width - pad - len(shown), pad)
        try:
            win.addstr(row, x, shown, attr)
        except curses.error:
            pass
