#!/usr/bin/env python3
"""Calculadora TUI — punto de entrada y ciclo de vida (update/uninstall)."""

import argparse
import curses
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tui.app import App

VERSION = "v0.8"


def _repo_root() -> str:
    from tui.update import repo_root

    return repo_root()


def _cli_update() -> int:
    from tui.update import do_update

    result = do_update(_repo_root())
    print(result.message)
    return 0 if result.ok else 1


def _cli_check_update() -> int:
    from tui.update import check_update

    info = check_update(_repo_root())
    if not info.ok:
        print(f"No se pudo verificar: {info.error}", file=sys.stderr)
        return 1
    if info.behind > 0:
        print(
            f"Hay una actualización disponible ({info.available}). Ejecutá: calc --update"
        )
    else:
        print(f"Estás al día ({info.current})")
    return 0


def _cli_reinstall() -> int:
    installer = os.path.join(_repo_root(), "install.sh")
    if not os.path.isfile(installer):
        print(f"Error: no se encontró {installer}", file=sys.stderr)
        return 1
    print("Reinstalando calc (corre install.sh)...")
    print("  puede pedir sudo para el wrapper.")
    result = subprocess.run(["bash", installer])
    return 0 if result.returncode == 0 else 1


def _installed_repo() -> str | None:
    """Ruta de la instalación si este código corre desde ahí (no desde el dev tree)."""
    repo = os.path.realpath(_repo_root())
    expected = os.path.realpath(
        os.path.expanduser(os.environ.get("CALC_DIR", "~/.config/calc"))
    )
    return repo if repo == expected else None


def _cli_uninstall(purge: bool) -> int:
    from tui.persist import variables_path
    from tui.theme import config_path

    repo = _installed_repo()
    if repo is None:
        print(
            "Error: el código no vive en una instalación vía install.sh; no se borra.",
            file=sys.stderr,
        )
        print(f"  (repo detectado: {_repo_root()})", file=sys.stderr)
        return 1

    print("Desinstalando calc...")
    bin_path = os.environ.get("CALC_BIN", "/usr/local/bin/calc")
    if os.path.exists(bin_path):
        print(f"  - eliminando wrapper: {bin_path} (sudo)")
        subprocess.run(["sudo", "rm", "-f", bin_path], check=False)

    if purge:
        print(f"  - eliminando instalación y datos: {repo}")
        shutil.rmtree(repo, ignore_errors=True)
    else:
        keep: dict[str, bytes] = {}
        for path in (config_path(), variables_path()):
            try:
                if path.is_file() and os.path.realpath(path).startswith(repo + os.sep):
                    keep[path.name] = path.read_bytes()
            except OSError:
                pass
        shutil.rmtree(repo, ignore_errors=True)
        os.makedirs(repo, exist_ok=True)
        for name, data in keep.items():
            (Path(repo) / name).write_bytes(data)
        if keep:
            print(f"  - datos conservados en {repo}: {', '.join(sorted(keep))}")

    print("calc desinstalado")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calculadora TUI (curses)")
    parser.add_argument("--version", action="version", version=f"calc {VERSION}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--update", action="store_true", help="actualiza (git pull) y sale"
    )
    group.add_argument(
        "--check-update", action="store_true", help="verifica si hay versión nueva"
    )
    group.add_argument(
        "--reinstall", action="store_true", help="reinstala corriendo install.sh"
    )
    group.add_argument(
        "--uninstall", action="store_true", help="desinstala (conserva los datos)"
    )
    parser.add_argument(
        "--purge", action="store_true", help="con --uninstall: borra también los datos"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.update:
        return _cli_update()
    if args.check_update:
        return _cli_check_update()
    if args.reinstall:
        return _cli_reinstall()
    if args.uninstall:
        return _cli_uninstall(args.purge)
    if args.purge:
        print(
            "Error: --purge solo tiene sentido junto con --uninstall", file=sys.stderr
        )
        return 2

    try:
        curses.wrapper(lambda stdscr: App(stdscr).run())
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # noqa: BLE001 — proteger la terminal
        try:
            curses.endwin()
        except Exception:
            pass
        print(f"Error fatal: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
