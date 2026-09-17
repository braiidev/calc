"""Tests del CLI de ciclo de vida (update/check/uninstall) sin tocar red ni sudo."""

from pathlib import Path

import pytest

import main


def test_parse_update_y_check() -> None:
    assert main.parse_args(["--update"]).update is True
    assert main.parse_args(["--check-update"]).check_update is True


def test_parse_uninstall_con_purge() -> None:
    args = main.parse_args(["--uninstall", "--purge"])
    assert args.uninstall is True
    assert args.purge is True


def test_flags_de_ciclo_son_excluyentes() -> None:
    with pytest.raises(SystemExit):
        main.parse_args(["--update", "--uninstall"])


def test_version_imprime_y_sale(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main.main(["--version"])
    assert exc.value.code == 0
    assert main.VERSION in capsys.readouterr().out


def test_purge_sin_uninstall_es_error(capsys) -> None:
    assert main.main(["--purge"]) == 2
    assert "solo tiene sentido" in capsys.readouterr().err


def test_purge_con_otra_accion_es_error(capsys) -> None:
    assert main.main(["--update", "--purge"]) == 2
    assert "solo tiene sentido" in capsys.readouterr().err


def test_installed_repo_no_es_el_dev_tree(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CALC_DIR", str(tmp_path / "otro"))
    assert main._installed_repo() is None


def test_installed_repo_requiere_marcadores(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "calc"
    repo.mkdir()
    (repo / "main.py").write_text("x", encoding="utf-8")
    monkeypatch.setattr(main, "_repo_root", lambda: str(repo))
    monkeypatch.setenv("CALC_DIR", str(repo))
    assert main._installed_repo() is None  # falta install.sh
    (repo / "install.sh").write_text("x", encoding="utf-8")
    assert main._installed_repo() == str(repo)


def test_installed_repo_rechaza_home(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "main.py").write_text("x", encoding="utf-8")
    (home / "install.sh").write_text("x", encoding="utf-8")
    monkeypatch.setattr(main, "_repo_root", lambda: str(home))
    monkeypatch.setenv("CALC_DIR", str(home))
    monkeypatch.setenv("HOME", str(home))
    assert main._installed_repo() is None


def test_looks_like_wrapper(tmp_path) -> None:
    wrapper = tmp_path / "calc"
    wrapper.write_text('#!/bin/bash\nexec python3 /x/main.py "$@"\n', encoding="utf-8")
    assert main._looks_like_wrapper(str(wrapper))
    ajeno = tmp_path / "otro"
    ajeno.write_text("#!/bin/bash\necho hola\n", encoding="utf-8")
    assert not main._looks_like_wrapper(str(ajeno))
    assert not main._looks_like_wrapper(str(tmp_path / "noexiste"))


def test_uninstall_no_borra_si_no_es_instalacion(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CALC_DIR", str(tmp_path / "otro"))
    assert main._cli_uninstall(False) == 1
    assert (Path(main._repo_root()) / "main.py").is_file()
    assert "no se borra" in capsys.readouterr().err


def test_uninstall_conserva_datos(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "calc"
    repo.mkdir()
    (repo / "main.py").write_text("x", encoding="utf-8")
    (repo / "install.sh").write_text("x", encoding="utf-8")
    (repo / ".git").mkdir()
    (repo / "config.json").write_text('{"theme": "frio"}', encoding="utf-8")
    (repo / "variables.json").write_text('{"x": 5.0}', encoding="utf-8")
    monkeypatch.setattr(main, "_repo_root", lambda: str(repo))
    monkeypatch.setenv("CALC_DIR", str(repo))
    monkeypatch.setenv("CALC_CONFIG", str(repo / "config.json"))
    monkeypatch.setenv("CALC_BIN", str(tmp_path / "bin" / "calc"))

    assert main._cli_uninstall(False) == 0
    assert (repo / "config.json").is_file()
    assert (repo / "variables.json").is_file()
    assert not (repo / "main.py").exists()


def test_uninstall_purge_borra_todo(tmp_path, monkeypatch) -> None:
    repo = tmp_path / "calc"
    repo.mkdir()
    (repo / "main.py").write_text("x", encoding="utf-8")
    (repo / "install.sh").write_text("x", encoding="utf-8")
    (repo / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(main, "_repo_root", lambda: str(repo))
    monkeypatch.setenv("CALC_DIR", str(repo))
    monkeypatch.setenv("CALC_CONFIG", str(repo / "config.json"))
    monkeypatch.setenv("CALC_BIN", str(tmp_path / "bin" / "calc"))

    assert main._cli_uninstall(True) == 0
    assert not repo.exists()
