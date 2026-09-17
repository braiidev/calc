"""Persistencia de las variables de usuario en un JSON aparte de la config.

El archivo vive junto al config (`~/.config/calc/variables.json`), respetando
los overrides de `config_path()`. La escritura es atómica y best-effort.
"""

import json
from pathlib import Path
from typing import Optional

from tui.theme import config_path

FILENAME = "variables.json"


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
