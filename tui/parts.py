"""Helpers compartidos de paneles: marco/título y ventana visible (overflow)."""

import curses

_FALLBACK_GLYPHS = {"cursor": ">", "up": "^", "down": "v", "h": "-"}


def fit(text: str, width: int) -> str:
    """Recortar `text` a `width` columnas, con elipsis ASCII si no entra."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return f"{text[:width - 3]}..."


def draw_line(win, row: int, left: int, width: int, text: str, attr: int = 0) -> None:
    """Dibujar una línea de contenido recortada y rellenada a `width`."""
    if width <= 0:
        return
    try:
        win.addstr(row, left, fit(text, width).ljust(width), attr)
    except curses.error:
        pass


def draw_frame(win, title: str, bordered: bool, attrs: dict, glyphs: dict) -> tuple:
    """Dibujar marco/título; retorna (top, left, content_h, content_w).

    Con `bordered` se dibuja una caja y el título va en el borde superior; si no,
    se usa una fila de título y una de separador.
    """
    height, width = win.getmaxyx()
    if bordered:
        _draw_box(win)
        if width > 6:
            label = fit(f" {title} ", width - 4)
            try:
                win.addstr(0, 2, label, attrs.get("title", 0))
            except curses.error:
                pass
        return 1, 2, max(height - 2, 0), max(width - 4, 0)

    if height >= 1:
        try:
            win.addstr(0, 1, fit(title, max(width - 1, 0)), attrs.get("title", 0))
        except curses.error:
            pass
    if height >= 2:
        line = glyphs.get("h", "-") * width
        try:
            win.addstr(1, 0, line, attrs.get("separator", 0))
        except curses.error:
            pass
    return 2, 1, max(height - 2, 0), max(width - 1, 0)


def compute_view(total: int, selected: int, avail: int) -> tuple[int, int, bool, bool]:
    """Ventana visible con auto-scroll centrado.

    Retorna (start, count, top_indicator, bottom_indicator). Los indicadores
    reservan una fila cada uno cuando hay ítems ocultos.
    """
    if avail <= 0 or total <= 0:
        return 0, 0, False, False
    idx = selected if selected >= 0 else total - 1
    if avail < 3:  # poco espacio: sin indicadores
        start = 0 if total <= avail else min(max(idx - avail // 2, 0), total - avail)
        return start, min(avail, total), False, False

    top_ind = bottom_ind = False
    start, count = 0, min(avail, total)
    for _ in range(4):
        usable = max(avail - int(top_ind) - int(bottom_ind), 1)
        count = min(usable, total)
        if total <= usable:
            start = 0
        else:
            start = min(max(idx - usable // 2, 0), total - usable)
        new_top, new_bottom = start > 0, start + count < total
        if (new_top, new_bottom) == (top_ind, bottom_ind):
            break
        top_ind, bottom_ind = new_top, new_bottom
    return start, count, top_ind, bottom_ind


def overflow_text(glyphs: dict, direction: str, count: int) -> str:
    """Texto del indicador de overflow, p. ej. `↑ 3 más`."""
    arrow = glyphs.get(direction, _FALLBACK_GLYPHS.get(direction, ""))
    return f"{arrow} {count} más"


def _draw_box(win) -> None:
    box = getattr(win, "box", None)
    if box is None:
        return
    try:
        box()
    except curses.error:
        pass
