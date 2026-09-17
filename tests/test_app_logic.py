"""Tests de la lógica de la TUI (sin curses): bandeja, foco y variables."""

from calculator import Calculator
from models.history import History
from tui.app import App
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


def make_app() -> App:
    app = object.__new__(App)
    app.calc = Calculator()
    app.history = History()
    app.history_panel = StubHistoryPanel(app.history)  # type: ignore[assignment]
    app.vars_panel = StubVarsPanel(app.calc.variables)  # type: ignore[assignment]
    app.expression = ""
    app.result_display = ""
    app.error = ""
    app.just_evaluated = False
    app.focus = "keyboard"
    app.show_help = False
    app.pending_confirm = None
    app._pending_confirm_action = "clear_history"
    app._edit_counter = 0
    app._last_tray = None
    app._last_tray_edit = -1
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
    app.theme = resolve_theme({"theme": "auto"}, 24, False)

    class KB:
        def focused_description(self):
            return "sumar"

    app.keyboard = KB()  # type: ignore[assignment]
    text = app._status_text()
    assert "teclado" in text
    assert "sumar" in text
    assert "tab historial" in text


def test_status_text_otros_focos() -> None:
    app = make_app()
    app.theme = resolve_theme({"theme": "auto"}, 24, False)
    app.focus = "history"
    assert "historial" in app._status_text()
    app.focus = "vars"
    assert "variables" in app._status_text()
    app.show_help = True
    assert "ayuda" in app._status_text()


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


def test_toggle_focus_ciclo() -> None:
    app = make_app()
    app._toggle_focus()
    assert app.focus == "history"
    app._toggle_focus()
    assert app.focus == "vars"
    app._toggle_focus()
    assert app.focus == "keyboard"


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


def test_historial_guarda_notacion() -> None:
    app = make_app()
    for char in "root(8,3)":
        app._insert(char)
    app._handle_action("eval", "")
    entry = app.history[0]
    assert entry is not None
    assert entry.notation == "[cbrt]"
