"""Lexer, parser y evaluator de expresiones matemáticas.

Operadores soportados:
- Aritmética básica: + - * / ( )
- División entera: `//` (9 // 4 = 2)
- Científica: ** (potencia), % (módulo), ! (factorial)
- Funciones: sqrt(x) (raíz cuadrada), root(x, n) (raíz n-ésima: root(8, 3) = 2)
- Variables (v0.4): pi, e (builtin) y asignación `x = 5` para uso posterior
"""

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from models.functions import Functions, FunctionDef
from models.variables import Variables


class TokType(Enum):
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    MULT = auto()
    DIV = auto()
    FLOORDIV = auto()
    MOD = auto()
    POW = auto()
    FACT = auto()
    ASSIGN = auto()
    IDENT = auto()
    COMMA = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokType
    value: Optional[float] = None
    lexeme: str = ""


class CalcSyntaxError(ValueError):
    """Error de sintaxis en la expresión."""


class CalcMathError(ValueError):
    """Error matemático (división por cero, factorial inválido, etc.)."""


# ---------------- AST ----------------


class Node:
    """Nodo base del árbol sintáctico."""


@dataclass
class NumberNode(Node):
    value: float


@dataclass
class VarNode(Node):
    name: str


@dataclass
class BinOpNode(Node):
    left: Node
    op: str
    right: Node


@dataclass
class UnaryOpNode(Node):
    op: str  # '-', '!', 'sqrt'
    child: Node


@dataclass
class AssignNode(Node):
    name: str
    value: Node


@dataclass
class DefNode(Node):
    """Definición de función de usuario: `f(a, b) = expr`."""

    name: str
    params: list[str]
    body: Node


@dataclass
class CallNode(Node):
    name: str
    args: list[Node]


# ---------------- Lexer ----------------

_SINGLE_CHAR: dict[str, TokType] = {
    "+": TokType.PLUS,
    "-": TokType.MINUS,
    "*": TokType.MULT,
    "/": TokType.DIV,
    "%": TokType.MOD,
    "!": TokType.FACT,
    "=": TokType.ASSIGN,
    ",": TokType.COMMA,
    "(": TokType.LPAREN,
    ")": TokType.RPAREN,
}


def tokenize(expr: str) -> list[Token]:
    """Convertir una expresión en una lista de tokens."""
    tokens: list[Token] = []
    i = 0
    n = len(expr)
    while i < n:
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isdigit() or ch == ".":
            j = i
            while j < n and (expr[j].isdigit() or expr[j] == "."):
                j += 1
            lexeme = expr[i:j]
            try:
                value = float(lexeme)
            except ValueError:
                raise CalcSyntaxError(f"Número mal formado: '{lexeme}'")
            tokens.append(Token(TokType.NUMBER, value=value, lexeme=lexeme))
            i = j
            continue
        if ch == "*" and i + 1 < n and expr[i + 1] == "*":
            tokens.append(Token(TokType.POW, lexeme="**"))
            i += 2
            continue
        if ch == "/" and i + 1 < n and expr[i + 1] == "/":
            tokens.append(Token(TokType.FLOORDIV, lexeme="//"))
            i += 2
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (expr[j].isalnum() or expr[j] == "_"):
                j += 1
            name = expr[i:j]
            tokens.append(Token(TokType.IDENT, lexeme=name))
            i = j
            continue
        ttype = _SINGLE_CHAR.get(ch)
        if ttype is None:
            raise CalcSyntaxError(f"Carácter no reconocido: '{ch}'")
        tokens.append(Token(ttype, lexeme=ch))
        i += 1
    tokens.append(Token(TokType.EOF, lexeme=""))
    return tokens


# ---------------- Parser ----------------

# Funciones con notación de llamada (nombre -> aridad): sqrt(x), root(x, n)
_FUNCTIONS = {"sqrt": 1, "root": 2}


