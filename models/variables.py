import math
from typing import Optional


class Variables:
    """Almacén de variables para la calculadora."""

    # Variables predefinidas (no se pueden sobreescribir)
    BUILTINS = {"pi": math.pi, "e": math.e}

    def __init__(self) -> None:
        self._store: dict[str, float] = {}

    def get(self, name: str) -> Optional[float]:
        """Obtener valor de variable (incluye builtins)."""
        if name in self.BUILTINS:
            return self.BUILTINS[name]
        return self._store.get(name)

    def set(self, name: str, value: float) -> None:
        """Asignar valor a variable (no permite sobreescribir builtins)."""
        if name in self.BUILTINS:
            raise ValueError(f"No se puede sobreescribir la variable builtin '{name}'")
        self._store[name] = value

    def delete(self, name: str) -> bool:
        """Eliminar variable. Retorna True si existía."""
        if name in self.BUILTINS:
            return False
        return self._store.pop(name, None) is not None

    def list_vars(self) -> dict[str, float]:
        """Retornar todas las variables (builtins + usuario)."""
        return {**self.BUILTINS, **self._store}

    def user_vars(self) -> dict[str, float]:
        """Variables de usuario (sin builtins), como copia."""
        return dict(self._store)

    def load_user_vars(self, data: dict[str, float]) -> None:
        """Reemplazar las variables de usuario (ignora builtins y valores inválidos)."""
        self._store = {
            name: float(value)
            for name, value in data.items()
            if isinstance(name, str)
            and name.isidentifier()
            and name not in self.BUILTINS
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        }

    def clear(self) -> None:
        """Eliminar todas las variables de usuario."""
        self._store.clear()
