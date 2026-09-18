"""Store de funciones definidas por el usuario: `f(a, b) = expr`."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from calculator import Node

# Nombres que no se pueden usar como función ni como parámetro.
RESERVED_NAMES = ("pi", "e", "sqrt", "root")


@dataclass
class FunctionDef:
    """Definición de una función de usuario."""

    name: str
    params: list[str]
    body: "Node"  # AST del cuerpo, ya parseado
    source: str  # cuerpo en texto (para mostrar y persistir)

    def signature(self) -> str:
        return f"{self.name}({', '.join(self.params)})"


class Functions:
    """Almacén de funciones de usuario (una por nombre, redefinible).

    Los cuerpos se guardan como AST parseado para la evaluación y la fuente
    original para la persistencia/display.
    """

    RESERVED = RESERVED_NAMES

    def __init__(self) -> None:
        self._store: dict[str, FunctionDef] = {}

    def get(self, name: str) -> Optional[FunctionDef]:
        return self._store.get(name)

    def define(
        self, name: str, params: list[str], body: "Node", source: str
    ) -> FunctionDef:
        """Registrar o redefinir una función. Valida nombre y parámetros."""
        if name in self.RESERVED:
            raise ValueError(f"No se puede redefinir '{name}'")
        seen: set[str] = set()
        for param in params:
            if param in self.RESERVED:
                raise ValueError(f"El parámetro '{param}' está reservado")
            if param in seen:
                raise ValueError(f"Parámetro duplicado: '{param}'")
            seen.add(param)
        defined = FunctionDef(name, list(params), body, source)
        self._store[name] = defined
        return defined

    def delete(self, name: str) -> bool:
        return self._store.pop(name, None) is not None

    def list_functions(self) -> list[FunctionDef]:
        return list(self._store.values())

    def user_functions(self) -> list[dict]:
        """Forma serializable (JSON) de las funciones, en orden de definición."""
        return [
            {"name": f.name, "params": f.params, "body": f.source}
            for f in self._store.values()
        ]

    def load_user_functions(self, data: list[dict]) -> None:
        """Reemplazar las funciones. Re-parsea los cuerpos; lo inválido se ignora."""
        from calculator import CalcSyntaxError, DefNode, Parser, tokenize

        loaded: dict[str, FunctionDef] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            params = item.get("params")
            source = item.get("body")
            if not isinstance(name, str) or not name.isidentifier():
                continue
            if not isinstance(params, list) or not all(
                isinstance(p, str) and p.isidentifier() for p in params
            ):
                continue
            if not isinstance(source, str):
                continue
            try:
                ast = Parser(
                    tokenize(f"{name}({', '.join(params)}) = {source}")
                ).parse()
                if not isinstance(ast, DefNode):
                    continue
                loaded[name] = self.define(ast.name, ast.params, ast.body, source)
            except (CalcSyntaxError, ValueError):
                continue
        self._store = loaded

    def clear(self) -> None:
        self._store.clear()
