"""Aplicación TUI principal: loop de curses y manejo de eventos."""

import curses

from calculator import Calculator, CalcSyntaxError, CalcMathError
from models.history import History
from tui.display import Display
from tui.help_panel import HelpPanel
from tui.history_panel import HistoryPanel
from tui.keyboard import Keyboard
from tui.theme import (
    ensure_config,
    init_colors,
    next_theme,
    resolve_theme,
    role_attrs,
    save_config,
)
from tui.vars_panel import VarsPanel

# Código de tecla: backspace puede venir como 127 o 8
KEY_BACKSPACE = (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC)
KEY_ENTER = (10, 13, curses.KEY_ENTER)
TAB = 9
SPACE = 32
# Caracteres insertables no alfanuméricos (letras = identificadores de variables)
OPERATOR_LITERALS = "+-*/()%!,="

DISPLAY_H = 4
KEYBOARD_H = 5
MIN_ROWS = DISPLAY_H + KEYBOARD_H + 2  # mínimo: display + historial + teclado
MIN_COLS = 30  # ancho mínimo del grid del teclado (6 * 5)

K_HINT = "teclado  · tab foco · ? ayuda · q salir"
H_HINT = "historial · tab foco · ? ayuda · q salir"
V_HINT = "variables · tab foco · ? ayuda · q salir"

