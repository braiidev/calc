"""Lexer, parser y evaluator de expresiones matemáticas.

Fase 1 (v0.1): soporta números decimales y operaciones + - * / ( ).
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class TokType(Enum):
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    MULT = auto()
    DIV = auto()
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
    """Error matemático (división por cero, etc.)."""


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
    op: str
    child: Node


_TOKEN_MAP: dict[str, TokType] = {
    "+": TokType.PLUS,
    "-": TokType.MINUS,
    "*": TokType.MULT,
    "/": TokType.DIV,
    "(": TokType.LPAREN,
    ")": TokType.RPAREN,
}


# ---------------- Lexer ----------------

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
        ttype = _TOKEN_MAP.get(ch)
        if ttype is None:
            raise CalcSyntaxError(f"Carácter no reconocido: '{ch}'")
        tokens.append(Token(ttype, lexeme=ch))
        i += 1
    tokens.append(Token(TokType.EOF, lexeme=""))
    return tokens


# ---------------- Parser ----------------

class Parser:
    """Parser por descenso recursivo con gramática de precedencia:

    expr   := term (('+' | '-') term)*
    term   := factor (('*' | '/') factor)*
    factor := '-' factor | NUMBER | '(' expr ')'
    """

    _BIN_OPS: dict[TokType, str] = {
        TokType.PLUS: "+",
        TokType.MINUS: "-",
        TokType.MULT: "*",
        TokType.DIV: "/",
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
            expected = _LABELS.get(ttype, ttype.name)
            raise CalcSyntaxError(f"Se esperaba '{expected}'")
        return token

    # ------- reglas -------

    def _parse_expr(self) -> Node:
        node = self._parse_term()
        while (op := self._current().type) in (TokType.PLUS, TokType.MINUS):
            self._advance()
            right = self._parse_term()
            node = BinOpNode(node, self._BIN_OPS[op], right)
        return node

    def _parse_term(self) -> Node:
        node = self._parse_factor()
        while (op := self._current().type) in (TokType.MULT, TokType.DIV):
            self._advance()
            right = self._parse_factor()
            node = BinOpNode(node, self._BIN_OPS[op], right)
        return node

    def _parse_factor(self) -> Node:
        token = self._current()
        if token.type == TokType.NUMBER:
            self._advance()
            return NumberNode(token.value)
        if token.type == TokType.MINUS:
            self._advance()
            return UnaryOpNode("-", self._parse_factor())
        if token.type == TokType.LPAREN:
            self._advance()
            node = self._parse_expr()
            self._expect(TokType.RPAREN)
            return node
        if token.type == TokType.EOF:
            raise CalcSyntaxError("Expresión incompleta")
        raise CalcSyntaxError(f"Token inesperado: '{token.lexeme}'")


_LABELS: dict[TokType, str] = {
    TokType.RPAREN: ")",
    TokType.EOF: "fin de expresión",
}


# ---------------- Evaluator ----------------

def evaluate_ast(node: Node) -> float:
    """Evaluar el árbol sintáctico abstracto."""
    if isinstance(node, NumberNode):
        return node.value
    if isinstance(node, UnaryOpNode):
        value = evaluate_ast(node.child)
        if node.op == "-":
            return -value
        raise CalcMathError(f"Operador unario desconocido: '{node.op}'")
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
    raise CalcSyntaxError(f"Operador no soportado: '{op}'")


# ---------------- API pública ----------------

class Calculator:
    """Calculadora con parser propio.

    Uso:
        calc = Calculator()
        result = calc.evaluate("2 + 3 * 4")  # 14.0
    """

    def __init__(self) -> None:
        pass

    def evaluate(self, expr: str) -> float:
        tokens = tokenize(expr)
        parser = Parser(tokens)
        ast = parser.parse()
        return evaluate_ast(ast)