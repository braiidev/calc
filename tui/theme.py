"""Temas, glifos y config del usuario.

Centraliza las paletas de color (pares de curses), los glifos Unicode/ASCII y las
preferencias de UI. La config vive en `~/.config/calc/config.json` (override:
`$CALC_CONFIG` o `$XDG_CONFIG_HOME`) y se crea con defaults la primera vez.
"""

import curses
import json
import locale
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ----- roles de color -----

ROLES = (
    "expression",
    "result",
    "error",
    "number",
    "operator",
    "action",
    "title",
    "title_dim",
    "selection",
    "hint",
    "separator",
)

# Par de curses por rol (1-based; el 0 está reservado).
ROLE_PAIR: dict[str, int] = {role: i + 1 for i, role in enumerate(ROLES)}

_COLORS: dict[str, int] = {
    "default": -1,
    "black": curses.COLOR_BLACK,
    "red": curses.COLOR_RED,
    "green": curses.COLOR_GREEN,
    "yellow": curses.COLOR_YELLOW,
    "blue": curses.COLOR_BLUE,
    "magenta": curses.COLOR_MAGENTA,
    "cyan": curses.COLOR_CYAN,
    "white": curses.COLOR_WHITE,
}

_MODS: dict[str, int] = {
    "bold": curses.A_BOLD,
    "dim": curses.A_DIM,
    "reverse": curses.A_REVERSE,
}

# Especificación de cada rol: "color+modificador+..." (color opcional).
# Tonos de color disponibles (T cicla entre ellos). El estilo de bordes NO se
# elige acá: se deriva del alto de la terminal en `resolve_theme`.

# Monocromo: sin color, sólo atributos.
MONO_COLORS: dict[str, str] = {
    "expression": "default",
    "result": "bold",
    "error": "reverse",
    "number": "default",
    "operator": "default",
    "action": "dim",
    "title": "bold",
    "title_dim": "dim",
    "selection": "reverse",
    "hint": "dim",
    "separator": "dim",
}

# Cálido: rojos/amarillos/magenta.
WARM_COLORS: dict[str, str] = {
    "expression": "yellow+bold",
    "result": "yellow+bold",
    "error": "red+bold",
    "number": "white",
    "operator": "red",
    "action": "magenta",
    "title": "yellow+bold",
    "title_dim": "yellow+dim",
    "selection": "reverse+yellow",
    "hint": "yellow+dim",
    "separator": "yellow+dim",
}

# Frío: cian/azul/verde (paleta base).
COOL_COLORS: dict[str, str] = {
    "expression": "cyan+bold",
    "result": "green+bold",
    "error": "red+bold",
    "number": "white",
    "operator": "cyan",
    "action": "blue",
    "title": "cyan+bold",
    "title_dim": "cyan+dim",
    "selection": "reverse+cyan",
    "hint": "cyan+dim",
    "separator": "cyan+dim",
}

# Contraste: máximo contraste con negrita/reverse.
CONTRAST_COLORS: dict[str, str] = {
    "expression": "white+bold",
    "result": "white+bold",
    "error": "red+reverse",
    "number": "white",
    "operator": "white+bold",
    "action": "white+bold",
    "title": "white+reverse",
    "title_dim": "dim",
    "selection": "reverse",
    "hint": "dim",
    "separator": "dim",
}

# ----- glifos -----

UNICODE_GLYPHS: dict[str, str] = {
    "h": "─",
    "v": "│",
    "tl": "┌",
    "tr": "┐",
    "bl": "└",
    "br": "┘",
    "cursor": "▶",
    "prompt": "›",
    "backspace": "⌫",
    "enter": "↵",
    "warn": "⚠",
    "root": "ⁿ√",
}

ASCII_GLYPHS: dict[str, str] = {
    "h": "-",
    "v": "|",
    "tl": "+",
    "tr": "+",
    "bl": "+",
    "br": "+",
    "cursor": ">",
    "prompt": ">",
    "backspace": "DEL",
    "enter": "=",
    "warn": "!",
    "root": "root",
}

# ----- tonos de color -----

# Orden del ciclo de la tecla T.
THEME_ORDER = ("mono", "calido", "frio", "contraste")
DEFAULT_TONE = "frio"
# Con esta cantidad de filas o más se dibujan bordes (si no, modo minimal).
BOXED_MIN_ROWS = 28

PALETTES: dict[str, dict[str, str]] = {
    "mono": MONO_COLORS,
    "calido": WARM_COLORS,
    "frio": COOL_COLORS,
    "contraste": CONTRAST_COLORS,
}


