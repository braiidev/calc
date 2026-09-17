"""Widget del panel de historial de operaciones."""

import curses


class HistoryPanel:
    """Muestra las últimas operaciones evaluadas, con scroll vertical."""

    def __init__(self, window, history) -> None:
        self.win = window
        self.history = history
        self.offset = 0  # 0 = desde el final (las más recientes)

    def render(self) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 2 or width < 1:
            return

        # Título
        title = " HISTORIAL "
        hbar = "=" * width
        line = f" {title}".ljust(width)
        try:
            self.win.addstr(0, 0, hbar)
        except curses.error:
            pass

        entries = self.history.last(self.offset + (height - 1))[: height - 1]
        start = max(len(entries) - (height - 1), 0)
        for i, (expr, result) in enumerate(entries[start:]):
            y = 1 + i
            if y >= height:
                break
            text = f"{expr} = {result}"
            max_len = max(width - 1, 0)
            shown = text if len(text) <= max_len else f"...{text[-(max_len - 3):]}"
            try:
                self.win.addstr(y, 0, shown, curses.A_DIM)
            except curses.error:
                pass
        self.win.refresh()

    # ----- scroll -----

    def scroll(self, delta: int) -> None:
        """Desplazar el scroll (1 = hacia entradas más antiguas)."""
        max_offset = max(self.history.length() - 1, 0)
        self.offset = max(0, min(max_offset, self.offset + delta))

    def reset_scroll(self) -> None:
        self.offset = 0