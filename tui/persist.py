"""Persistencia de variables e historial en JSON aparte de la config.

Los archivos viven junto al config (`~/.config/calc/`), respetando los overrides
de `config_path()`. La escritura es atómica y best-effort.
"""

import json
from pathlib import Path
from typing import Optional

from models.history import HistoryEntry
from tui.theme import config_path

FILENAME = "variables.json"
HISTORY_FILENAME = "history.json"
FUNCTIONS_FILENAME = "functions.json"


def variables_path() -> Path:
    """Ruta del archivo de variables, junto al config del usuario."""
    return config_path().with_name(FILENAME)


def load_variables(path: Optional[Path] = None) -> dict[str, float]:
    """Leer variables de usuario; {} si no existe, está corrupto o es inválido."""
    target = path or variables_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    result: dict[str, float] = {}
    for name, value in raw.items():
        if not isinstance(name, str) or not name.isidentifier():
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        result[name] = float(value)
    return result


def save_variables(store: dict[str, float], path: Optional[Path] = None) -> None:
    """Escribir las variables de forma atómica (ignora errores de E/S)."""
    target = path or variables_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(
            json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(target)
    except OSError:
        pass


def history_path() -> Path:
    """Ruta del archivo de historial, junto al config del usuario."""
    return config_path().with_name(HISTORY_FILENAME)


def functions_path() -> Path:
    """Ruta del archivo de funciones de usuario, junto al config del usuario."""
    return config_path().with_name(FUNCTIONS_FILENAME)


def load_functions(path: Optional[Path] = None) -> list[dict]:
    """Leer funciones de usuario; [] si no existe, está corrupto o es inválido."""
    target = path or functions_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    result: list[dict] = []
    for item in raw:
        name = item.get("name") if isinstance(item, dict) else None
        params = item.get("params") if isinstance(item, dict) else None
        body = item.get("body") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name.isidentifier():
            continue
        if not isinstance(params, list) or not all(
            isinstance(p, str) and p.isidentifier() for p in params
        ):
            continue
        if not isinstance(body, str):
            continue
        result.append({"name": name, "params": params, "body": body})
    return result


def save_functions(data: list[dict], path: Optional[Path] = None) -> None:
    """Escribir las funciones de forma atómica (ignora errores de E/S)."""
    target = path or functions_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(target)
    except OSError:
        pass


def load_history(path: Optional[Path] = None) -> list[HistoryEntry]:
    """Leer el historial; [] si no existe, está corrupto o es inválido."""
    target = path or history_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    result: list[HistoryEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        expr = item.get("expr")
        value = item.get("result")
        notation = item.get("notation", "")
        if not isinstance(expr, str) or not isinstance(value, str):
            continue
        if not isinstance(notation, str):
            notation = ""
        result.append(HistoryEntry(expr, value, notation))
    return result


def save_history(entries: list[HistoryEntry], path: Optional[Path] = None) -> None:
    """Escribir el historial de forma atómica (ignora errores de E/S)."""
    target = path or history_path()
    data = [
        {"expr": e.expr, "result": e.result, "notation": e.notation} for e in entries
    ]
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(target)
    except OSError:
        pass
