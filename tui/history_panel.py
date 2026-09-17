"""Widget del panel de historial de operaciones."""

import curses


class HistoryPanel:
    """Muestra el historial con una entrada seleccionada (cursor) y auto-scroll."""

    def __init__(self, window, history) -> None:
        self.win = window
        self.history = history
        self.selected = -1  # índice absoluto en el historial (-1 = nada)

    def render(self) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 2 or width < 1:
            return

        # Barra superior
        try:
            self.win.addstr(0, 0, "=" * width)
        except curses.error:
            pass

        total = len(self.history)
        if total == 0:
            try:
                self.win.addstr(1, 1, "sin entradas", curses.A_DIM)
            except curses.error:
                pass
            self.win.refresh()
            return

        visible = height - 1
        if self.selected < 0:
            self.selected = total - 1
        start = 0
        if total > visible:
            start = min(max(self.selected - visible // 2, 0), total - visible)
        rows = self.history.last(total)[start : start + visible]

        for i, (expr, result) in enumerate(rows):
            y = 1 + i
            if y >= height:
                break
            cursor, attr = (" ", curses.A_DIM)
            if start + i == self.selected:
                cursor = ">"
                attr = curses.A_NORMAL
            text = f"{cursor} {expr} = {result}"
            max_len = max(width - 1, 0)
            shown = text if len(text) <= max_len else f"{text[:max_len - 3]}..."
            try:
                self.win.addstr(y, 0, shown.ljust(max_len), attr)
            except curses.error:
                pass
        self.win.refresh()

    # ----- selección -----

    def move(self, delta: int) -> None:
        """Mover la selección (±1) dentro de los límites."""
        if len(self.history) == 0:
            return
        current = self.selected if self.selected >= 0 else len(self.history) - 1
        self.selected = max(0, min(len(self.history) - 1, current + delta))

    def to_first(self) -> None:
        """Seleccionar la entrada más antigua."""
        if len(self.history):
            self.selected = 0

    def to_last(self) -> None:
        """Seleccionar la entrada más reciente."""
        if len(self.history):
            self.selected = len(self.history) - 1

    def selected_entry(self) -> tuple[str, str, int] | None:
        """(expr, result, index) de la entrada seleccionada, o None."""
        if len(self.history) == 0:
            return None
        idx = self.selected if self.selected >= 0 else len(self.history) - 1
        entry = self.history[idx]
        if entry is None:
            return None
        return entry[0], entry[1], idx

    def delete_selected(self) -> bool:
        """Eliminar la entrada seleccionada. Retorna True si se borró."""
        current = self.selected_entry()
        if current is None:
            return False
        ok = self.history.delete_at(current[2])
        if ok and len(self.history):
            self.selected = min(max(current[2] - 1, 0), len(self.history) - 1)
        else:
            self.selected = -1
        return ok

    def reset_selection(self) -> None:
        self.selected = -1  # al render se ajusta a la última
