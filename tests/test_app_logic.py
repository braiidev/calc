"""Tests de la lógica de la TUI (sin curses): bandeja, foco y variables."""

import curses
import json

from calculator import Calculator
from models.history import History
from tui.app import HOME_DIGITS, TICK_MS, App
from tui.keyboard import Keyboard
from tui.theme import resolve_theme


class StubHistoryPanel:
    def __init__(self, history: History) -> None:
        self.history = history
        self.selected = len(history) - 1

    def selected_entry(self):
        if len(self.history) == 0:
            return None
        idx = self.selected if self.selected >= 0 else len(self.history) - 1
        entry = self.history[idx]
        if entry is None:
            return None
        return entry, idx

    def reset_selection(self) -> None:
        self.selected = -1

    def move(self, delta: int) -> None:
        if len(self.history) == 0:
            return
        current = self.selected if self.selected >= 0 else len(self.history) - 1
        self.selected = max(0, min(len(self.history) - 1, current + delta))

    def to_first(self) -> None:
        if len(self.history):
            self.selected = 0

    def to_last(self) -> None:
        if len(self.history):
            self.selected = len(self.history) - 1

    def delete_selected(self) -> bool:
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


class StubVarsPanel:
    def __init__(self, variables) -> None:
        self.variables = variables
        self.selected = -1

    def selected_var(self):
        items = list(self.variables.list_vars().items())
        if not items:
            return None
        idx = self.selected if self.selected >= 0 else len(items) - 1
        return items[idx]

    def reset_selection(self) -> None:
        self.selected = -1

    def delete_selected(self) -> bool:
        current = self.selected_var()
        if current is None:
            return False
        return self.variables.delete(current[0])


class StubHelpPanel:
    def __init__(self) -> None:
        self.offset = 0

    def scroll_to_top(self) -> None:
        self.offset = 0

    def scroll(self, delta: int) -> None:
        self.offset += delta


class StubScr:
    def __init__(self) -> None:
        self.timeout_value: int | None = None

    def timeout(self, value: int) -> None:
        self.timeout_value = value


class StubThread:
    def __init__(self, alive: bool) -> None:
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


def make_app() -> App:
    app = object.__new__(App)
    app.calc = Calculator()
    app.history = History()
    app.history_panel = StubHistoryPanel(app.history)  # type: ignore[assignment]
    app.vars_panel = StubVarsPanel(app.calc.variables)  # type: ignore[assignment]
    app.help_panel = StubHelpPanel()  # type: ignore[assignment]
    app.expression = ""
    app.result_display = ""
    app.error = ""
    app.just_evaluated = False
    app.focus = "keyboard"
    app.show_help = False
    app.editing = False
    app.cursor = 0
    app.key_hints = False
    app.pending_confirm = None
    app._pending_confirm_action = "clear_history"
    app._edit_counter = 0
    app._last_tray = None
    app._last_tray_edit = -1
    app.too_small = False
    app.variables_path = None  # sin persistencia por defecto en tests
    app.history_path = None
    app.theme = resolve_theme({}, 24, False)
    app.update_available = False
    app.update_label = ""
    app._update_checked = False
    app._update_requested = False
    app._update_message = ""
    app._update_thread = None
    return app


def test_history_enter_space_no_duplica() -> None:
    app = make_app()
    app.history.add("3+4", "7")
    app.history_panel.selected = 0
    app._history_activate()  # enter
    assert app.expression == "7"
    app._history_activate()  # space sobre el mismo ítem: no-op
    assert app.expression == "7"


def test_history_concatena_al_teclear_operador() -> None:
    app = make_app()
    app.history.add("3+4", "7")
    app.history.add("10*2", "20")
    app.history_panel.selected = 0
    app._history_activate()  # traigo A -> 7
    app._insert("*")  # 7*
    app.history_panel.selected = 1
    app._history_activate()  # traigo B -> 7*20
    assert app.expression == "7*20"


