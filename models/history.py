"""Historial session de operaciones evaluadas."""

from collections import deque
from typing import Optional


class History:
    """Almacena las últimas operaciones evaluadas (expr, resultado).

    El resultado se guarda como texto ya formateado, tal como se mostró.
    """

    def __init__(self, max_size: int = 20) -> None:
        self._entries: deque[tuple[str, str]] = deque(maxlen=max_size)

    def add(self, expr: str, result: str) -> None:
        """Agregar una operación (colas de la más reciente al final)."""
        self._entries.append((expr, result))

    def clear(self) -> None:
        """Vaciar el historial."""
        self._entries.clear()

    def length(self) -> int:
        return len(self._entries)

    def last(self, n: int = 10) -> list[tuple[str, str]]:
        """Retornar las últimas n entradas, la más reciente al final."""
        return list(self._entries)[-n:]

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int) -> Optional[tuple[str, str]]:
        if index < 0 or index >= len(self._entries):
            return None
        return self._entries[index]