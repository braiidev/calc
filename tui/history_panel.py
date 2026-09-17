"""Widget del panel de historial de operaciones."""

import curses

from models.history import HistoryEntry


class HistoryPanel:
    """Muestra el historial con una entrada seleccionada (cursor) y auto-scroll."""

    def __init__(self, window, history, attrs=None) -> None:
        self.win = window
        self.history = history
        self.attrs = attrs or {}
        self.selected = -1  # índice absoluto en el historial (-1 = nada)

    def _attr(self, role: str) -> int:
        return self.attrs.get(role, 0)

    def render(self) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 2 or width < 1:
            return

        # Barra superior
        try:
            self.win.addstr(0, 0, "=" * width, self._attr("separator"))
        except curses.error:
            pass

        total = len(self.history)
        if total == 0:
            try:
                self.win.addstr(1, 1, "sin entradas", self._attr("hint"))
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

        for i, entry in enumerate(rows):
            y = 1 + i
            if y >= height:
                break
            cursor, attr = (" ", self._attr("expression"))
            if start + i == self.selected:
                cursor = ">"
                attr = self._attr("selection")
            text = f"{cursor} {entry.expr} = {entry.result}"
            if entry.notation:
                text += f"  {entry.notation}"
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

    def selected_entry(self) -> tuple[HistoryEntry, int] | None:
        """(entrada, index) de la seleccionada, o None."""
        if len(self.history) == 0:
            return None
        idx = self.selected if self.selected >= 0 else len(self.history) - 1
        entry = self.history[idx]
        if entry is None:
            return None
        return entry, idx

    def delete_selected(self) -> bool:
        """Eliminar la entrada seleccionada. Retorna True si se borró."""
        current = self.selected_entry()
        if current is None:
            return False
        idx = current[1]
        ok = self.history.delete_at(idx)
        if ok and len(self.history):
            self.selected = min(max(idx - 1, 0), len(self.history) - 1)
        else:
            self.selected = -1
        return ok

    def reset_selection(self) -> None:
        self.selected = -1  # al render se ajusta a la última
