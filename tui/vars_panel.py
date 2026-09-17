"""Widget del panel de variables (builtins + usuario)."""

import curses
from typing import Callable

from models.variables import Variables


class VarsPanel:
    """Muestra las variables con cursor, auto-scroll y borrado."""

    def __init__(
        self, window, variables: Variables, formatter: Callable[[float], str]
    ) -> None:
        self.win = window
        self.variables = variables
        self.formatter = formatter
        self.selected = -1  # índice absoluto en la lista (-1 = nada)

    def _items(self) -> list[tuple[str, float]]:
        return list(self.variables.list_vars().items())

    def render(self) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 2 or width < 1:
            return

        try:
            self.win.addstr(0, 0, "=" * width)
        except curses.error:
            pass

        items = self._items()
        if not items:
            try:
                self.win.addstr(1, 1, "sin variables", curses.A_DIM)
            except curses.error:
                pass
            self.win.refresh()
            return

        visible = height - 1
        if self.selected < 0:
            self.selected = len(items) - 1
        start = 0
        if len(items) > visible:
            start = min(max(self.selected - visible // 2, 0), len(items) - visible)
        rows = items[start : start + visible]

        for i, (name, value) in enumerate(rows):
            y = 1 + i
            if y >= height:
                break
            cursor, attr = (" ", curses.A_DIM)
            if start + i == self.selected:
                cursor = ">"
                attr = curses.A_NORMAL
            text = f"{cursor} {name} = {self.formatter(value)}"
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
        total = len(self._items())
        if total == 0:
            return
        current = self.selected if self.selected >= 0 else total - 1
        self.selected = max(0, min(total - 1, current + delta))

    def to_first(self) -> None:
        if self._items():
            self.selected = 0

    def to_last(self) -> None:
        total = len(self._items())
        if total:
            self.selected = total - 1

    def selected_var(self) -> tuple[str, float] | None:
        """(name, value) de la variable seleccionada, o None."""
        items = self._items()
        if not items:
            return None
        idx = self.selected if self.selected >= 0 else len(items) - 1
        return items[idx]

    def delete_selected(self) -> bool:
        """Eliminar la variable seleccionada (solo de usuario)."""
        current = self.selected_var()
        if current is None:
            return False
        ok = self.variables.delete(current[0])
        if ok:
            total = len(self._items())
            self.selected = min(max(self.selected - 1, 0), total - 1) if total else -1
        return ok

    def reset_selection(self) -> None:
        self.selected = -1