def test_vars_activate_no_duplica() -> None:
    app = make_app()
    app.calc.evaluate("x = 5")
    names = list(app.calc.variables.list_vars())
    app.vars_panel.selected = names.index("x")
    app._vars_activate()
    assert app.expression == "5"
    app._vars_activate()
    assert app.expression == "5"


def test_status_text_keyboard() -> None:
    app = make_app()
    app.theme = resolve_theme({"theme": "frio"}, 24, False)

    class KB:
        def focused_description(self):
            return "sumar"

    app.keyboard = KB()  # type: ignore[assignment]
    text = app._status_text()
    assert "teclado" in text
    assert "«sumar»" in text
    assert "tab historial" in text
    assert "? ayuda" in text
    assert "q salir" in text


def test_status_text_historial_muestra_entrada() -> None:
    app = make_app()
    app.theme = resolve_theme({"theme": "frio"}, 24, False)
    app.history.add("9 // 4", "2", "[floor]")
    app.focus = "history"
    text = app._status_text()
    assert "historial" in text
    assert "9 // 4 = 2" in text
    assert "tab variables" in text


def test_status_text_vars_muestra_variable() -> None:
    app = make_app()
    app.theme = resolve_theme({"theme": "frio"}, 24, False)
    app.calc.evaluate("x = 5")
    app.focus = "vars"
    text = app._status_text()
    assert "variables" in text
    assert "x = 5" in text
    assert "tab teclado" in text


def test_status_text_vacio_y_ayuda() -> None:
    app = make_app()
    app.theme = resolve_theme({"theme": "frio"}, 24, False)
    app.focus = "history"
    assert "—" in app._status_text()
    app.show_help = True
    assert "ayuda" in app._status_text()


def test_too_small_solo_permite_salir() -> None:
    app = make_app()
    app.too_small = True
    assert app._handle_key(ord("5")) is False
    assert app.expression == ""
    assert app._handle_key(ord("q")) is True


class StubStd:
    def __init__(self, height: int, width: int) -> None:
        self._size = (height, width)

    def getmaxyx(self) -> tuple[int, int]:
        return self._size


def test_render_status_escribe_en_la_barra_del_fondo() -> None:
    import tui.app as app_module

    class BarWin:
        def __init__(self, height: int, width: int, top: int, left: int) -> None:
            self._size = (height, width, top, left)
            self.writes: list[tuple[int, int, str, int]] = []

        def getmaxyx(self) -> tuple[int, int]:
            return self._size[0], self._size[1]

        def erase(self) -> None:
            self.writes = []

        def addstr(self, y: int, x: int, text: str, attr: int) -> None:
            self.writes.append((y, x, text, attr))

        def noutrefresh(self) -> None:
            pass

    bar = BarWin(1, 80, 23, 0)
    app = object.__new__(App)
    app.status_win = bar  # type: ignore[attr-defined]
    app.attrs = {"hint": 2}
    app._render_status("teclado · tab historial · e editar · ? ayuda · q salir")
    assert bar.writes == [
        (0, 1, "teclado · tab historial · e editar · ? ayuda · q salir", 2)
    ]


def test_render_status_vacio_o_sin_barra_no_escribe() -> None:
    app = object.__new__(App)
    app.status_win = None  # type: ignore[attr-defined]
    app._render_status("")
    assert True


def test_on_resize_no_llama_resizeterm(monkeypatch) -> None:
    import tui.app as app_module

    called = {"resizeterm": False}

    def boom(*args):
        called["resizeterm"] = True
        raise AssertionError("no debe llamarse resizeterm en KEY_RESIZE")

    monkeypatch.setattr(app_module.curses, "resizeterm", boom)

    class Std:
        def getmaxyx(self):
            return (5, 20)

        def clear(self):
            pass

        def refresh(self):
            pass

    app = make_app()
    app.stdscr = Std()  # type: ignore[assignment]
    rebuilt = []
    app._make_windows = lambda: rebuilt.append(True)  # type: ignore[assignment]
    app._on_resize()
    assert rebuilt == [True]
    assert called["resizeterm"] is False


