"""Self-update vía git (patrón Clock/Player), sin dependencias externas.

La instalación es un clone de git en `~/.config/calc` (o `$CALC_DIR`), así que
la raíz del repo es `parents[1]` de este módulo (`tui/update.py` → `tui` → raíz).

La actualización se decide por **commits** (`git rev-list --count
HEAD..origin/main`), no por versiones: es inmune al defasaje entre el contador
de tasks (v0.N) y cualquier semver de producto.
"""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

GIT_TIMEOUT = 8
PULL_TIMEOUT = 30

_lock = threading.Lock()


def repo_root() -> str:
    """Raíz del repo git que contiene este paquete (install desde clone)."""
    return str(Path(__file__).resolve().parents[1])


def _git_env() -> dict[str, str]:
    """Entorno para git: sin prompts interactivos que ensucien la TUI."""
    env = dict(os.environ)
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GCM_INTERACTIVE", "never")
    # ssh: si no hay comando custom, evitar que pida host key/password y cuelgue.
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    return env


def _git(
    repo: str, args: list[str], timeout: int = GIT_TIMEOUT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_git_env(),
        stdin=subprocess.DEVNULL,
    )


def _short_error(stderr: str, fallback: str) -> str:
    """Primera línea del error de git (los suyos son multi-línea)."""
    lines = (stderr or "").strip().splitlines()
    return lines[0] if lines else fallback


def _describe(repo: str, rev: str) -> str:
    try:
        r = _git(repo, ["describe", "--tags", rev, "--abbrev=0"])
        if r.returncode == 0:
            return r.stdout.strip()
        s = _git(repo, ["rev-parse", "--short", rev])
        if s.returncode == 0:
            return s.stdout.strip()
    except Exception:  # noqa: BLE001 — describe es best-effort
        pass
    return rev[:7]


@dataclass
class UpdateInfo:
    """Resultado de `check_update`: commits detrás y revisiones implicadas."""

    ok: bool
    error: str | None = None
    behind: int = 0
    current: str = ""
    available: str = ""


def check_update(repo: str) -> UpdateInfo:
    """Devuelve cuántos commits está detrás `repo` respecto de origin/main."""
    with _lock:
        return _check_update_unlocked(repo)


def _check_update_unlocked(repo: str) -> UpdateInfo:
    if not os.path.isdir(os.path.join(repo, ".git")):
        return UpdateInfo(False, "no es un repositorio git")
    try:
        fetch = _git(repo, ["fetch", "origin"], timeout=GIT_TIMEOUT)
        if fetch.returncode != 0:
            return UpdateInfo(False, _short_error(fetch.stderr, "fetch falló"))
        count = _git(repo, ["rev-list", "--count", "HEAD..origin/main"])
        if count.returncode != 0:
            return UpdateInfo(False, _short_error(count.stderr, "rev-list falló"))
        behind = int((count.stdout or "0").strip() or 0)
        return UpdateInfo(
            ok=True,
            behind=behind,
            current=_describe(repo, "HEAD"),
            available=_describe(repo, "origin/main"),
        )
    except FileNotFoundError:
        return UpdateInfo(False, "git no está instalado")
    except Exception as exc:  # noqa: BLE001 — no romper por un git raro
        return UpdateInfo(False, str(exc))


@dataclass
class UpdateResult:
    """Resultado de `do_update`: éxito y mensaje para mostrar."""

    ok: bool
    message: str


def do_update(repo: str) -> UpdateResult:
    """Aplicar la actualización si hay commits detrás. Si falla el pull, resetea."""
    with _lock:
        info = _check_update_unlocked(repo)
        if not info.ok:
            return UpdateResult(False, f"No se pudo verificar: {info.error}")
        if info.behind == 0:
            return UpdateResult(True, f"Estás al día ({info.current})")
        pull = _git(repo, ["pull", "--ff-only"], timeout=PULL_TIMEOUT)
        if pull.returncode == 0:
            return UpdateResult(True, f"Actualizado a {info.available}")
        reset = _git(repo, ["reset", "--hard", "origin/main"], timeout=15)
        if reset.returncode == 0:
            return UpdateResult(
                True, f"Actualizado a {info.available} (historial corregido)"
            )
        return UpdateResult(
            False, f"Falló el pull: {_short_error(pull.stderr, 'error')}"
        )


def is_auto_update_enabled() -> bool:
    """El chequeo automático al arrancar se desactiva con CALC_NO_AUTO_UPDATE=1."""
    return os.environ.get("CALC_NO_AUTO_UPDATE", "0").lower() not in (
        "1",
        "true",
        "yes",
    )
