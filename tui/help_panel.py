"""Widget de la leyenda de ayuda: operadores, notación, variables y teclas."""

import curses

_HELP_LINES = [
    "AYUDA  ·  ? o esc cerrar  ·  w/s o flechas desplazar",
    "",
    "OPERADORES",
    "  + - * /   básicos            **         potencia",
    "  //        división entera    %          módulo",
    "  !         factorial          ( )        agrupar",
    "  sqrt(x)   raíz cuadrada      root(x,n)  raíz n-ésima",
    "",
    "NOTACIÓN   [floor] div. entera · [sqrt] · [cbrt] · [nroot]",
    "VARIABLES  pi, e (constantes) · x = 5 (asignar)",
    "",
    "TECLAS",
    "  mover: w a s d o flechas (teclado, historial, variables y ayuda)",
    "  números: física 0-9 · homerow u i o = 4 5 6 · j k l = 1 2 3 · m = 0",
    "  h hints del teclado · e editar (texto libre) · c retroceder",
    "  x borrar bajo cursor (display/ítem) · X borrar todo (confirma)",
    "  tab foco · enter/space evaluar o traer · g/G inicio/fin · esc limpiar",
    "  T color · U actualizar · ? ayuda · q salir",
]


class HelpPanel:
    """Dibuja la leyenda de ayuda en la ventana central (modal, desplazable)."""

    def __init__(self, window, attrs=None) -> None:
        self.win = window
        self.attrs = attrs or {}
        self.offset = 0

    def _attr(self, role: str) -> int:
        return self.attrs.get(role, 0)

    def _visible(self, height: int) -> int:
        """Filas de contenido: si hay overflow, la última se usa de indicador."""
        return height - 1 if len(_HELP_LINES) > height else height

    def _clamp(self, height: int) -> None:
        max_off = max(0, len(_HELP_LINES) - self._visible(height))
        self.offset = max(0, min(self.offset, max_off))

    def scroll_to_top(self) -> None:
        self.offset = 0

    def scroll(self, delta: int) -> None:
        height, _ = self.win.getmaxyx()
        self.offset += delta
        self._clamp(height)

    def render(self) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 1 or width < 1:
            self.win.noutrefresh()
            return
        max_len = max(width - 1, 0)
        self._clamp(height)
        visible = self._visible(height)
        for row in range(visible):
            idx = self.offset + row
            if idx >= len(_HELP_LINES):
                break
            line = _HELP_LINES[idx]
            shown = line if len(line) <= max_len else line[:max_len]
            attr = self._attr("title") if line.isupper() else self._attr("expression")
            try:
                self.win.addstr(row, 0, shown.ljust(max_len), attr)
            except curses.error:
                pass
        if len(_HELP_LINES) > height and height >= 1:
            up = self.offset > 0
            down = self.offset + visible < len(_HELP_LINES)
            arrow = "↕" if up and down else ("↑" if up else "↓")
            more = f" {arrow}  j/k desplazar "
            self.win.addstr(height - 1, 0, more.ljust(max_len), self._attr("title"))
        self.win.noutrefresh()