class Parser:
    """Parser por descenso recursivo. Precedencia (de menor a mayor):

    assign  := IDENT '=' assign | expr
    expr    := term (('+' | '-') term)*
    term    := unary (('*' | '/' | '//' | '%') unary)*
    unary   := '-' unary | power
    power   := postfix ('**' unary)?            # asociativa a la derecha
    postfix := primary ('!')*
    primary := NUMBER | IDENT | '(' expr ')'
             | IDENT '(' expr (',' expr)* ')'
    """

    _TERM_OPS = {
        TokType.MULT: "*",
        TokType.DIV: "/",
        TokType.FLOORDIV: "//",
        TokType.MOD: "%",
    }

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def parse(self) -> Node:
        if self._current().type == TokType.EOF:
            raise CalcSyntaxError("Expresión vacía")
        node = self._parse_assign()
        if self._current().type != TokType.EOF:
            raise CalcSyntaxError(f"Token inesperado: '{self._current().lexeme}'")
        return node

    # ------- helpers -------

    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._current()
        self._pos += 1
        return token

    def _match(self, ttype: TokType) -> Optional[Token]:
        if self._current().type == ttype:
            return self._advance()
        return None

    def _expect(self, ttype: TokType) -> Token:
        token = self._match(ttype)
        if token is None:
            raise CalcSyntaxError(f"Se esperaba '{_LABELS.get(ttype, ttype.name)}'")
        return token

    def _peek(self, offset: int = 1) -> Optional[TokType]:
        """Tipo del token en `offset` posiciones desde el actual."""
        pos = self._pos + offset
        if pos >= len(self._tokens):
            return None
        return self._tokens[pos].type

    # ------- reglas -------

    def _parse_assign(self) -> Node:
        if self._current().type == TokType.IDENT and self._peek() == TokType.ASSIGN:
            name = self._advance().lexeme
            self._expect(TokType.ASSIGN)
            return AssignNode(name, self._parse_assign())
        # función: `f(a, b) = expr` (solo como definición; si no hay '=', es una llamada)
        if self._current().type == TokType.IDENT and self._peek() == TokType.LPAREN:
            defined = self._try_parse_def()
            if defined is not None:
                return defined
        return self._parse_expr()

    def _try_parse_def(self) -> Optional[Node]:
        """Intentar `IDENT '(' IDENT (',' IDENT)* ')' '=' expr`; si no cuadra, rewind."""
        start = self._pos
        name = self._advance().lexeme
        self._expect(TokType.LPAREN)
        params: list[str] = []
        if self._current().type == TokType.IDENT:
            params.append(self._advance().lexeme)
            while self._match(TokType.COMMA):
                if self._current().type != TokType.IDENT:
                    self._pos = start
                    return None
                params.append(self._advance().lexeme)
        if not self._match(TokType.RPAREN):
            self._pos = start
            return None
        if not self._match(TokType.ASSIGN):
            self._pos = start
            return None
        body = self._parse_assign()
        return DefNode(name, params, body)

    def _parse_expr(self) -> Node:
        node = self._parse_term()
        while (op := self._current().type) in (TokType.PLUS, TokType.MINUS):
            self._advance()
            right = self._parse_term()
            node = BinOpNode(node, "+" if op == TokType.PLUS else "-", right)
        return node

    def _parse_term(self) -> Node:
        node = self._parse_unary()
        while (op := self._current().type) in self._TERM_OPS:
            self._advance()
            right = self._parse_unary()
            node = BinOpNode(node, self._TERM_OPS[op], right)
        return node

    def _parse_unary(self) -> Node:
        if self._match(TokType.MINUS):
            return UnaryOpNode("-", self._parse_unary())
        return self._parse_power()

    def _parse_power(self) -> Node:
        node = self._parse_postfix()
        if self._match(TokType.POW):
            # right = unary -> asociativa derecha y admite exponente negativo
            right = self._parse_unary()
            node = BinOpNode(node, "**", right)
        return node

    def _parse_postfix(self) -> Node:
        node = self._parse_primary()
        while self._match(TokType.FACT):
            node = UnaryOpNode("!", node)
        return node

    def _parse_primary(self) -> Node:
        token = self._current()
        if token.type == TokType.NUMBER:
            self._advance()
            if token.value is None:
                raise CalcSyntaxError(f"Número mal formado: '{token.lexeme}'")
            return NumberNode(token.value)
        if token.type == TokType.IDENT:
            self._advance()
            if self._match(TokType.LPAREN):
                args = [self._parse_expr()]
                while self._match(TokType.COMMA):
                    args.append(self._parse_expr())
                self._expect(TokType.RPAREN)
                if token.lexeme in _FUNCTIONS:
                    arity = _FUNCTIONS[token.lexeme]
                    if len(args) != arity:
                        raise CalcSyntaxError(
                            f"'{token.lexeme}' espera {arity} argumento(s), recibió {len(args)}"
                        )
                return CallNode(token.lexeme, args)
            return VarNode(token.lexeme)
        if token.type == TokType.LPAREN:
            self._advance()
            node = self._parse_expr()
            self._expect(TokType.RPAREN)
            return node
        if token.type == TokType.EOF:
            raise CalcSyntaxError("Expresión incompleta")
        raise CalcSyntaxError(f"Token inesperado: '{token.lexeme}'")


_LABELS: dict[TokType, str] = {
    TokType.NUMBER: "número",
    TokType.PLUS: "+",
    TokType.MINUS: "-",
    TokType.MULT: "*",
    TokType.DIV: "/",
    TokType.FLOORDIV: "//",
    TokType.MOD: "%",
    TokType.POW: "**",
    TokType.FACT: "!",
    TokType.ASSIGN: "=",
    TokType.IDENT: "identificador",
    TokType.COMMA: ",",
    TokType.LPAREN: "(",
    TokType.RPAREN: ")",
}