def test_make_windows_too_small_no_crea_ventanas() -> None:
    app = object.__new__(App)
    app.stdscr = StubStd(5, 20)  # type: ignore[assignment]
    app.config = {}
    app._use_color = False
    app._make_windows()
    assert app.too_small is True
    assert app.display_win is None
    assert app.status_win is None


def test_make_windows_size_ok(monkeypatch) -> None:
    import tui.app as app_module

    class FakeWin:
        def __init__(self, height: int, width: int, *args) -> None:
            self._size = (height, width)

        def getmaxyx(self) -> tuple[int, int]:
            return self._size

    monkeypatch.setattr(app_module.curses, "newwin", FakeWin)
    app = object.__new__(App)
    app.stdscr = StubStd(24, 80)  # type: ignore[assignment]
    app.calc = Calculator()
    app.history = History()
    app.config = {}
    app._use_color = False
    app._make_windows()
    assert app.too_small is False
    assert app.display_win is not None
    assert app.status_win is not None
    assert app.mid_layout == "D"  # 80 >= 70: historial | variables
    assert app.vars_win is not None


def test_make_windows_secciones_no_se_pisan(monkeypatch) -> None:
    import tui.app as app_module

    class FakeWin:
        def __init__(self, height: int, width: int, top: int, left: int) -> None:
            self._size = (height, width, top, left)

        def getmaxyx(self) -> tuple[int, int]:
            return self._size[0], self._size[1]

    monkeypatch.setattr(app_module.curses, "newwin", FakeWin)
    app = object.__new__(App)
    app.stdscr = StubStd(24, 80)  # type: ignore[assignment]
    app.calc = Calculator()
    app.history = History()
    app.config = {}
    app._use_color = False
    app._make_windows()
    status_h, status_w, status_top, status_left = app.status_win._size  # type: ignore[attr-defined]
    kb_h, kb_w, kb_top, kb_left = app.keyboard_win._size  # type: ignore[attr-defined]
    disp_h, disp_w, disp_top, disp_left = app.display_win._size  # type: ignore[attr-defined]
    hist_h, hist_w, hist_top, hist_left = app.history_win._size  # type: ignore[attr-defined]
    assert (status_h, status_w, status_top, status_left) == (1, 80, 23, 0)
    assert kb_top == status_top - kb_h  # teclado pegado sobre la statusbar
    assert disp_top == kb_top - disp_h  # display pegado sobre el teclado
    assert (disp_top, disp_h) == (hist_h, app_module.DISPLAY_H)  # historial arriba
    assert hist_top == 0


def test_pick_mid_layout() -> None:
    assert App._pick_mid_layout(24, 80) == "D"
    assert App._pick_mid_layout(18, 40) == "E"
    assert App._pick_mid_layout(24, 69) == "E"
    assert App._pick_mid_layout(17, 40) == "F"
    assert App._pick_mid_layout(11, 30) == "F"


def test_make_windows_layout_apilado(monkeypatch) -> None:
    import tui.app as app_module

    class FakeWin:
        def __init__(self, height: int, width: int, *args) -> None:
            self._size = (height, width)

        def getmaxyx(self) -> tuple[int, int]:
            return self._size

    monkeypatch.setattr(app_module.curses, "newwin", FakeWin)
    app = object.__new__(App)
    app.stdscr = StubStd(20, 40)  # type: ignore[assignment]
    app.calc = Calculator()
    app.history = History()
    app.config = {}
    app._use_color = False
    app._make_windows()
    assert app.mid_layout == "E"
    assert app.history_win is not None
    assert app.vars_win is not None


def test_help_abre_y_cierra() -> None:
    app = make_app()
    assert app._handle_key(ord("?")) is False
    assert app.show_help is True
    assert app._handle_key(ord("?")) is False
    assert app.show_help is False


def test_help_es_modal() -> None:
    app = make_app()
    app._handle_key(ord("?"))
    app._handle_key(ord("5"))  # no debe editar ni cerrar
    assert app.expression == ""
    assert app.show_help is True
    app._handle_key(27)  # ESC cierra
    assert app.show_help is False