@dataclass(frozen=True)
class Theme:
    """Tema resuelto, listo para dibujar."""

    name: str
    style: str  # "boxed" | "minimal"
    glyphs: dict[str, str]
    colors: dict[str, str]
    live_notation: bool = True
    status_bar: bool = True


# ----- config -----

DEFAULT_CONFIG: dict = {
    "theme": DEFAULT_TONE,
    "glyphs": "auto",
    "live_notation": True,
    "status_bar": True,
    "colors": {},
}


def config_path() -> Path:
    """Ruta de la config: `$CALC_CONFIG` > `$XDG_CONFIG_HOME/calc` > `~/.config/calc`."""
    env = os.environ.get("CALC_CONFIG")
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "calc" / "config.json"


def load_config() -> dict:
    """Leer la config del disco, con defaults para lo que falte o esté corrupto."""
    cfg = dict(DEFAULT_CONFIG)
    path = config_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            for key in DEFAULT_CONFIG:
                if key in data:
                    cfg[key] = data[key]
            if isinstance(cfg.get("colors"), dict):
                cfg["colors"] = {
                    role: value
                    for role, value in cfg["colors"].items()
                    if role in ROLES and isinstance(value, str)
                }
            else:
                cfg["colors"] = {}
    return cfg


def save_config(cfg: dict) -> bool:
    """Escribir la config. Retorna True si se pudo."""
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def ensure_config() -> dict:
    """Cargar la config, creándola con defaults si no existe."""
    if not config_path().is_file():
        save_config(DEFAULT_CONFIG)
    return load_config()


# ----- resolución y aplicación -----


def choose_glyphs(mode: str) -> dict[str, str]:
    """Glifos Unicode o ASCII; en `auto` decide por el encoding del locale."""
    if mode == "ascii":
        return dict(ASCII_GLYPHS)
    if mode == "unicode":
        return dict(UNICODE_GLYPHS)
    encoding = (locale.getpreferredencoding(False) or "").upper()
    return dict(UNICODE_GLYPHS if "UTF" in encoding else ASCII_GLYPHS)


def theme_names() -> tuple[str, ...]:
    return THEME_ORDER


def next_theme(name: str) -> str:
    """Siguiente tono de color en el ciclo (para la tecla T)."""
    if name not in THEME_ORDER:
        return THEME_ORDER[0]
    return THEME_ORDER[(THEME_ORDER.index(name) + 1) % len(THEME_ORDER)]


def resolve_theme(
    cfg: dict, rows: int, use_color: bool, glyph_mode: Optional[str] = None
) -> Theme:
    """Resolver el tema efectivo: tono de color (config) y estilo (alto)."""
    name = cfg.get("theme", DEFAULT_TONE)
    if name not in PALETTES:
        name = DEFAULT_TONE

    # El estilo con/sin bordes lo decide el alto, no la config.
    style = "boxed" if rows >= BOXED_MIN_ROWS else "minimal"

    colors = dict(PALETTES[name])
    if not use_color:
        colors = dict(MONO_COLORS)
    overrides = cfg.get("colors") or {}
    colors.update({role: value for role, value in overrides.items() if role in ROLES})

    mode = glyph_mode if glyph_mode is not None else cfg.get("glyphs", "auto")
    return Theme(
        name=name,
        style=style,
        glyphs=choose_glyphs(mode),
        colors=colors,
        live_notation=bool(cfg.get("live_notation", True)),
        status_bar=bool(cfg.get("status_bar", True)),
    )


def _parse_spec(spec: str) -> tuple[int, int]:
    """`"cyan+bold"` -> (COLOR_CYAN, A_BOLD)."""
    color = -1
    mods = 0
    for part in spec.split("+"):
        part = part.strip()
        if part in _COLORS:
            color = _COLORS[part]
        elif part in _MODS:
            mods |= _MODS[part]
    return color, mods


def init_colors() -> bool:
    """Inicializar curses para color. Retorna True si hay color disponible."""
    if not curses.has_colors():
        return False
    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass
    return True


def role_attrs(theme: Theme, use_color: bool) -> dict[str, int]:
    """Atributos de curses por rol, según el tema. Sin terminal real: sólo mods."""
    attrs: dict[str, int] = {}
    for role in ROLES:
        color, mods = _parse_spec(theme.colors.get(role, ""))
        if use_color and color != -1:
            curses.init_pair(ROLE_PAIR[role], color, -1)
            attrs[role] = curses.color_pair(ROLE_PAIR[role]) | mods
        else:
            attrs[role] = mods
    return attrs