# ---------------- Evaluator ----------------

_FACTORIAL_MAX = 1000
_MAX_CALL_DEPTH = 100


class _Scope(Variables):
    """Variables con un frame local encima (params de una función llamada).

    Los parámetros tapan a las variables globales/builtin; las asignaciones
    dentro del cuerpo afectan al scope global.
    """

    def __init__(self, bindings: dict[str, float], parent: Variables) -> None:
        super().__init__()
        self._bindings = dict(bindings)
        self._parent = parent

    def get(self, name: str) -> Optional[float]:
        if name in self._bindings:
            return self._bindings[name]
        return self._parent.get(name)

    def set(self, name: str, value: float) -> None:
        self._parent.set(name, value)

    def delete(self, name: str) -> bool:
        if name in self._bindings:
            del self._bindings[name]
            return True
        return self._parent.delete(name)

    def list_vars(self) -> dict[str, float]:
        return {**self._parent.list_vars(), **self._bindings}

    def user_vars(self) -> dict[str, float]:
        return self._parent.user_vars()


def evaluate_ast(
    node: Node,
    variables: Optional[Variables] = None,
    functions: Optional[Functions] = None,
    depth: int = 0,
) -> float:
    """Evaluar el árbol sintáctico abstracto.

    `variables` se actualiza con las asignaciones (`x = 5`) encontradas;
    `functions` es el store de funciones de usuario para las llamadas.
    """
    if variables is None:
        variables = Variables()
    if functions is None:
        functions = Functions()
    if isinstance(node, NumberNode):
        return node.value
    if isinstance(node, VarNode):
        return _lookup_var(variables, node.name)
    if isinstance(node, AssignNode):
        value = evaluate_ast(node.value, variables, functions, depth)
        _set_var(variables, node.name, value)
        return value
    if isinstance(node, DefNode):
        raise CalcSyntaxError(
            f"Definición de '{node.name}' fuera de lugar: solo como expresión completa"
        )
    if isinstance(node, UnaryOpNode):
        value = evaluate_ast(node.child, variables, functions, depth)
        if node.op == "-":
            return -value
        if node.op == "!":
            return _factorial(value)
        raise CalcMathError(f"Operador desconocido: '{node.op}'")
    if isinstance(node, CallNode):
        args = [evaluate_ast(arg, variables, functions, depth) for arg in node.args]
        return _call_function(node.name, args, variables, functions, depth)
    if isinstance(node, BinOpNode):
        left = evaluate_ast(node.left, variables, functions, depth)
        right = evaluate_ast(node.right, variables, functions, depth)
        return _apply_binop(node.op, left, right)
    raise CalcSyntaxError("Nodo desconocido en el árbol de expresión")


def _call_function(
    name: str,
    args: list[float],
    variables: Variables,
    functions: Optional[Functions] = None,
    depth: int = 0,
) -> float:
    if name == "sqrt":
        return _sqrt(args[0])
    if name == "root":
        return _root(args[0], args[1])
    if functions is not None:
        defined = functions.get(name)
        if defined is not None:
            return _call_user_function(defined, args, variables, functions, depth)
    raise CalcMathError(f"Función desconocida: '{name}'")


def _call_user_function(
    fn: FunctionDef,
    args: list[float],
    variables: Variables,
    functions: Functions,
    depth: int,
) -> float:
    if len(args) != len(fn.params):
        raise CalcMathError(
            f"'{fn.name}' espera {len(fn.params)} argumento(s), recibió {len(args)}"
        )
    if depth >= _MAX_CALL_DEPTH:
        raise CalcMathError("Recursión demasiado profunda")
    scope = _Scope(dict(zip(fn.params, args)), variables)
    return evaluate_ast(fn.body, scope, functions, depth + 1)


def _lookup_var(variables: Variables, name: str) -> float:
    value = variables.get(name)
    if value is None:
        raise CalcSyntaxError(f"Variable indefinida: '{name}'")
    return value


def _set_var(variables: Variables, name: str, value: float) -> None:
    try:
        variables.set(name, value)
    except ValueError as exc:
        raise CalcMathError(str(exc))


def _apply_binop(op: str, left: float, right: float) -> float:
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        if right == 0:
            raise CalcMathError("División por cero")
        return left / right
    if op == "//":
        if right == 0:
            raise CalcMathError("División por cero")
        return float(math.floor(left / right))
    if op == "%":
        if right == 0:
            raise CalcMathError("División por cero")
        return left % right
    if op == "**":
        try:
            return left**right
        except (OverflowError, ValueError):
            raise CalcMathError("Resultado fuera de rango")
    raise CalcSyntaxError(f"Operador no soportado: '{op}'")


