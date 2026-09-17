"""Tests de la lógica de la TUI (sin curses): bandeja, foco y variables."""

from calculator import Calculator
from models.history import History
from tui.app import App


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
        return entry[0], entry[1], idx

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
    assert app.history[0] == ("2+3", "5")
