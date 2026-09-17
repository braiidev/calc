"""Lexer, parser y evaluator de expresiones matemáticas.

Operadores soportados:
- Aritmética básica: + - * / ( )
- División entera: `:` (5:2 = 2)
- Científica: ** (potencia), // (raíz n-ésima: 8//3 = 2), % (módulo),
  ! (factorial), sqrt() (raíz cuadrada)
"""

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class TokType(Enum):
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    MULT = auto()
    DIV = auto()
    FLDIV = auto()
    ROOT = auto()
    MOD = auto()
    POW = auto()
    FACT = auto()
    IDENT = auto()
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
class BinOpNode(Node):
    left: Node
    op: str
    right: Node


@dataclass
class UnaryOpNode(Node):
    op: str  # '-', '!', 'sqrt'
    child: Node


# ---------------- Lexer ----------------

_SINGLE_CHAR: dict[str, TokType] = {
    "+": TokType.PLUS,
    "-": TokType.MINUS,
    "*": TokType.MULT,
    "/": TokType.DIV,
    ":": TokType.FLDIV,
    "%": TokType.MOD,
    "!": TokType.FACT,
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
            tokens.append(Token(TokType.ROOT, lexeme="//"))
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

# Funciones con notación de llamada: sqrt(x)
_FUNCTIONS = {"sqrt"}


class Parser:
    """Parser por descenso recursivo. Precedencia (de menor a mayor):

    expr    := term (('+' | '-') term)*
    term    := unary (('*' | '/' | ':' | '//' | '%') unary)*
    unary   := '-' unary | power
    power   := postfix ('**' unary)?            # asociativa a la derecha
    postfix := primary ('!')*
    primary := NUMBER | '(' expr ')' | IDENT '(' expr ')'
    """

    _TERM_OPS = {
        TokType.MULT: "*",
        TokType.DIV: "/",
        TokType.FLDIV: ":",
        TokType.ROOT: "//",
        TokType.MOD: "%",
    }

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def parse(self) -> Node:
        if self._current().type == TokType.EOF:
            raise CalcSyntaxError("Expresión vacía")
        node = self._parse_expr()
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

    # ------- reglas -------

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
            if token.lexeme not in _FUNCTIONS:
                raise CalcSyntaxError(f"Función desconocida: '{token.lexeme}'")
            self._expect(TokType.LPAREN)
            arg = self._parse_expr()
            self._expect(TokType.RPAREN)
            return UnaryOpNode(token.lexeme, arg)
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
    TokType.FLDIV: ":",
    TokType.ROOT: "//",
    TokType.MOD: "%",
    TokType.POW: "**",
    TokType.FACT: "!",
    TokType.IDENT: "identificador",
    TokType.LPAREN: "(",
    TokType.RPAREN: ")",
}


# ---------------- Evaluator ----------------

_FACTORIAL_MAX = 1000


def evaluate_ast(node: Node) -> float:
    """Evaluar el árbol sintáctico abstracto."""
    if isinstance(node, NumberNode):
        return node.value
    if isinstance(node, UnaryOpNode):
        value = evaluate_ast(node.child)
        if node.op == "-":
            return -value
        if node.op == "!":
            return _factorial(value)
        if node.op == "sqrt":
            return _sqrt(value)
        raise CalcMathError(f"Operador desconocido: '{node.op}'")
    if isinstance(node, BinOpNode):
        left = evaluate_ast(node.left)
        right = evaluate_ast(node.right)
        return _apply_binop(node.op, left, right)
    raise CalcSyntaxError("Nodo desconocido en el árbol de expresión")


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
    if op == ":":
        if right == 0:
            raise CalcMathError("División por cero")
        if left != int(left) or right != int(right):
            raise CalcMathError("La división entera requiere enteros")
        return float(int(left) // int(right))
    if op == "//":
        return _root(left, right)
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
    """Raíz n-ésima: base // index == base ** (1/index). `8//3 = 2`."""
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


# ---------------- API pública ----------------


class Calculator:
    """Calculadora con parser propio.

    Uso:
        calc = Calculator()
        result = calc.evaluate("2 + 3 * 4")    # 14.0
        result = calc.evaluate("2 ** 3 !")     # 64.0
        result = calc.evaluate("8//3")         # 2.0  (raíz cúbica)
        result = calc.evaluate("5:2")          # 2.0  (división entera)
    """

    def __init__(self) -> None:
        pass

    def evaluate(self, expr: str) -> float:
        tokens = tokenize(expr)
        parser = Parser(tokens)
        ast = parser.parse()
        return evaluate_ast(ast)
