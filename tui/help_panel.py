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
    "  tab foco · enter/space evaluar o traer valor",
    "  esc/D limpiar · c borrar · d borrar ítem · ? ayuda · q salir",
]


class HelpPanel:
    """Dibuja la leyenda de ayuda en la ventana central (modal)."""

    def __init__(self, window) -> None:
        self.win = window

    def render(self) -> None:
        height, width = self.win.getmaxyx()
        self.win.erase()
        if height < 1 or width < 1:
            return
        max_len = max(width - 1, 0)
        for i, line in enumerate(_HELP_LINES):
            if i >= height:
                break
            shown = line if len(line) <= max_len else line[:max_len]
            attr = curses.A_BOLD if line.isupper() else 0
            try:
                self.win.addstr(i, 0, shown.ljust(max_len), attr)
            except curses.error:
                pass
        self.win.refresh()
