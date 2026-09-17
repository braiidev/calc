"""Tests de temas, glifos y config del usuario."""

import curses
import json

from tui import theme as th


def test_config_path_override(monkeypatch, tmp_path) -> None:
    target = tmp_path / "c.json"
    monkeypatch.setenv("CALC_CONFIG", str(target))
    assert th.config_path() == target


def test_config_path_xdg(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CALC_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert th.config_path() == tmp_path / "calc" / "config.json"


def test_ensure_config_crea_defaults(monkeypatch, tmp_path) -> None:
    target = tmp_path / "calc" / "config.json"
    monkeypatch.setenv("CALC_CONFIG", str(target))
    cfg = th.ensure_config()
    assert target.is_file()
    assert cfg["theme"] == "frio"
    assert json.loads(target.read_text(encoding="utf-8"))["theme"] == "frio"


def test_load_config_ignora_corrupto(monkeypatch, tmp_path) -> None:
    target = tmp_path / "config.json"
    target.write_text("{ no es json", encoding="utf-8")
    monkeypatch.setenv("CALC_CONFIG", str(target))
    assert th.load_config()["theme"] == "frio"


def test_load_config_filtra_colores_raros(monkeypatch, tmp_path) -> None:
    target = tmp_path / "config.json"
    target.write_text(
        json.dumps({"colors": {"result": "blue", "nope": "red", "x": 5}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("CALC_CONFIG", str(target))
    assert th.load_config()["colors"] == {"result": "blue"}


def test_resolve_theme_estilo_por_filas() -> None:
    cfg = {"theme": "frio"}
    assert th.resolve_theme(cfg, th.BOXED_MIN_ROWS - 1, True).style == "minimal"
    assert th.resolve_theme(cfg, th.BOXED_MIN_ROWS, True).style == "boxed"


def test_resolve_theme_estilo_independiente_del_tono() -> None:
    chico = th.resolve_theme({"theme": "calido"}, 10, True)
    grande = th.resolve_theme({"theme": "calido"}, 40, True)
    assert chico.style == "minimal"
    assert grande.style == "boxed"


def test_resolve_theme_sin_color_usa_mono() -> None:
    theme = th.resolve_theme({"theme": "frio"}, 30, False)
    assert theme.colors == th.MONO_COLORS


def test_resolve_theme_override_colores() -> None:
    cfg = {"theme": "frio", "colors": {"result": "blue+bold"}}
    assert th.resolve_theme(cfg, 24, True).colors["result"] == "blue+bold"


def test_resolve_theme_nombre_invalido() -> None:
    assert th.resolve_theme({"theme": "zzz"}, 24, True).name == "frio"


def test_tonos_tienen_paletas_distintas() -> None:
    frio = th.resolve_theme({"theme": "frio"}, 24, True)
    calido = th.resolve_theme({"theme": "calido"}, 24, True)
    contraste = th.resolve_theme({"theme": "contraste"}, 24, True)
    assert frio.colors["operator"] == "cyan"
    assert calido.colors["operator"] == "red"
    assert contraste.colors["operator"] == "white+bold"


def test_choose_glyphs() -> None:
    assert th.choose_glyphs("ascii")["cursor"] == ">"
    assert th.choose_glyphs("unicode")["cursor"] == "▶"


def test_next_theme_ciclo() -> None:
    assert th.next_theme("mono") == "calido"
    assert th.next_theme("calido") == "frio"
    assert th.next_theme("contraste") == "mono"
    assert th.next_theme("desconocido") == "mono"


def test_role_attrs_sin_color_solo_mods() -> None:
    theme = th.resolve_theme({"theme": "frio"}, 24, False)
    attrs = th.role_attrs(theme, use_color=False)
    assert attrs["result"] == curses.A_BOLD
    assert attrs["number"] == 0
