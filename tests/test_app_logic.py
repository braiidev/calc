"""Tests de la lógica de la bandeja del historial (sin curses)."""

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


def make_app() -> App:
    app = object.__new__(App)
    app.calc = Calculator()
    app.history = History()
    app.history_panel = StubHistoryPanel(app.history)  # type: ignore[assignment]
    app.expression = ""
    app.result_display = ""
    app.error = ""
    app.just_evaluated = False
    app.focus = "keyboard"
    app.pending_confirm = None
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
