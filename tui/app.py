"""Aplicación TUI principal: loop de curses y manejo de eventos."""

import curses

from calculator import Calculator, CalcSyntaxError, CalcMathError
from models.history import History
from tui.display import Display
from tui.history_panel import HistoryPanel
from tui.keyboard import Keyboard, PAIR_NUM, PAIR_OP, PAIR_ACTION

# Código de tecla: backspace puede venir como 127 o 8
KEY_BACKSPACE = (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC)
KEY_ENTER = (10, 13, curses.KEY_ENTER)
TAB = 9
SPACE = 32
INSERTABLE = "0123456789.+-*/()%!"

DISPLAY_H = 4
KEYBOARD_H = 5

K_HINT = "teclado  · tab foco · q salir"
H_HINT = "historial · tab foco · q salir"


def format_result(value: float) -> str:
    """Formatear float de forma legible (14.0 -> 14, 0.3 no 0.30000000000004)."""
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")


class App:
    """Calculadora TUI con focus conmutado entre historial y teclado."""

    def __init__(self, stdscr) -> None:
        self.stdscr = stdscr
        self.calc = Calculator()
        self.history = History()
        self.expression = ""
        self.result_display = ""
        self.error = ""
        self.just_evaluated = False
        self.focus = "keyboard"  # "keyboard" | "history"
        self.pending_confirm: str | None = None

        self._init_colors()
        stdscr.keypad(True)
        curses.curs_set(0)

        self._make_windows()

    # ----- setup -----

    def _init_colors(self) -> None:
        if not curses.has_colors():
            return
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(PAIR_NUM, curses.COLOR_WHITE, -1)
        curses.init_pair(PAIR_OP, curses.COLOR_CYAN, -1)
        curses.init_pair(PAIR_ACTION, curses.COLOR_YELLOW, -1)

    def _make_windows(self) -> None:
        height, width = self.stdscr.getmaxyx()
        kb_top = max(DISPLAY_H, height - KEYBOARD_H)
        self.display_win = curses.newwin(DISPLAY_H, width, 0, 0)
        self.history_win = curses.newwin(kb_top - DISPLAY_H, width, DISPLAY_H, 0)
        self.keyboard_win = curses.newwin(height - kb_top, width, kb_top, 0)
        self.display = Display(self.display_win)
        self.history_panel = HistoryPanel(self.history_win, self.history)
        self.keyboard = Keyboard(self.keyboard_win)

    # ----- loop principal -----

    def run(self) -> None:
        self.stdscr.clearok(
            True
        )  # repintado completo inicial (evita negro en tmux/terminales lazy)
        while True:
            self._render()
            ch = self.stdscr.getch()
            if ch == curses.KEY_RESIZE:
                curses.resizeterm(*self.stdscr.getmaxyx())
                self._make_windows()
                continue
            if self._handle_key(ch):
                break

    # ----- render -----

    def _render(self) -> None:
        if not self.error and not self.pending_confirm:
            try:
                self.result_display = format_result(self.calc.evaluate(self.expression))
            except (CalcSyntaxError, CalcMathError, ValueError, KeyError):
                self.result_display = ""
        message = self.pending_confirm or self.error
        hint = H_HINT if self.focus == "history" else K_HINT
        self.display.render(self.expression, self.result_display, message, hint)
        self.history_panel.render()
        self.keyboard.render(highlight=self.expression[-1] if self.expression else None)
        self.stdscr.refresh()

    # ----- entrada -----

    def _handle_key(self, ch: int) -> bool:
        """Procesar tecla. Retorna True si la app debe salir."""
        if self.pending_confirm:
            self._process_confirm(ch)
            return False

        if ch == TAB:
            self._toggle_focus()
            return False
        if ch in (ord("q"), ord("Q")):
            return True
        if ch == 27:  # ESC: limpiar display
            self._handle_action("clear", "")
            return False

        # Enter y Space según el foco
        if ch in KEY_ENTER:
            if self.focus == "history":
                self._history_activate()
            else:
                self._handle_action("eval", "")
            return False
        if ch == SPACE:
            if self.focus == "history":
                self._history_activate()
            else:
                action, char = self.keyboard.focused_action()
                self._handle_action(action, char)
            return False

        # Navegación y acciones según el foco
        if self.focus == "history":
            if self._handle_history_key(ch):
                return False
        else:
            if self._handle_keyboard_key(ch):
                return False

        # Insertable: dígitos y operadores en ambos focos
        if 32 < ch <= 126 and chr(ch) in INSERTABLE:
            self._insert(chr(ch))
        return False

    def _handle_keyboard_key(self, ch: int) -> bool:
        """Teclas del foco teclado. Retorna True si se consumieron."""
        if ch in (ord("h"), curses.KEY_LEFT):
            self.keyboard.move(0, -1)
        elif ch in (ord("l"), curses.KEY_RIGHT):
            self.keyboard.move(0, 1)
        elif ch in (ord("j"), curses.KEY_DOWN):
            self.keyboard.move(1, 0)
        elif ch in (ord("k"), curses.KEY_UP):
            self.keyboard.move(-1, 0)
        elif ch in (ord("c"), ord("C")):
            self._handle_action("back", "")
        elif ch in (ord("d"), ord("D")):
            self._handle_action("clear", "")
        elif ch in KEY_BACKSPACE:
            self._handle_action("back", "")
        else:
            return False
        return True

    def _handle_history_key(self, ch: int) -> bool:
        """Teclas del foco historial. Retorna True si se consumieron."""
        if ch in (ord("j"), curses.KEY_DOWN):
            self.history_panel.move(1)
        elif ch in (ord("k"), curses.KEY_UP):
            self.history_panel.move(-1)
        elif ch == ord("h"):
            self.history_panel.to_first()
        elif ch == ord("l"):
            self.history_panel.to_last()
        elif ch in (ord("d"), ord("D")):
            self.history_panel.delete_selected()
        elif ch in (ord("x"), ord("X")):
            if len(self.history):
                self.pending_confirm = "¿Borrar todo el historial? (y/N)"
        else:
            return False
        return True

    def _process_confirm(self, ch: int) -> None:
        """Manejar la confirmación de borrar historial."""
        if ch in (ord("y"), ord("Y")):
            self.history.clear()
            self.history_panel.reset_selection()
        self.pending_confirm = None  # cualquier otra tecla cancela

    def _toggle_focus(self) -> None:
        self.focus = "history" if self.focus == "keyboard" else "keyboard"

    def _history_activate(self) -> None:
        """Poner el resultado de la entrada seleccionada en la bandeja (display).

        Se concatena al final de la expresión actual para permitir continuar,
        p. ej. `5*` + traer resultado B -> `5*3`.
        """
        entry = self.history_panel.selected_entry()
        if entry is None:
            return
        value = entry[1]
        if self.just_evaluated or not self.expression:
            self.expression = value  # nueva bandeja: empieza limpio
        else:
            last = self.expression[-1]
            if last.isdigit() or last == ")":
                self.expression += "*" + value  # evitar pegar números (5 + 3 -> 5*3)
            else:
                self.expression += value
        self.just_evaluated = False
        self.error = ""

    # ----- acciones -----

    def _insert(self, char: str) -> None:
        self.error = ""
        if self.just_evaluated:
            self.expression = self.result_display + char if char in "+-*/%!" else char
            self.just_evaluated = False
            return
        self.expression += char

    def _handle_action(self, action: str, char: str) -> None:
        if action == "insert":
            self._insert(char)
        elif action == "clear":
            self.expression = ""
            self.result_display = ""
            self.error = ""
            self.just_evaluated = False
        elif action == "back":
            self.expression = self.expression[:-1]
            self.error = ""
        elif action == "eval":
            if self.expression.strip() == "":
                return
            try:
                value = self.calc.evaluate(self.expression)
                formatted = format_result(value)
                self.history.add(self.expression, formatted)
                self.history_panel.reset_selection()
                self.result_display = formatted
                self.error = ""
                self.just_evaluated = True
            except (CalcSyntaxError, CalcMathError, ValueError, KeyError) as exc:
                self.error = str(exc)
        elif action == "ans":
            if self.result_display:
                self.expression = self.result_display
                self.just_evaluated = False
                self.error = ""