def test_help_q_sale() -> None:
    app = make_app()
    app.show_help = True
    assert app._handle_key(ord("q")) is True


def test_help_ws_desplaza() -> None:
    app = make_app()
    app._handle_key(ord("?"))
    app._handle_key(ord("s"))
    assert app.help_panel.offset == 1
    app._handle_key(ord("w"))
    assert app.help_panel.offset == 0
    app.help_panel.offset = 5
    app._handle_key(ord("?"))  # reabrir vuelve arriba
    app._handle_key(ord("?"))  # y cerrar
    assert app.help_panel.offset == 0


def test_status_menciona_e_editar() -> None:
    app = make_app()
    app.focus = "history"
    assert "e editar" in app._status_text()


def test_timeout_bloquea_en_reposo() -> None:
    app = make_app()
    app.stdscr = StubScr()  # type: ignore[assignment]
    app._update_thread = None
    app._apply_timeout()
    assert app.stdscr.timeout_value == -1


def test_timeout_tickea_mientras_chequea() -> None:
    app = make_app()
    app.stdscr = StubScr()  # type: ignore[assignment]
    app._update_thread = StubThread(True)  # type: ignore[assignment]
    app._apply_timeout()
    assert app.stdscr.timeout_value == TICK_MS


def test_toggle_focus_ciclo() -> None:
    app = make_app()
    app._toggle_focus()
    assert app.focus == "history"
    app._toggle_focus()
    assert app.focus == "vars"
    app._toggle_focus()
    assert app.focus == "keyboard"


def test_eval_persiste_historial(tmp_path) -> None:
    app = make_app()
    app.history_path = tmp_path / "history.json"
    for char in "2+3":
        app._insert(char)
    app._handle_action("eval", "")
    data = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert data[0]["expr"] == "2+3"
    assert data[0]["result"] == "5"


def test_asignacion_no_persiste_historial(tmp_path) -> None:
    app = make_app()
    app.history_path = tmp_path / "history.json"
    for char in "x=5":
        app._insert(char)
    app._handle_action("eval", "")
    assert not (tmp_path / "history.json").exists()


def test_asignacion_desde_tui() -> None:
    app = make_app()
    for char in "x = 5":
        app._insert(char)
    assert app.expression == "x = 5"
    app._handle_action("eval", "")
    assert app.calc.variables.get("x") == 5.0
    assert app.result_display == "5"


def test_eval_tolera_igual_tecleado() -> None:
    app = make_app()
    for char in "2+3=":
        app._insert(char)
    app._handle_action("eval", "")
    assert app.result_display == "5"
    entry = app.history[0]
    assert entry is not None
    assert entry.expr == "2+3"
    assert entry.result == "5"


def test_asignacion_no_va_al_historial() -> None:
    app = make_app()
    for char in "x = 5":
        app._insert(char)
    app._handle_action("eval", "")
    assert len(app.history) == 0
    assert app.result_display == "5"


def test_calculo_si_va_al_historial() -> None:
    app = make_app()
    for char in "2+3":
        app._insert(char)
    app._handle_action("eval", "")
    assert len(app.history) == 1


def test_asignacion_persiste_variables(tmp_path) -> None:
    app = make_app()
    app.variables_path = tmp_path / "variables.json"
    for char in "x = 5":
        app._insert(char)
    app._handle_action("eval", "")
    assert app.variables_path is not None
    saved = json.loads(app.variables_path.read_text(encoding="utf-8"))
    assert saved == {"x": 5.0}


def test_persist_sin_path_no_escribe() -> None:
    app = make_app()
    app.calc.variables.set("x", 1)
    app._persist_variables()  # variables_path None: no-op


def test_historial_guarda_notacion() -> None:
    app = make_app()
    for char in "root(8,3)":
        app._insert(char)
    app._handle_action("eval", "")
    entry = app.history[0]
    assert entry is not None
    assert entry.notation == "[cbrt]"


