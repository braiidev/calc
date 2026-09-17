"""Widget del panel de historial de operaciones."""

from models.history import HistoryEntry
from tui.parts import compute_view, draw_frame, draw_line, overflow_text


class HistoryPanel:
    """Muestra el historial con una entrada seleccionada (cursor) y auto-scroll."""

    def __init__(
        self,
        window,
        history,
        attrs=None,
        glyphs=None,
        bordered: bool = False,
        title: str = "HISTORIAL",
    ) -> None:
        self.win = window
        self.history = history
        self.attrs = attrs or {}
        self.glyphs = glyphs or {}
        self.bordered = bordered
        self.title = title
        self.selected = -1  # índice absoluto en el historial (-1 = nada)

    def _attr(self, role: str) -> int:
        return self.attrs.get(role, 0)

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

        total = len(self.history)
        if total == 0:
            draw_line(
                self.win, top, left, content_w, "sin entradas", self._attr("hint")
            )
            self.win.noutrefresh()
            return

        if self.selected < 0:
            self.selected = total - 1
        start, count, top_ind, bottom_ind = compute_view(
            total, self.selected, content_h
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
            entry = self.history[idx]
            if entry is None:
                continue
            cur, attr = (" ", self._attr("expression"))
            if idx == self.selected:
                cur, attr = cursor, self._attr("selection")
            text = f"{cur} {entry.expr} = {entry.result}"
            if entry.notation:
                text += f"  {entry.notation}"
            draw_line(self.win, row, left, content_w, text, attr)
            row += 1
        if bottom_ind:
            draw_line(
                self.win,
                row,
                left,
                content_w,
                overflow_text(self.glyphs, "down", total - (start + count)),
                self._attr("hint"),
            )
        self.win.noutrefresh()

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