def _root(base: float, index: float) -> float:
    """Raíz n-ésima: `root(8, 3) == 8 ** (1/3) == 2`."""
    if index == 0:
        raise CalcMathError("Índice de raíz cero")
    negative = base < 0
    if base < 0:
        if index != int(index):
            raise CalcMathError("Raíz de número negativo con índice fraccionario")
        if int(index) % 2 == 0:
            raise CalcMathError("Raíz de índice par sobre número negativo")
        base = -base
    try:
        result = base ** (1.0 / index)
    except (OverflowError, ValueError):
        raise CalcMathError("Resultado fuera de rango")
    return -result if negative else result


def _factorial(value: float) -> float:
    if value != int(value):
        raise CalcMathError("El factorial requiere un entero")
    n = int(value)
    if n < 0:
        raise CalcMathError("Factorial de número negativo")
    if n > _FACTORIAL_MAX:
        raise CalcMathError(f"Factorial demasiado grande (máx {_FACTORIAL_MAX})")
    return float(math.factorial(n))


def _sqrt(value: float) -> float:
    if value < 0:
        raise CalcMathError("Raíz de número negativo")
    return math.sqrt(value)


# ---------------- Notación semántica ----------------

# Etiquetas de las operaciones "complejas" (las de símbolo no evidente).
_TAG_FLOOR = "floor"
_TAG_SQRT = "sqrt"
_TAG_CBRT = "cbrt"
_TAG_NROOT = "nroot"


def _add_tag(tags: list[str], tag: str) -> None:
    if tag not in tags:
        tags.append(tag)


def _call_tag(node: CallNode) -> Optional[str]:
    """Etiqueta semántica de una función, o None si no es 'compleja'."""
    if node.name == "sqrt":
        return _TAG_SQRT
    if node.name == "root":
        index = node.args[1]
        if isinstance(index, NumberNode) and index.value == int(index.value):
            n = int(index.value)
            if n == 2:
                return _TAG_SQRT
            if n == 3:
                return _TAG_CBRT
        return _TAG_NROOT
    return None


def _collect_tags(node: Node, tags: list[str]) -> None:
    """Recorrer el AST agregando, sin repetir, las etiquetas de operaciones complejas."""
    if isinstance(node, AssignNode):
        _collect_tags(node.value, tags)
    elif isinstance(node, UnaryOpNode):
        _collect_tags(node.child, tags)
    elif isinstance(node, CallNode):
        for arg in node.args:
            _collect_tags(arg, tags)
        tag = _call_tag(node)
        if tag is not None:
            _add_tag(tags, tag)
    elif isinstance(node, BinOpNode):
        _collect_tags(node.left, tags)
        _collect_tags(node.right, tags)
        if node.op == "//":
            _add_tag(tags, _TAG_FLOOR)


# ---------------- API pública ----------------


class Calculator:
    """Calculadora con parser propio y almacén de variables.

    Uso:
        calc = Calculator()
        result = calc.evaluate("2 + 3 * 4")    # 14.0
        result = calc.evaluate("2 ** 3 !")     # 64.0
        result = calc.evaluate("root(8, 3)")   # 2.0  (raíz cúbica)
        result = calc.evaluate("9 // 4")       # 2.0  (división entera)
        result = calc.evaluate("x = 5")        # 5.0  (asigna y devuelve)
        result = calc.evaluate("x * 2")        # 10.0 (usa la variable)
    """

    def __init__(self) -> None:
        self.variables = Variables()
        self.functions = Functions()

    def evaluate(self, expr: str) -> float:
        tokens = tokenize(expr)
        parser = Parser(tokens)
        ast = parser.parse()
        return evaluate_ast(ast, self.variables, self.functions)

    def is_definition(self, expr: str) -> bool:
        """True si la expresión es una definición de función `f(a, b) = ...`."""
        try:
            ast = Parser(tokenize(expr)).parse()
        except CalcSyntaxError:
            return False
        return isinstance(ast, DefNode)

    def define(self, expr: str) -> Optional[str]:
        """Registrar una función de usuario y devolver su nombre; None si no es definición."""
        ast = Parser(tokenize(expr)).parse()
        if not isinstance(ast, DefNode):
            return None
        source = expr.split("=", 1)[1].strip()
        try:
            self.functions.define(ast.name, ast.params, ast.body, source)
        except ValueError as exc:
            raise CalcSyntaxError(str(exc))
        return ast.name

    def notation(self, expr: str) -> str:
        """Etiquetas semánticas de las operaciones complejas, en orden de aparición.

        Devuelve, p. ej., `[floor] [cbrt]`; o "" si no hay operaciones complejas
        o la expresión no parsea.
        """
        try:
            ast = Parser(tokenize(expr)).parse()
        except CalcSyntaxError:
            return ""
        tags: list[str] = []
        _collect_tags(ast, tags)
        return " ".join(f"[{tag}]" for tag in tags)
