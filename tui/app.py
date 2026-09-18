"""Aplicación TUI principal: loop de curses y manejo de eventos."""

import curses
import os
import sys
import threading
from pathlib import Path

from calculator import Calculator, CalcSyntaxError, CalcMathError
from models.history import History
from tui.display import Display
from tui.help_panel import HelpPanel
from tui.history_panel import HistoryPanel
from tui.keyboard import Keyboard
from tui.persist import (
    functions_path,
    history_path,
    load_functions,
    load_history,
    load_variables,
    save_functions,
    save_history,
    save_variables,
    variables_path,
)
from tui.theme import (
    ensure_config,
    init_colors,
    next_theme,
    resolve_theme,
    role_attrs,
    save_config,
)
from tui.update import check_update, do_update, is_auto_update_enabled, repo_root
from tui.vars_panel import VarsPanel

# Código de tecla: backspace puede venir como 127 o 8
KEY_BACKSPACE = (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC)
KEY_ENTER = (10, 13, curses.KEY_ENTER)
TAB = 9
SPACE = 32
# Caracteres insertables no alfanuméricos (letras = identificadores de variables)
OPERATOR_LITERALS = "+-*/()%!.,="

# Capa homerow: espejo del numpad en la mano derecha del teclado QWERTY.
# uio → 4/5/6, jkl → 1/2/3, m → 0.  (7-9 y el resto ya se insertan directo.)
HOME_DIGITS = {"u": "4", "i": "5", "o": "6", "j": "1", "k": "2", "l": "3", "m": "0"}

STATUS_H = 1
DISPLAY_H = 4
KEYBOARD_H = 6
MIN_ROWS = STATUS_H + DISPLAY_H + KEYBOARD_H + 2  # mínimo: secciones + historial
MIN_COLS = 30  # ancho mínimo del grid del teclado (6 * 5)

# Layout del panel central:
#   D = historial | variables en paralelo (ancho suficiente)
#   E = historial arriba / variables abajo (alto suficiente)
#   F = una sola sección, la del foco (espacio reducido)
MID_WIDE_MIN_COLS = 70
MID_STACK_MIN_ROWS = 18

# Cada cuánto despierta getch para refrescar la UI (p. ej. cuando el chequeo
# de actualización en background termina). No bloquea: ncurses no redibuja lo
# que no cambió.
TICK_MS = 400

