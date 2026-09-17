"""Tests de la persistencia de variables de usuario y historial en JSON."""

import json

from models.history import History, HistoryEntry
from models.variables import Variables
from tui import persist


def test_save_load_roundtrip(tmp_path) -> None:
    path = tmp_path / "variables.json"
    persist.save_variables({"x": 5.0, "y": 0.5}, path)
    assert persist.load_variables(path) == {"x": 5.0, "y": 0.5}


def test_load_inexistente_o_corrupto(tmp_path) -> None:
    assert persist.load_variables(tmp_path / "nope.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{ no es json", encoding="utf-8")
    assert persist.load_variables(bad) == {}


def test_load_filtra_invalidos(tmp_path) -> None:
    path = tmp_path / "v.json"
    path.write_text(
        json.dumps({"ok": 1, "pi": 3, "mal nombre": 1, "b": True, "s": "x"}),
        encoding="utf-8",
    )
    assert persist.load_variables(path) == {"ok": 1.0, "pi": 3.0}


def test_variables_path_junto_al_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CALC_CONFIG", str(tmp_path / "config.json"))
    assert persist.variables_path() == tmp_path / "variables.json"


def test_load_user_vars_filtra_builtins() -> None:
    variables = Variables()
    variables.load_user_vars({"x": 2, "pi": 3, "b": True, "mal nombre": 1})
    assert variables.user_vars() == {"x": 2.0}


def test_history_roundtrip(tmp_path) -> None:
    path = tmp_path / "history.json"
    entries = [HistoryEntry("2+2", "4", ""), HistoryEntry("9//4", "2", "[floor]")]
    persist.save_history(entries, path)
    assert persist.load_history(path) == entries


def test_history_load_inexistente_o_corrupto(tmp_path) -> None:
    assert persist.load_history(tmp_path / "nope.json") == []
    bad = tmp_path / "bad.json"
    bad.write_text("[ no es json", encoding="utf-8")
    assert persist.load_history(bad) == []


def test_history_load_filtra_invalidos(tmp_path) -> None:
    path = tmp_path / "h.json"
    path.write_text(
        json.dumps(
            [
                {"expr": "1+1", "result": "2"},
                {"expr": 1, "result": "2"},
                {"result": "2"},
                "x",
                {"expr": "2+2", "result": "4", "notation": 5},
            ]
        ),
        encoding="utf-8",
    )
    assert persist.load_history(path) == [
        HistoryEntry("1+1", "2", ""),
        HistoryEntry("2+2", "4", ""),
    ]


def test_history_path_junto_al_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CALC_CONFIG", str(tmp_path / "config.json"))
    assert persist.history_path() == tmp_path / "history.json"


def test_history_load_entries_recorta_al_maximo() -> None:
    history = History(max_size=2)
    history.load_entries([HistoryEntry(str(i), str(i)) for i in range(5)])
    assert [e.expr for e in history.entries()] == ["3", "4"]
