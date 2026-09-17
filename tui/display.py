"""Widget de display: muestra la expresión y el resultado."""

import curses


class Display:
    """Zona superior: expresión actual, resultado y errores."""

    def __init__(self, window) -> None:
        self.win = window

    def render(self, expression: str, result: str, error: str = "") -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()

        # Expresión (fila 1, alineada a la derecha)
        expr = expression if expression else " "
        self._draw_right_aligned(self.win, 1, expr, width)

        # Separador
        if height >= 3:
            self.win.addstr(2, 0, "-" * width)

        # Resultado o error (fila 3)
        if height >= 4:
            body = error if error else result
            self._draw_right_aligned(self.win, 3, body, width)

        self.win.refresh()

    @staticmethod
    def _draw_right_aligned(win, row: int, text: str, width: int, pad: int = 1) -> None:
        """Dibujar texto alineado a la derecha, recortado y con padding."""
        max_len = max(width - (pad * 2), 0)
        shown = text if len(text) <= max_len else f"...{text[-(max_len - 3):]}"
        x = max(width - pad - len(shown), pad)
        try:
            win.addstr(row, x, shown)
        except curses.error:
            pass