def test_status_muestra_actualizacion_disponible() -> None:
    app = make_app()
    app.focus = "history"
    app.update_available = True
    app.update_label = "v0.9"
    assert "U actualizar v0.9" in app._status_text()


def test_status_sin_update_no_menciona_U() -> None:
    app = make_app()
    app.focus = "history"
    assert "U actualizar" not in app._status_text()


def test_U_con_update_pide_confirmacion() -> None:
    app = make_app()
    app.update_available = True
    app._handle_key(ord("U"))
    assert app.pending_confirm is not None
    assert app._pending_confirm_action == "do_update"


def test_U_sin_update_dispara_verificacion(monkeypatch) -> None:
    app = make_app()
    started: list[bool] = []
    app._start_update_check = lambda: started.append(True)  # type: ignore[method-assign]
    app._handle_key(ord("U"))
    assert started
    assert app._update_requested is True
    assert "verificando" in app._update_message


def test_confirmar_update_aplica_y_reinicia(monkeypatch) -> None:
    app = make_app()
    called: list[bool] = []
    app._apply_update_and_restart = lambda: called.append(True)  # type: ignore[method-assign]
    app._ask_confirm("¿Actualizar y reiniciar? (y/N)", "do_update")
    app._process_confirm(ord("y"))
    assert called
    assert app.pending_confirm is None


def test_cancelar_update_no_aplica() -> None:
    app = make_app()
    called: list[bool] = []
    app._apply_update_and_restart = lambda: called.append(True)  # type: ignore[method-assign]
    app._ask_confirm("¿Actualizar y reiniciar? (y/N)", "do_update")
    app._process_confirm(ord("n"))
    assert not called
    assert app.pending_confirm is None


def test_insert_limpia_mensaje_de_update() -> None:
    app = make_app()
    app._update_message = "estás al día (v0.8)"
    app._insert("5")
    assert app._update_message == ""


def _feed(app, text: str) -> None:
    for char in text:
        app._handle_key(ord(char))


def test_e_entra_en_modo_edicion() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    assert app.editing is True
    assert "edición" in app._status_text()


def test_edicion_permite_letras_que_eran_comandos() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "hola=5")
    assert app.expression == "hola=5"


def test_edicion_enter_evalua_guarda_y_sale() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "x=9")
    app._handle_key(10)
    assert app.editing is False
    assert app.calc.variables.get("x") == 9


def test_edicion_space_evalua_y_sale() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "2+3")
    app._handle_key(32)
    assert app.editing is False
    assert app.result_display == "5"


def test_edicion_esc_sale_sin_evaluar() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "2+")
    app._handle_key(27)
    assert app.editing is False
    assert app.expression == "2+"
    assert app.result_display == ""


def test_edicion_q_es_texto_no_salida() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    assert app._handle_key(ord("q")) is False
    assert app.expression == "q"


def test_edicion_backspace_borra() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "ab")
    app._handle_key(127)
    assert app.expression == "a"


def test_normal_no_inserta_letras_sueltas() -> None:
    app = make_app()
    app.focus = "history"  # evita depender del widget de teclado
    app._handle_key(ord("a"))
    assert app.expression == ""


def test_normal_si_inserta_digitos_y_operadores() -> None:
    app = make_app()
    app.focus = "history"
    app._handle_key(ord("7"))
    app._handle_key(ord("+"))
    app._handle_key(ord("."))
    assert app.expression == "7+."


def test_edicion_cursor_arranca_al_final() -> None:
    app = make_app()
    app.expression = "12+3"
    app._handle_key(ord("e"))
    assert app.cursor == 4


def test_edicion_inserta_en_medio() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "ab")
    app._handle_key(curses.KEY_LEFT)
    app._handle_key(ord("X"))
    assert app.expression == "aXb"
    assert app.cursor == 2


