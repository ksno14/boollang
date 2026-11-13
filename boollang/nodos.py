"""
Definición mínima de los nodos del Árbol de Sintaxis Abstracta (AST) para boollang.

Compartido entre el analizador sintáctico (parser), el evaluador semántico
y el módulo de traza.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass(frozen=True)
class Constante:
    """Hoja booleana literal (`true` o `false`)."""

    valor: bool


@dataclass(frozen=True)
class Negacion:
    """Operador unario lógico `not <FactB>`."""

    op: "ExprBool"


@dataclass(frozen=True)
class Conjuncion:
    """Operador binario lógico `<TermB> and <FactB>`."""

    izq: "ExprBool"
    der: "ExprBool"


@dataclass(frozen=True)
class Disyuncion:
    """Operador binario lógico `<ExpB> or <TermB>`."""

    izq: "ExprBool"
    der: "ExprBool"


ExprBool = Union[Constante, Negacion, Conjuncion, Disyuncion]


@dataclass
class Sentencia:
    """Representa una sentencia del programa fuente junto con su AST o error."""

    linea: int
    texto: str
    arbol: Optional[ExprBool] = None
    error: Optional[str] = None


@dataclass
class Programa:
    """Programa completo compuesto por una secuencia ordenada de sentencias."""

    sentencias: list[Sentencia] = field(default_factory=list)
