"""Widget del panel de variables (builtins + usuario)."""

from typing import Callable

from models.variables import Variables
from tui.parts import compute_view, draw_frame, draw_line, overflow_text


class VarsPanel:
    """Muestra las variables con cursor, auto-scroll y borrado."""

    def __init__(
        self,
        window,
        variables: Variables,
        formatter: Callable[[float], str],
        attrs=None,
        glyphs=None,
        bordered: bool = False,
        title: str = "VARIABLES",
    ) -> None:
        self.win = window
        self.variables = variables
        self.formatter = formatter
        self.attrs = attrs or {}
        self.glyphs = glyphs or {}
        self.bordered = bordered
        self.title = title
        self.selected = -1  # índice absoluto en la lista (-1 = nada)

    def _attr(self, role: str) -> int:
        return self.attrs.get(role, 0)

    def _items(self) -> list[tuple[str, float]]:
        return list(self.variables.list_vars().items())

    def render(self, active: bool = True) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 2 or width < 1:
            self.win.noutrefresh()
            return

        title_attr = self._attr("title") if active else self._attr("title_dim")
        top, left, content_h, content_w = draw_frame(
            self.win,
            self.title,
            self.bordered,
            {**self.attrs, "title": title_attr},
            self.glyphs,
        )

        items = self._items()
        if not items:
            draw_line(
                self.win, top, left, content_w, "sin variables", self._attr("hint")
            )
            self.win.noutrefresh()
            return

        if self.selected < 0:
            self.selected = len(items) - 1
        start, count, top_ind, bottom_ind = compute_view(
            len(items), self.selected, content_h
        )

        cursor = self.glyphs.get("cursor", ">")
        row = top
        if top_ind:
            draw_line(
                self.win,
                row,
                left,
                content_w,
                overflow_text(self.glyphs, "up", start),
                self._attr("hint"),
            )
            row += 1
        for i in range(count):
            idx = start + i
            name, value = items[idx]
            cur, attr = (" ", self._attr("expression"))
            if idx == self.selected:
                cur, attr = cursor, self._attr("selection")
            text = f"{cur} {name} = {self.formatter(value)}"
            draw_line(self.win, row, left, content_w, text, attr)
            row += 1
        if bottom_ind:
            draw_line(
                self.win,
                row,
                left,
                content_w,
                overflow_text(self.glyphs, "down", len(items) - (start + count)),
                self._attr("hint"),
            )
        self.win.noutrefresh()

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
