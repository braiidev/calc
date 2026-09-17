"""Widget de la leyenda de ayuda: operadores, notación, variables y teclas."""

import curses

_HELP_LINES = [
    "AYUDA  ·  ? o esc para cerrar",
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
    "  e editar (texto libre) · enter/space evaluar · esc salir de edición",
    "  tab foco · enter/space evaluar o traer valor",
    "  esc/D limpiar · c borrar · d borrar ítem · q salir",
    "  T color · U actualizar · ? ayuda",
]


class HelpPanel:
    """Dibuja la leyenda de ayuda en la ventana central (modal)."""

    def __init__(self, window, attrs=None) -> None:
        self.win = window
        self.attrs = attrs or {}

    def _attr(self, role: str) -> int:
        return self.attrs.get(role, 0)

    def render(self) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 1 or width < 1:
            self.win.noutrefresh()
            return
        max_len = max(width - 1, 0)
        for i, line in enumerate(_HELP_LINES):
            if i >= height:
                break
            shown = line if len(line) <= max_len else line[:max_len]
            attr = self._attr("title") if line.isupper() else self._attr("expression")
            try:
                self.win.addstr(i, 0, shown.ljust(max_len), attr)
            except curses.error:
                pass
        self.win.noutrefresh()
