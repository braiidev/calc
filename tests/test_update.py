"""Tests del módulo de auto-update (sin red: se usa un dir que no es repo git)."""

from pathlib import Path

from tui import update


def test_repo_root_apunta_al_repo() -> None:
    root = Path(update.repo_root())
    assert (root / "main.py").is_file()
    assert (root / "tui" / "update.py").is_file()


def test_check_update_en_dir_sin_git(tmp_path: Path) -> None:
    info = update.check_update(str(tmp_path))
    assert info.ok is False
    assert info.error


def test_do_update_en_dir_sin_git(tmp_path: Path) -> None:
    result = update.do_update(str(tmp_path))
    assert result.ok is False
    assert "no es un repositorio" in result.message


def test_auto_update_se_desactiva_por_env(monkeypatch) -> None:
    monkeypatch.delenv("CALC_NO_AUTO_UPDATE", raising=False)
    assert update.is_auto_update_enabled()
    monkeypatch.setenv("CALC_NO_AUTO_UPDATE", "1")
    assert not update.is_auto_update_enabled()
    monkeypatch.setenv("CALC_NO_AUTO_UPDATE", "yes")
    assert not update.is_auto_update_enabled()