def test_edicion_mueve_cursor_home_end() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "abc")
    app._handle_key(curses.KEY_HOME)
    assert app.cursor == 0
    app._handle_key(curses.KEY_RIGHT)
    assert app.cursor == 1
    app._handle_key(curses.KEY_END)
    assert app.cursor == 3
    app._handle_key(curses.KEY_LEFT)
    assert app.cursor == 2


def test_edicion_backspace_en_medio() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "abc")
    app._handle_key(curses.KEY_LEFT)
    app._handle_key(127)
    assert app.expression == "ac"
    assert app.cursor == 1


def test_edicion_delete_borra_adelante() -> None:
    app = make_app()
    app._handle_key(ord("e"))
    _feed(app, "abc")
    app._handle_key(curses.KEY_HOME)
    app._handle_key(curses.KEY_DC)
    assert app.expression == "bc"
    assert app.cursor == 0


def test_capa_homerow_inserta_digitos() -> None:
    for key, valor in HOME_DIGITS.items():
        app = make_app()
        app.focus = "history"
        app._handle_key(ord(key))
        assert app.expression == valor, key


def test_teclado_wasd_navega() -> None:
    app = make_app()
    kb = Keyboard(None)  # type: ignore[arg-type]
    app.keyboard = kb  # type: ignore[assignment]
    app._handle_key(ord("s"))
    assert kb.row == 1
    app._handle_key(ord("w"))
    assert kb.row == 0
    app._handle_key(ord("d"))
    assert kb.col == 1
    app._handle_key(ord("a"))
    assert kb.col == 0


def test_teclado_d_mueve_y_no_borra() -> None:
    app = make_app()
    kb = Keyboard(None)  # type: ignore[arg-type]
    app.keyboard = kb  # type: ignore[assignment]
    app.expression = "9"
    app._handle_key(ord("d"))
    assert app.expression == "9"
    assert kb.col == 1


def test_teclado_x_limpia_display() -> None:
    app = make_app()
    app.keyboard = Keyboard(None)  # type: ignore[arg-type]
    app.focus = "keyboard"
    for char in "12+3":
        app._handle_key(ord(char))
    app._handle_key(ord("x"))
    assert app.expression == ""


def test_historial_ws_mueve() -> None:
    app = make_app()
    for i in range(3):
        app.history.add(f"{i}+0", str(i))
    app.focus = "history"
    app.history_panel.selected = 1
    app._handle_key(ord("w"))
    assert app.history_panel.selected == 0
    app._handle_key(ord("s"))
    assert app.history_panel.selected == 1


def test_historial_gG_extremos() -> None:
    app = make_app()
    for i in range(3):
        app.history.add(f"{i}+0", str(i))
    app.focus = "history"
    app._handle_key(ord("g"))
    assert app.history_panel.selected == 0
    app._handle_key(ord("G"))
    assert app.history_panel.selected == 2


def test_historial_x_borra_seleccionada() -> None:
    app = make_app()
    app.history.add("2+2", "4")
    app.history.add("3+3", "6")
    app.focus = "history"
    app._handle_key(ord("x"))
    assert len(app.history) == 1
    entry = app.history[0]
    assert entry is not None
    assert entry.expr == "2+2"


def test_historial_X_pide_confirmacion() -> None:
    app = make_app()
    app.history.add("2+2", "4")
    app.focus = "history"
    app._handle_key(ord("X"))
    assert app.pending_confirm is not None
    app._process_confirm(ord("y"))
    assert len(app.history) == 0


def test_variables_x_borra_seleccionada() -> None:
    app = make_app()
    app.calc.evaluate("x = 5")
    app.calc.evaluate("y = 3")
    app.focus = "vars"
    app._handle_key(ord("x"))
    assert "y" not in app.calc.variables.user_vars()


def test_h_toggle_hints() -> None:
    app = make_app()
    app.keyboard = Keyboard(None)  # type: ignore[arg-type]
    app._handle_key(ord("h"))
    assert app.key_hints is True
    assert app.keyboard.show_hints is True
    assert "h hints on" in app._status_text()
    app._handle_key(ord("h"))
    assert app.key_hints is False
    assert "h hints on" not in app._status_text()
