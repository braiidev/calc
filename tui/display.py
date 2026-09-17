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

        # Expresión (fila 1, alineada a la derecha con prompt)
        expr = expression if expression else " "
        self._draw_right_aligned(
            self.win,
            1,
            f"{self._glyph('prompt')} {expr}",
            width,
            attr=self._attr("expression"),
        )

        # Separador (fila 2)
        if height >= 3:
            try:
                self.win.addstr(2, 0, self._glyph("h") * width, self._attr("separator"))
            except curses.error:
                pass

        # Notación (dim, a la izquierda) y resultado/error (derecha), fila 3
        if height >= 4:
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