K_HINT = "teclado · tab foco · e editar · ? ayuda · q salir"
H_HINT = "historial · tab foco · e editar · ? ayuda · q salir"
V_HINT = "variables · tab foco · e editar · ? ayuda · q salir"

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
        self.variables_path: Path | None = variables_path()
        self.calc.variables.load_user_vars(load_variables(self.variables_path))
        self.functions_path: Path | None = functions_path()
        self.calc.functions.load_user_functions(load_functions(self.functions_path))
        self.history = History()
        self.history_path: Path | None = history_path()
        self.history.load_entries(load_history(self.history_path))
        self.expression = ""
        self.result_display = ""
        self.error = ""
        self.just_evaluated = False
        self.focus = "keyboard"  # "keyboard" | "history" | "vars"
        self.show_help = False
        self.editing = False  # modo edición: tipeo libre (ver `e`)
        self.cursor = 0  # posición del cursor dentro de `expression`
        self.key_hints = False  # hints de capa homerow en el teclado (h toggle)
        self.pending_confirm: str | None = None
        self._pending_confirm_action: str = "clear_history"
        self._edit_counter = 0
        self._last_tray: tuple | None = None
        self._last_tray_edit = -1

        self.update_available = False
        self.update_label = ""
        self._update_checked = False
        self._update_requested = False
        self._update_message = ""
        self._update_thread: threading.Thread | None = None

        self.config = ensure_config()
        self._use_color = init_colors()
        stdscr.keypad(True)
        curses.curs_set(0)

        self.too_small = False
        self.mid_layout = "F"
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

    @staticmethod
    def _pick_mid_layout(height: int, width: int) -> str:
        """Elegir D/E/F según el espacio disponible."""
        if width >= MID_WIDE_MIN_COLS:
            return "D"
        if height >= MID_STACK_MIN_ROWS:
            return "E"
        return "F"

    def _make_windows(self) -> None:
        self._apply_theme()
        height, width = self.stdscr.getmaxyx()
        self.too_small = height < MIN_ROWS or width < MIN_COLS
        if self.too_small:
            self.display_win = None
            self.history_win = None
            self.vars_win = None
            self.keyboard_win = None
            self.help_win = None
            self.status_win = None
            return
        self.mid_layout = self._pick_mid_layout(height, width)
        status_top = height - STATUS_H
        kb_top = status_top - KEYBOARD_H
        display_top = kb_top - DISPLAY_H
        mid_h = display_top
        bordered = self.theme.style == "boxed"
        glyphs = self.theme.glyphs

        self.display_win = curses.newwin(DISPLAY_H, width, display_top, 0)
        self.keyboard_win = curses.newwin(KEYBOARD_H, width, kb_top, 0)
        self.status_win = curses.newwin(STATUS_H, width, status_top, 0)
        self.help_win = curses.newwin(mid_h, width, 0, 0)
        if self.mid_layout == "D":
            left_w = width // 2
            self.history_win = curses.newwin(mid_h, left_w, 0, 0)
            self.vars_win = curses.newwin(mid_h, width - left_w, 0, left_w)
        elif self.mid_layout == "E":
            hist_h = mid_h // 2
            self.history_win = curses.newwin(hist_h, width, 0, 0)
            self.vars_win = curses.newwin(mid_h - hist_h, width, hist_h, 0)
        else:  # F: ambos paneles ocupan el medio, se muestra el del foco
            self.history_win = curses.newwin(mid_h, width, 0, 0)
            self.vars_win = curses.newwin(mid_h, width, 0, 0)

        self.display = Display(self.display_win, self.attrs, glyphs)
        self.history_panel = HistoryPanel(
            self.history_win, self.history, self.attrs, glyphs, bordered
        )
        self.vars_panel = VarsPanel(
            self.vars_win,
            self.calc.variables,
            format_result,
            self.attrs,
            glyphs,
            bordered,
            functions=self.calc.functions,
        )
        self.help_panel = HelpPanel(self.help_win, self.attrs)
        self.keyboard = Keyboard(self.keyboard_win, self.attrs, glyphs)

    # ----- loop principal -----

    def run(self) -> None:
        # Limpieza inicial explícita: sin esto el primer render puede quedar
        # en negro hasta el primer evento (clearok + refresh de subwindows).
        self.stdscr.clear()
        self.stdscr.refresh()
        if is_auto_update_enabled():
            self._start_update_check()
        while True:
            self._apply_timeout()
            self._render()
            ch = self.stdscr.getch()
            if ch == -1:  # tick: el update en background puede haber cambiado algo
                continue
            if ch == curses.KEY_RESIZE:
                self._on_resize()
                continue
            if self._handle_key(ch):
                break

    def _apply_timeout(self) -> None:
        """Despertar periódicamente solo mientras hay un update check en curso.

        En reposo `getch` bloquea (timeout -1) y la TUI no consume CPU; durante
        el chequeo en background se refresca para mostrar el resultado.
        """
        pending = self._update_thread is not None and self._update_thread.is_alive()
        self.stdscr.timeout(TICK_MS if pending else -1)

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
        message = self.pending_confirm or self.error or self._update_message
        hint = self._status_text()
        self.display.render(
            self.expression,
            self.result_display,
            message,
            notation,
            cursor=self.cursor if self.editing else None,
        )
        self._render_status(hint)
        if self.show_help:
            self.help_panel.render()
        elif self.mid_layout == "F":
            if self.focus == "vars":
                self.vars_panel.render(active=True)
            else:
                self.history_panel.render(active=True)
        else:
            self.history_panel.render(active=self.focus == "history")
            self.vars_panel.render(active=self.focus == "vars")
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

    def _render_status(self, text: str) -> None:
        """Barra de estado fija al borde inferior (sección 4)."""
        if self.status_win is None:
            return
        height, width = self.status_win.getmaxyx()
        self.status_win.erase()
        if height >= 1 and width > 1:
            try:
                self.status_win.addstr(
                    0, 1, text[: max(width - 2, 0)], self.attrs.get("hint", 0)
                )
            except curses.error:
                pass
        self.status_win.noutrefresh()

    _MODE_LABEL = {"keyboard": "teclado", "history": "historial", "vars": "variables"}
    _NEXT_FOCUS = {"keyboard": "historial", "history": "variables", "vars": "teclado"}

    def _status_text(self) -> str:
        """Barra: `<modo> · <acción bajo cursor> · tab <destino> · e editar · ? ayuda · q salir`."""
        prompt = self.theme.glyphs.get("prompt", ">")
        update = ""
        hints = " · h hints on" if self.key_hints else ""
        if self.update_available:
            label = f" {self.update_label}" if self.update_label else ""
            update = f" · U actualizar{label}"
        if self.editing:
            return f"{prompt} edición · tipeá texto · enter evaluar · esc salir{update}"
        if self.show_help:
            return f"{prompt} ayuda · ? o esc cerrar · q salir"
        if not self.theme.status_bar:
            base = {"keyboard": K_HINT, "history": H_HINT, "vars": V_HINT}[self.focus]
            return base + update + hints
        if self.focus == "keyboard":
            desc = self.keyboard.focused_description()
            item = f"«{desc}»" if desc else "—"
        elif self.focus == "history":
            item = self._history_item()
        else:
            item = self._vars_item()
        mode = self._MODE_LABEL[self.focus]
        nxt = self._NEXT_FOCUS[self.focus]
        return f"{prompt} {mode} · {item} · tab {nxt} · e editar · ? ayuda · q salir{update}{hints}"

    def _history_item(self) -> str:
        """Entrada seleccionada del historial como texto `expr = result`."""
        current = self.history_panel.selected_entry()
        if current is None:
            return "—"
        entry, _ = current
        return f"{entry.expr} = {entry.result}"

    def _vars_item(self) -> str:
        """Entrada seleccionada (variable o función) como texto `nombre = ...`."""
        entry = self.vars_panel.selected_entry()
        if entry is None:
            return "—"
        return entry.display

    # ----- entrada -----

    def _handle_key(self, ch: int) -> bool:
        """Procesar tecla. Retorna True si la app debe salir."""
        if self.too_small:  # solo se puede salir hasta agrandar la terminal
            return ch in (ord("q"), ord("Q"))
        if self.pending_confirm:
            self._process_confirm(ch)
            return False

        if self.editing:  # modo edición: casi todo es texto
            self._handle_edit_key(ch)
            return False

        if self.show_help:  # modal: cierra, sale o desplaza
            if ch in (ord("?"), 27):
                self.show_help = False
            elif ch in (ord("q"), ord("Q")):
                return True
            elif ch in (ord("w"), ord("s"), curses.KEY_DOWN, curses.KEY_UP):
                self.help_panel.scroll(1 if ch in (ord("s"), curses.KEY_DOWN) else -1)
            return False

        if ch == TAB:
            self._toggle_focus()
            return False
        if ch in (ord("q"), ord("Q")):
            return True
        if ch == ord("?"):
            self.help_panel.scroll_to_top()
            self.show_help = True
            return False
        if ch == ord("T"):
            self._cycle_theme()
            return False
        if ch == ord("U"):
            self._handle_update_key()
            return False
        if ch in (ord("e"), ord("E")):
            self._enter_edit()
            return False
        if ch == 27:  # ESC: limpiar display
            self._handle_action("clear", "")
            return False
        if ch in (ord("h"), ord("H")):  # toggle hints de capa homerow
            self.key_hints = not self.key_hints
            self.keyboard.toggle_hints()
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

        # Insertable directo: dígitos, operadores y capa homerow. Las letras
        # command que sobreviven se ignoran; para texto libre usá modo edición.
        if 32 < ch <= 126:
            c = chr(ch)
            if c.isdigit() or c in OPERATOR_LITERALS:
                self._insert(c)
            elif c in HOME_DIGITS:
                self._insert(HOME_DIGITS[c])
        return False

    def _enter_edit(self) -> None:
        """Entrar al modo edición: tipeo libre, enter/space evalúa y sale."""
        self.editing = True
        self.cursor = len(self.expression)
        self.show_help = False
        self.error = ""
        self._update_message = ""

    def _handle_edit_key(self, ch: int) -> None:
        """Teclas en modo edición: texto libre y movimiento de cursor.

        Espacio inserta un espacio (texto libre, p. ej. `f(a, b) = expr`);
        enter/esc salen (con o sin evaluar).
        """
        if ch in KEY_ENTER:
            self.editing = False
            self._handle_action("eval", "")
        elif ch == 27:  # esc: salir sin evaluar
            self.editing = False
        elif ch == curses.KEY_DC:  # del: borrar hacia adelante
            self._edit_delete()
        elif ch in KEY_BACKSPACE:
            self._edit_backspace()
        elif ch == curses.KEY_LEFT:
            self.cursor = max(0, self.cursor - 1)
        elif ch == curses.KEY_RIGHT:
            self.cursor = min(len(self.expression), self.cursor + 1)
        elif ch in (curses.KEY_HOME, 1):  # Home / Ctrl-A
            self.cursor = 0
        elif ch in (curses.KEY_END, 5):  # End / Ctrl-E
            self.cursor = len(self.expression)
        elif ch == SPACE:  # espacio es texto válido (`f(a, b) = expr`)
            self._insert_at_cursor(" ")
        elif 32 < ch <= 126:
            self._insert_at_cursor(chr(ch))

    def _insert_at_cursor(self, text: str) -> None:
        """Insertar texto en la posición del cursor (modo edición)."""
        self.error = ""
        self._update_message = ""
        if self.just_evaluated:  # empezar de cero tras evaluar
            self.expression = ""
            self.cursor = 0
            self.just_evaluated = False
            self.result_display = ""
        pos = min(max(self.cursor, 0), len(self.expression))
        self.expression = self.expression[:pos] + text + self.expression[pos:]
        self.cursor = pos + len(text)
        self._edit_counter += 1

    def _edit_backspace(self) -> None:
        self.error = ""
        if self.just_evaluated:
            self.expression = ""
            self.cursor = 0
            self.just_evaluated = False
            self.result_display = ""
            self._edit_counter += 1
            return
        if self.cursor > 0:
            self.expression = (
                self.expression[: self.cursor - 1] + self.expression[self.cursor :]
            )
            self.cursor -= 1
            self._edit_counter += 1

    def _edit_delete(self) -> None:
        self.error = ""
        if 0 <= self.cursor < len(self.expression):
            self.expression = (
                self.expression[: self.cursor] + self.expression[self.cursor + 1 :]
            )
            self._edit_counter += 1

    def _handle_keyboard_key(self, ch: int) -> bool:
        """Teclas del foco teclado. Retorna True si se consumieron."""
        if ch in (ord("w"), curses.KEY_UP):
            self.keyboard.move(-1, 0)
        elif ch in (ord("s"), curses.KEY_DOWN):
            self.keyboard.move(1, 0)
        elif ch in (ord("a"), curses.KEY_LEFT):
            self.keyboard.move(0, -1)
        elif ch in (ord("d"), curses.KEY_RIGHT):
            self.keyboard.move(0, 1)
        elif ch in (ord("c"), ord("C")):
            self._handle_action("back", "")
        elif ch in (ord("x"),):
            self._handle_action("clear", "")
        elif ch in KEY_BACKSPACE:
            self._handle_action("back", "")
        else:
            return False
        return True

    def _handle_history_key(self, ch: int) -> bool:
        """Teclas del foco historial. Retorna True si se consumieron."""
        if ch in (ord("s"), curses.KEY_DOWN):
            self.history_panel.move(1)
        elif ch in (ord("w"), curses.KEY_UP):
            self.history_panel.move(-1)
        elif ch == ord("g"):
            self.history_panel.to_first()
        elif ch == ord("G"):
            self.history_panel.to_last()
        elif ch in (ord("x"),):
            if self.history_panel.delete_selected():
                self._persist_history()
        elif ch in (ord("X"),):
            if len(self.history):
                self._ask_confirm("¿Borrar todo el historial? (y/N)", "clear_history")
        else:
            return False
        return True

    def _handle_vars_key(self, ch: int) -> bool:
        """Teclas del foco variables. Retorna True si se consumieron."""
        if ch in (ord("s"), curses.KEY_DOWN):
            self.vars_panel.move(1)
        elif ch in (ord("w"), curses.KEY_UP):
            self.vars_panel.move(-1)
        elif ch == ord("g"):
            self.vars_panel.to_first()
        elif ch == ord("G"):
            self.vars_panel.to_last()
        elif ch in (ord("x"),):
            if self.vars_panel.delete_selected():
                self._persist_variables()
                self._persist_functions()
        elif ch in (ord("X"),):
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

    def _persist_variables(self) -> None:
        """Guardar las variables de usuario (best-effort)."""
        if self.variables_path is None:
            return
        save_variables(self.calc.variables.user_vars(), self.variables_path)

    def _persist_functions(self) -> None:
        """Guardar las funciones de usuario (best-effort)."""
        if self.functions_path is None:
            return
        save_functions(self.calc.functions.user_functions(), self.functions_path)

    def _persist_history(self) -> None:
        """Guardar el historial (best-effort)."""
        if self.history_path is None:
            return
        save_history(self.history.entries(), self.history_path)

    # ----- actualización -----

    def _start_update_check(self) -> None:
        """Lanzar el chequeo de actualización en background.

        Reutiliza el hilo en curso; si ya terminó, arranca uno nuevo para poder
        re-verificar a pedido (`U`) sin bloquear la TUI.
        """
        if self._update_thread is not None and not self._update_checked:
            return
        self._update_checked = False
        self._update_thread = threading.Thread(
            target=self._check_updates_bg, name="calc-update-check", daemon=True
        )
        self._update_thread.start()

    def _check_updates_bg(self) -> None:
        """Correr en background: solo toca flags simples que el loop relee."""
        info = check_update(repo_root())
        if info.ok and info.behind > 0:
            self.update_available = True
            self.update_label = info.available
        if self._update_requested:
            if not info.ok:
                self._update_message = (
                    "no se pudo verificar (sin conexión o sin remoto)"
                )
            elif info.behind == 0:
                self._update_message = f"estás al día ({info.current})"
            else:
                self._update_message = ""
            self._update_requested = False
        self._update_checked = True

    def _handle_update_key(self) -> None:
        """Tecla `U`: aplicar si hay update, o verificar en background."""
        if self.update_available:
            self._ask_confirm("¿Actualizar y reiniciar? (y/N)", "do_update")
            return
        self._update_requested = True
        self._update_message = "verificando actualizaciones…"
        self._start_update_check()

    def _apply_update_and_restart(self) -> None:
        """Bajar la actualización (git) y reiniciar el proceso."""
        self._update_message = "actualizando…"
        self._render()
        result = do_update(repo_root())
        if not result.ok:
            self.error = result.message
            self._update_message = ""
            return
        self.error = ""
        self._update_message = result.message
        self._restart()

    def _restart(self) -> None:
        """Reemplazar el proceso actual por uno nuevo (ya con el código nuevo)."""
        entry = os.path.join(repo_root(), "main.py")
        if not os.path.isfile(entry):
            entry = os.path.abspath(sys.argv[0])
        exe = sys.executable or "python3"
        try:
            curses.endwin()
        except Exception:  # noqa: BLE001 — pase lo que pase, hay que reiniciar
            pass
        os.execv(exe, [exe, entry])

    def _ask_confirm(self, message: str, action: str) -> None:
        self.pending_confirm = message
        self._pending_confirm_action = action

    def _process_confirm(self, ch: int) -> None:
        """Manejar la confirmación de borrado o de actualización."""
        action = self._pending_confirm_action
        self.pending_confirm = None  # cualquier otra tecla cancela
        if ch not in (ord("y"), ord("Y")):
            return
        if action == "do_update":
            self._apply_update_and_restart()
        elif action == "clear_vars":
            self.calc.variables.clear()
            self.vars_panel.reset_selection()
            self._persist_variables()
        else:
            self.history.clear()
            self.history_panel.reset_selection()
            self._persist_history()

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
        """Traer la entrada seleccionada a la bandeja.

        Variable → su valor; función → `f(` para completar los argumentos.
        """
        entry = self.vars_panel.selected_entry()
        if entry is None:
            return
        if (
            self._last_tray == ("vars", entry.name)
            and self._edit_counter == self._last_tray_edit
        ):
            return
        self._tray_activate_value(entry.action)
        self._last_tray = ("vars", entry.name)
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
        self._update_message = ""  # al escribir, el aviso de update deja de estorbar
        if self.just_evaluated:
            self.expression = self.result_display + char if char in "+-*/%!." else char
            self.just_evaluated = False
        else:
            self.expression += char
        self.cursor = len(self.expression)
        self._edit_counter += 1

    def _handle_action(self, action: str, char: str) -> None:
        if action == "insert":
            self._insert(char)
        elif action == "clear":
            self.expression = ""
            self.result_display = ""
            self.error = ""
            self.just_evaluated = False
            self.cursor = 0
            self._edit_counter += 1
        elif action == "back":
            self.expression = self.expression[:-1]
            self.error = ""
            self.cursor = len(self.expression)
            self._edit_counter += 1
        elif action == "eval":
            expr = self.expression.strip()
            if expr.endswith("="):  # '=' tecleado como carácter de una asignación
                expr = expr[:-1].strip()
            if expr == "":
                return
            try:
                defined = self.calc.define(
                    expr
                )  # `f(a, b) = expr`: registra la función
                if defined is not None:
                    self.result_display = f"fn {defined}"
                    self.error = ""
                    self.just_evaluated = True
                    self.vars_panel.reset_selection()
                    self.history_panel.reset_selection()
                    self._persist_functions()
                    self._edit_counter += 1
                    return
                value = self.calc.evaluate(expr)
                formatted = format_result(value)
                is_assignment = "=" in expr
                if (
                    not is_assignment
                ):  # las asignaciones van a variables, no al historial
                    self.history.add(expr, formatted, self.calc.notation(expr))
                    self.history_panel.reset_selection()
                    self._persist_history()
                self.result_display = formatted
                self.error = ""
                self.just_evaluated = True
                if is_assignment:
                    self._persist_variables()
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
