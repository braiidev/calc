"""Widget de display: muestra la expresión y el resultado."""

import curses
from typing import Optional


class Display:
    """Zona superior: expresión actual, resultado y errores."""

    def __init__(self, window, attrs: Optional[dict[str, int]] = None) -> None:
        self.win = window
        self.attrs = attrs or {}

    def _attr(self, role: str) -> int:
        return self.attrs.get(role, 0)

    def render(
        self, expression: str, result: str, error: str = "", hint: str = ""
    ) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()

        # Hint (fila 0)
        self._draw_left_aligned(
            self.win,
            0,
            hint if hint else "q salir · esc limpiar",
            width,
            attr=self._attr("hint"),
        )

        # Expresión (fila 1, alineada a la derecha)
        expr = expression if expression else " "
        self._draw_right_aligned(
            self.win, 1, expr, width, attr=self._attr("expression")
        )

        # Separador
        if height >= 3:
            self.win.addstr(2, 0, "-" * width, self._attr("separator"))

        # Resultado o error (fila 3)
        if height >= 4:
            if error:
                self._draw_right_aligned(
                    self.win, 3, error, width, attr=self._attr("error")
                )
            else:
                self._draw_right_aligned(
                    self.win, 3, result, width, attr=self._attr("result")
                )

        self.win.refresh()

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
