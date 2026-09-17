"""Historial session de operaciones evaluadas."""

from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HistoryEntry:
    """Una operación evaluada: expresión cruda, resultado y notación semántica."""

    expr: str
    result: str
    notation: str = ""


class History:
    """Almacena las últimas operaciones evaluadas.

    El resultado se guarda como texto ya formateado, tal como se mostró, y la
    notación como etiquetas semánticas de las operaciones complejas (p. ej.
    `[floor]`).
    """

    def __init__(self, max_size: int = 20) -> None:
        self._max_size = max_size
        self._entries: deque[HistoryEntry] = deque(maxlen=max_size)

    def add(self, expr: str, result: str, notation: str = "") -> None:
        """Agregar una operación (cola de la más reciente al final)."""
        self._entries.append(HistoryEntry(expr, result, notation))

    def entries(self) -> list[HistoryEntry]:
        """Todas las entradas, de la más antigua a la más reciente."""
        return list(self._entries)

    def load_entries(self, entries: list[HistoryEntry]) -> None:
        """Reemplazar el contenido por `entries` (recorta al tamaño máximo)."""
        self._entries = deque(entries[-self._max_size :], maxlen=self._max_size)

    def delete_at(self, index: int) -> bool:
        """Eliminar la entrada en `index`. Retorna True si existía."""
        if index < 0 or index >= len(self._entries):
            return False
        items = list(self._entries)
        del items[index]
        self._entries = deque(items, maxlen=self._max_size)
        return True

    def clear(self) -> None:
        """Vaciar el historial."""
        self._entries.clear()

    def length(self) -> int:
        return len(self._entries)

    def last(self, n: int = 10) -> list[HistoryEntry]:
        """Retornar las últimas n entradas, la más reciente al final."""
        return list(self._entries)[-n:]

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int) -> Optional[HistoryEntry]:
        if index < 0 or index >= len(self._entries):
            return None
        return self._entries[index]
