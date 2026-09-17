"""Tests de `install.sh`: flags de ciclo de vida, guards y flujo de instalación.

Corren en un sandbox (CALC_DIR/CALC_BIN apuntan a `tmp_path`) y usan un `sudo`
falso en el PATH para no requerir privilegios.
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"

pytestmark = pytest.mark.skipif(not INSTALL.exists(), reason="falta install.sh")


def _run(args, *, calc_dir, calc_bin, path_prefix=None, repo_url=None):
    env = os.environ.copy()
    env["CALC_DIR"] = str(calc_dir)
    env["CALC_BIN"] = str(calc_bin)
    if repo_url is not None:
        env["REPO_URL"] = str(repo_url)
    if path_prefix is not None:
        env["PATH"] = f"{path_prefix}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", str(INSTALL), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def _sudo_shim(tmp_path: Path) -> Path:
    """`sudo` falso que ejecuta el comando sin privilegios."""
    shim = tmp_path / "shim"
    shim.mkdir(exist_ok=True)
    sudo = shim / "sudo"
    sudo.write_text('#!/bin/sh\nexec "$@"\n')
    sudo.chmod(sudo.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return shim


def _source_repo(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('ok')\n")
    (src / "install.sh").write_text("#!/bin/bash\necho installer\n")
    subprocess.run(["git", "init", "-q"], cwd=src, check=True)
    subprocess.run(["git", "add", "."], cwd=src, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=src,
        check=True,
    )
    return src


def _fake_install(tmp_path: Path) -> Path:
    app = tmp_path / "app"
    app.mkdir()
    (app / "main.py").write_text("# código\n")
    (app / "install.sh").write_text("#!/bin/bash\necho installer\n")
    return app


def test_version(tmp_path: Path) -> None:
    r = _run(["--version"], calc_dir=tmp_path / "app", calc_bin=tmp_path / "calc")
    assert r.returncode == 0
    assert "v0.9" in r.stdout


def test_help(tmp_path: Path) -> None:
    r = _run(["--help"], calc_dir=tmp_path / "app", calc_bin=tmp_path / "calc")
    assert r.returncode == 0
    assert "uso:" in r.stdout


def test_argumento_invalido(tmp_path: Path) -> None:
    r = _run(["--nope"], calc_dir=tmp_path / "app", calc_bin=tmp_path / "calc")
    assert r.returncode == 2
    assert "desconocido" in r.stderr


def _sh_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CALC_DIR"] = str(tmp_path / "app")
    env["CALC_BIN"] = str(tmp_path / "calc")
    return env


def test_funciona_con_sh_posix(tmp_path: Path) -> None:
    r = subprocess.run(
        ["sh", str(INSTALL), "--version"],
        capture_output=True,
        text=True,
        env=_sh_env(tmp_path),
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "v0.9" in r.stdout


def test_piped_via_sh(tmp_path: Path) -> None:
    with INSTALL.open() as script:
        r = subprocess.run(
            ["sh", "-s", "--", "--version"],
            stdin=script,
            capture_output=True,
            text=True,
            env=_sh_env(tmp_path),
            timeout=60,
        )
    assert r.returncode == 0, r.stderr
    assert "v0.9" in r.stdout


def test_uninstall_rechaza_app_dir_inseguro(tmp_path: Path) -> None:
    r = _run(["--uninstall"], calc_dir=Path("/"), calc_bin=tmp_path / "calc")
    assert r.returncode == 1
    assert "inseguro" in r.stderr


def test_uninstall_rechaza_sin_instalacion(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    r = _run(["--uninstall"], calc_dir=app, calc_bin=tmp_path / "calc")
    assert r.returncode == 1
    assert "no parece" in r.stderr


def test_uninstall_conserva_datos(tmp_path: Path) -> None:
    app = _fake_install(tmp_path)
    (app / "config.json").write_text('{"theme":"frio"}')
    (app / "variables.json").write_text('{"x": 1.0}')
    r = _run(["--uninstall"], calc_dir=app, calc_bin=tmp_path / "calc")
    assert r.returncode == 0
    assert not (app / "main.py").exists()
    assert not (app / "install.sh").exists()
    assert (app / "config.json").read_text() == '{"theme":"frio"}'
    assert (app / "variables.json").read_text() == '{"x": 1.0}'


def test_uninstall_purge_borra_todo(tmp_path: Path) -> None:
    app = _fake_install(tmp_path)
    (app / "config.json").write_text("{}")
    r = _run(["--uninstall", "--purge"], calc_dir=app, calc_bin=tmp_path / "calc")
    assert r.returncode == 0
    assert not app.exists()


def test_uninstall_quita_wrapper_propio(tmp_path: Path) -> None:
    app = _fake_install(tmp_path)
    binf = tmp_path / "bin" / "calc"
    binf.parent.mkdir()
    binf.write_text(f'#!/bin/bash\nexec python3 "{app}/main.py" "$@"\n')
    r = _run(
        ["--uninstall"],
        calc_dir=app,
        calc_bin=binf,
        path_prefix=_sudo_shim(tmp_path),
    )
    assert r.returncode == 0
    assert not binf.exists()


def test_uninstall_no_borra_wrapper_ajeno(tmp_path: Path) -> None:
    app = _fake_install(tmp_path)
    binf = tmp_path / "bin" / "calc"
    binf.parent.mkdir()
    binf.write_text("contenido ajeno\n")
    r = _run(
        ["--uninstall"],
        calc_dir=app,
        calc_bin=binf,
        path_prefix=_sudo_shim(tmp_path),
    )
    assert r.returncode == 0
    assert binf.exists()
    assert "no se borra" in r.stderr


def test_update_falla_sin_repo(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    r = _run(["--update"], calc_dir=app, calc_bin=tmp_path / "calc")
    assert r.returncode == 1
    assert "no es un repo" in r.stderr


def test_install_clona_y_crea_wrapper(tmp_path: Path) -> None:
    src = _source_repo(tmp_path)
    app = tmp_path / "app"
    binf = tmp_path / "bin" / "calc"
    r = _run(
        [],
        calc_dir=app,
        calc_bin=binf,
        path_prefix=_sudo_shim(tmp_path),
        repo_url=src,
    )
    assert r.returncode == 0, r.stderr
    assert (app / "main.py").exists()
    assert (app / ".git").is_dir()
    assert binf.exists()
    assert "main.py" in binf.read_text()
    assert os.access(binf, os.X_OK)


def test_install_hace_backup_de_dir_existente(tmp_path: Path) -> None:
    src = _source_repo(tmp_path)
    app = tmp_path / "app"
    app.mkdir()
    (app / "viejo.txt").write_text("x")
    r = _run(
        [],
        calc_dir=app,
        calc_bin=tmp_path / "bin" / "calc",
        path_prefix=_sudo_shim(tmp_path),
        repo_url=src,
    )
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "app.bak" / "viejo.txt").exists()


def test_update_actualiza_repo_clonado(tmp_path: Path) -> None:
    src = _source_repo(tmp_path)
    app = tmp_path / "app"
    r = _run(
        [],
        calc_dir=app,
        calc_bin=tmp_path / "bin" / "calc",
        path_prefix=_sudo_shim(tmp_path),
        repo_url=src,
    )
    assert r.returncode == 0, r.stderr
    (src / "nuevo.txt").write_text("y")
    subprocess.run(["git", "add", "."], cwd=src, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "add"],
        cwd=src,
        check=True,
    )
    r = _run(
        ["--update"],
        calc_dir=app,
        calc_bin=tmp_path / "bin" / "calc",
        path_prefix=_sudo_shim(tmp_path),
    )
    assert r.returncode == 0, r.stderr
    assert (app / "nuevo.txt").exists()