_FOCUS_ORDER = ("keyboard", "history", "vars")


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
        self.focus = "keyboard"  # "keyboard" | "history" | "vars"
        self.show_help = False
        self.pending_confirm: str | None = None
        self._pending_confirm_action: str = "clear_history"
        self._edit_counter = 0
        self._last_tray: tuple | None = None
        self._last_tray_edit = -1

        self.config = ensure_config()
        self._use_color = init_colors()
        stdscr.keypad(True)
        curses.curs_set(0)

        self.too_small = False
        self._make_windows()

    # ----- setup -----

    def _apply_theme(self) -> None:
        rows = self.stdscr.getmaxyx()[0]
        self.theme = resolve_theme(self.config, rows, self._use_color)
        self.attrs = role_attrs(self.theme, self._use_color)

    def _cycle_theme(self) -> None:
        self.config["theme"] = next_theme(self.theme.name)
        save_config(self.config)
        self._apply_theme()

    def _make_windows(self) -> None:
        self._apply_theme()
        height, width = self.stdscr.getmaxyx()
        self.too_small = height < MIN_ROWS or width < MIN_COLS
        if self.too_small:
            self.display_win = None
            self.history_win = None
            self.keyboard_win = None
            return
        kb_top = max(DISPLAY_H, height - KEYBOARD_H)
        self.display_win = curses.newwin(DISPLAY_H, width, 0, 0)
        self.history_win = curses.newwin(kb_top - DISPLAY_H, width, DISPLAY_H, 0)
        self.keyboard_win = curses.newwin(height - kb_top, width, kb_top, 0)
        self.display = Display(self.display_win, self.attrs, self.theme.glyphs)
        self.history_panel = HistoryPanel(self.history_win, self.history, self.attrs)
        self.vars_panel = VarsPanel(
            self.history_win, self.calc.variables, format_result, self.attrs
        )
        self.help_panel = HelpPanel(self.history_win, self.attrs)
        self.keyboard = Keyboard(self.keyboard_win, self.attrs)

    # ----- loop principal -----

    def run(self) -> None:
        # Limpieza inicial explícita: sin esto el primer render puede quedar
        # en negro hasta el primer evento (clearok + refresh de subwindows).
        self.stdscr.clear()
        self.stdscr.refresh()
        while True:
            self._render()
            ch = self.stdscr.getch()
            if ch == curses.KEY_RESIZE:
                self._on_resize()
                continue
            if self._handle_key(ch):
                break

    def _on_resize(self) -> None:
        """Reconstruir el layout tras un resize.

        Ojo: NO llamar a `curses.resizeterm()` acá. ncurses ya redimensionó
        `stdscr` al recibir SIGWINCH (su `getmaxyx()` es el nuevo tamaño) y
        volver a llamarlo re-dispara KEY_RESIZE indefinidamente.
        """
        self.stdscr.clear()
        self.stdscr.refresh()
        self._make_windows()

    # ----- render -----

    def _render(self) -> None:
        if self.too_small:
            self._render_too_small()
            return
        # No previsualizar asignaciones (ejecutan sobre el almacén) ni `=`
        if not self.error and not self.pending_confirm:
            if "=" in self.expression:
                self.result_display = ""
            else:
                try:
                    self.result_display = format_result(
                        self.calc.evaluate(self.expression)
                    )
                except (CalcSyntaxError, CalcMathError, ValueError, KeyError):
                    self.result_display = ""
        notation = ""
        if self.theme.live_notation and self.expression and not self.error:
            notation = self.calc.notation(self.expression)
        message = self.pending_confirm or self.error
        hint = self._status_text()
        self.display.render(
            self.expression, self.result_display, message, hint, notation
        )
        if self.show_help:
            self.help_panel.render()
        elif self.focus == "vars":
            self.vars_panel.render()
        else:
            self.history_panel.render()
        last = self.expression[-1] if self.expression else None
        suffix = self.expression[-2:] if len(self.expression) >= 2 else ""
        highlight = suffix if suffix in ("**", "//") else last
        self.keyboard.render(highlight=highlight)
        curses.doupdate()

    def _render_too_small(self) -> None:
        """Aviso centrado cuando la terminal no alcanza el tamaño mínimo."""
        height, width = self.stdscr.getmaxyx()
        self.stdscr.erase()
        lines = [
            "terminal demasiado pequeña",
            f"mínimo {MIN_COLS}x{MIN_ROWS} · actual {width}x{height}",
            "agrandá la ventana · q para salir",
        ]
        start = max(height // 2 - len(lines) // 2, 0)
        for i, line in enumerate(lines):
            y = start + i
            if y >= height or not line:
                continue
            x = max((width - len(line)) // 2, 0)
            attr = self.attrs.get("error", 0) if i == 0 else self.attrs.get("hint", 0)
            try:
                self.stdscr.addstr(y, x, line[: max(width - 1, 0)], attr)
            except curses.error:
                pass
        self.stdscr.noutrefresh()
        curses.doupdate()

    _MODE_LABEL = {"keyboard": "teclado", "history": "historial", "vars": "variables"}
    _NEXT_FOCUS = {"keyboard": "historial", "history": "variables", "vars": "teclado"}

    def _status_text(self) -> str:
        """Barra: `<modo> · <acción bajo cursor> · tab <destino> · ? ayuda · q salir`."""
        prompt = self.theme.glyphs.get("prompt", ">")
        if self.show_help:
            return f"{prompt} ayuda · ? o esc cerrar · q salir"
        if not self.theme.status_bar:
            return {"keyboard": K_HINT, "history": H_HINT, "vars": V_HINT}[self.focus]
        if self.focus == "keyboard":
            desc = self.keyboard.focused_description()
            item = f"«{desc}»" if desc else "—"
        elif self.focus == "history":
            item = self._history_item()
        else:
            item = self._vars_item()
        mode = self._MODE_LABEL[self.focus]
        nxt = self._NEXT_FOCUS[self.focus]
        return f"{prompt} {mode} · {item} · tab {nxt} · ? ayuda · q salir"

    def _history_item(self) -> str:
        """Entrada seleccionada del historial como texto `expr = result`."""
        current = self.history_panel.selected_entry()
        if current is None:
            return "—"
        entry, _ = current
        return f"{entry.expr} = {entry.result}"

    def _vars_item(self) -> str:
        """Variable seleccionada como texto `nombre = valor`."""
        var = self.vars_panel.selected_var()
        if var is None:
            return "—"
        name, value = var
        return f"{name} = {format_result(value)}"

    # ----- entrada -----

    def _handle_key(self, ch: int) -> bool:
        """Procesar tecla. Retorna True si la app debe salir."""
        if self.too_small:  # solo se puede salir hasta agrandar la terminal
            return ch in (ord("q"), ord("Q"))
        if self.pending_confirm:
            self._process_confirm(ch)
            return False

        if self.show_help:  # modal: solo cierra o sale
            if ch in (ord("?"), 27):
                self.show_help = False
            elif ch in (ord("q"), ord("Q")):
                return True
            return False

        if ch == TAB:
            self._toggle_focus()
            return False
        if ch in (ord("q"), ord("Q")):
            return True
        if ch == ord("?"):
            self.show_help = True
            return False
        if ch == ord("T"):
            self._cycle_theme()
            return False
        if ch == 27:  # ESC: limpiar display
            self._handle_action("clear", "")
            return False

        # Enter y Space según el foco
        if ch in KEY_ENTER:
            if self.focus == "history":
                self._history_activate()
            elif self.focus == "vars":
                self._vars_activate()
            else:
                self._handle_action("eval", "")
            return False
        if ch == SPACE:
            if self.focus == "history":
                self._history_activate()
            elif self.focus == "vars":
                self._vars_activate()
            else:
                action, char = self.keyboard.focused_action()
                self._handle_action(action, char)
            return False

        # Navegación y acciones según el foco
        if self.focus == "history":
            if self._handle_history_key(ch):
                return False
        elif self.focus == "vars":
            if self._handle_vars_key(ch):
                return False
        else:
            if self._handle_keyboard_key(ch):
                return False

        # Insertable: dígitos, operadores y letras (identificadores) en ambos focos
        if 32 < ch <= 126:
            c = chr(ch)
            if c.isalnum() or c in OPERATOR_LITERALS:
                self._insert(c)
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
                self._ask_confirm("¿Borrar todo el historial? (y/N)", "clear_history")
        else:
            return False
        return True

    def _handle_vars_key(self, ch: int) -> bool:
        """Teclas del foco variables. Retorna True si se consumieron."""
        if ch in (ord("j"), curses.KEY_DOWN):
            self.vars_panel.move(1)
        elif ch in (ord("k"), curses.KEY_UP):
            self.vars_panel.move(-1)
        elif ch == ord("h"):
            self.vars_panel.to_first()
        elif ch == ord("l"):
            self.vars_panel.to_last()
        elif ch in (ord("d"), ord("D")):
            self.vars_panel.delete_selected()
        elif ch in (ord("x"), ord("X")):
            user_vars = len(self.calc.variables.list_vars()) - len(
                self.calc.variables.BUILTINS
            )
            if user_vars:
                self._ask_confirm(
                    "¿Borrar todas las variables de usuario? (y/N)", "clear_vars"
                )
        else:
            return False
        return True

    def _ask_confirm(self, message: str, action: str) -> None:
        self.pending_confirm = message
        self._pending_confirm_action = action

    def _process_confirm(self, ch: int) -> None:
        """Manejar la confirmación de borrado (historial o variables)."""
        if ch in (ord("y"), ord("Y")):
            if self._pending_confirm_action == "clear_vars":
                self.calc.variables.clear()
                self.vars_panel.reset_selection()
            else:
                self.history.clear()
                self.history_panel.reset_selection()
        self.pending_confirm = None  # cualquier otra tecla cancela

    def _toggle_focus(self) -> None:
        idx = _FOCUS_ORDER.index(self.focus)
        self.focus = _FOCUS_ORDER[(idx + 1) % len(_FOCUS_ORDER)]

    def _history_activate(self) -> None:
        """Traer el resultado de la entrada seleccionada a la bandeja (display).

        Se concatena al final de la expresión actual para permitir continuar,
        p. ej. `5*` + traer resultado B -> `5*3`. Re-activar el mismo ítem sin
        editar nada entre medio no hace nada (evita que `<enter><space>` multiplique).
        """
        current = self.history_panel.selected_entry()
        if current is None:
            return
        entry, idx = current
        if (
            self._last_tray == ("history", idx)
            and self._edit_counter == self._last_tray_edit
        ):
            return
        self._tray_activate_value(entry.result)
        self._last_tray = ("history", idx)
        self._last_tray_edit = self._edit_counter

    def _vars_activate(self) -> None:
        """Traer el valor de la variable seleccionada a la bandeja."""
        var = self.vars_panel.selected_var()
        if var is None:
            return
        if (
            self._last_tray == ("vars", var[0])
            and self._edit_counter == self._last_tray_edit
        ):
            return
        self._tray_activate_value(format_result(var[1]))
        self._last_tray = ("vars", var[0])
        self._last_tray_edit = self._edit_counter

    def _tray_activate_value(self, value: str) -> None:
        """Poner `value` en la bandeja, concatenando si ya hay expresión."""
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
            self.expression = self.result_display + char if char in "+-*/%!." else char
            self.just_evaluated = False
        else:
            self.expression += char
        self._edit_counter += 1

    def _handle_action(self, action: str, char: str) -> None:
        if action == "insert":
            self._insert(char)
        elif action == "clear":
            self.expression = ""
            self.result_display = ""
            self.error = ""
            self.just_evaluated = False
            self._edit_counter += 1
        elif action == "back":
            self.expression = self.expression[:-1]
            self.error = ""
            self._edit_counter += 1
        elif action == "eval":
            expr = self.expression.strip()
            if expr.endswith("="):  # '=' tecleado como carácter de una asignación
                expr = expr[:-1].strip()
            if expr == "":
                return
            try:
                value = self.calc.evaluate(expr)
                formatted = format_result(value)
                self.history.add(expr, formatted, self.calc.notation(expr))
                self.history_panel.reset_selection()
                self.result_display = formatted
                self.error = ""
                self.just_evaluated = True
            except (CalcSyntaxError, CalcMathError, ValueError, KeyError) as exc:
                self.error = str(exc)
            finally:
                self._edit_counter += 1
        elif action == "ans":
            if self.result_display:
                self.expression = self.result_display
                self.just_evaluated = False
                self.error = ""
                self._edit_counter += 1
