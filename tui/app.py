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

DISPLAY_H = 4
KEYBOARD_H = 5


def format_result(value: float) -> str:
    """Formatear float de forma legible (14.0 -> 14, 0.3 no 0.30000000000004)."""
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")


class App:
    """Calculadora TUI."""

    def __init__(self, stdscr) -> None:
        self.stdscr = stdscr
        self.calc = Calculator()
        self.history = History()
        self.expression = ""
        self.result_display = ""
        self.error = ""
        self.just_evaluated = False

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
        self.stdscr.clearok(True)  # repintado completo inicial (evita negro en tmux/terminales lazy)
        while True:
            self._render()
            ch = self.stdscr.getch()
            if ch in (ord("q"), ord("Q")):  # q/Q: salir
                break
            if ch == 27:  # ESC: limpiar
                self._handle_action("clear", "")
                continue
            if ch in (ord("c"), ord("C")):  # c/C: limpiar historial
                self.history.clear()
                self.history_panel.reset_scroll()
                continue
            if ch == curses.KEY_RESIZE:
                curses.resizeterm(*self.stdscr.getmaxyx())
                self._make_windows()
                continue
            self._handle_key(ch)

    # ----- render -----

    def _render(self) -> None:
        if not self.error:
            try:
                self.result_display = format_result(self.calc.evaluate(self.expression))
            except (CalcSyntaxError, CalcMathError, ValueError):
                self.result_display = ""
        self.display.render(self.expression, self.result_display, self.error)
        self.history_panel.render()
        self.keyboard.render(highlight=self.expression[-1] if self.expression else None)
        self.stdscr.refresh()

    # ----- input -----

    def _handle_key(self, ch: int) -> None:
        # Navegación con flechas sobre los botones
        if ch == curses.KEY_LEFT:
            self.keyboard.move(0, -1)
            return
        if ch == curses.KEY_RIGHT:
            self.keyboard.move(0, 1)
            return
        if ch == curses.KEY_UP:
            self.history_panel.scroll(1)
            return
        if ch == curses.KEY_DOWN:
            self.history_panel.scroll(-1)
            return
        if ch in KEY_ENTER:
            self._handle_action("eval", "")
            return
        if ch == 32:  # SPACE: activar botón enfocado
            action, char = self.keyboard.focused_action()
            self._handle_action(action, char)
            return
        if ch in KEY_BACKSPACE:
            self._handle_action("back", "")
            return
        if ch < 32 or ch > 126:
            return  # tecla sin mapear

        char = chr(ch)
        if char in "0123456789.+-*/()%!":
            self._insert(char)

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
                self.history_panel.reset_scroll()
                self.result_display = formatted
                self.error = ""
                self.just_evaluated = True
            except (CalcSyntaxError, CalcMathError, ValueError) as exc:
                self.error = str(exc)
        elif action == "ans":
            if self.result_display:
                self.expression = self.result_display
                self.just_evaluated = False
                self.error = ""