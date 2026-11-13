"""
Definición de los nodos del Árbol de Sintaxis Abstracta (AST) para boollang.

Módulo diseñado y estructurado por el Integrante 6 (Estructura del árbol AST).
Compartido entre el analizador sintáctico (parser), el evaluador semántico
y el módulo de traza.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple, Union


@dataclass(frozen=True)
class Constante:
    """Hoja booleana literal (`true` o `false`)."""

    valor: bool

    @property
    def nombre_op(self) -> str:
        """Nombre del operador o tipo de nodo."""
        return "const"

    @property
    def prioridad(self) -> int:
        """Nivel de precedencia sintáctica (más alto = mayor precedencia)."""
        return 4

    def hijos(self) -> Tuple["ExprBool", ...]:
        """Retorna los nodos hijos inmediatos."""
        return ()

    def a_texto(self, con_parentesis: bool = False) -> str:
        """Representación textual de la constante en sintaxis boollang."""
        return "true" if self.valor else "false"

    def __str__(self) -> str:
        return self.a_texto()


@dataclass(frozen=True)
class Negacion:
    """Operador unario lógico `not <FactB>`."""

    op: "ExprBool"

    @property
    def nombre_op(self) -> str:
        """Nombre del operador o tipo de nodo."""
        return "not"

    @property
    def prioridad(self) -> int:
        """Nivel de precedencia sintáctica (más alto = mayor precedencia)."""
        return 3

    def hijos(self) -> Tuple["ExprBool", ...]:
        """Retorna los nodos hijos inmediatos."""
        return (self.op,)

    def a_texto(self, con_parentesis: bool = False) -> str:
        """Representación textual de la negación, añadiendo paréntesis si su hijo es binario."""
        if isinstance(self.op, (Conjuncion, Disyuncion)):
            texto = f"not ({self.op.a_texto()})"
        else:
            texto = f"not {self.op.a_texto()}"
        return f"({texto})" if con_parentesis else texto

    def __str__(self) -> str:
        return self.a_texto()


@dataclass(frozen=True)
class Conjuncion:
    """Operador binario lógico `<TermB> and <FactB>`."""

    izq: "ExprBool"
    der: "ExprBool"

    @property
    def nombre_op(self) -> str:
        """Nombre del operador o tipo de nodo."""
        return "and"

    @property
    def prioridad(self) -> int:
        """Nivel de precedencia sintáctica (más alto = mayor precedencia)."""
        return 2

    def hijos(self) -> Tuple["ExprBool", ...]:
        """Retorna los nodos hijos inmediatos."""
        return (self.izq, self.der)

    def a_texto(self, con_parentesis: bool = False) -> str:
        """Representación textual de la conjunción según precedencia y asociatividad a izquierda."""
        izq_txt = (
            f"({self.izq.a_texto()})"
            if isinstance(self.izq, Disyuncion)
            else self.izq.a_texto()
        )
        der_txt = (
            f"({self.der.a_texto()})"
            if isinstance(self.der, (Disyuncion, Conjuncion))
            else self.der.a_texto()
        )
        texto = f"{izq_txt} and {der_txt}"
        return f"({texto})" if con_parentesis else texto

    def __str__(self) -> str:
        return self.a_texto()


@dataclass(frozen=True)
class Disyuncion:
    """Operador binario lógico `<ExpB> or <TermB>`."""

    izq: "ExprBool"
    der: "ExprBool"

    @property
    def nombre_op(self) -> str:
        """Nombre del operador o tipo de nodo."""
        return "or"

    @property
    def prioridad(self) -> int:
        """Nivel de precedencia sintáctica (más alto = mayor precedencia)."""
        return 1

    def hijos(self) -> Tuple["ExprBool", ...]:
        """Retorna los nodos hijos inmediatos."""
        return (self.izq, self.der)

    def a_texto(self, con_parentesis: bool = False) -> str:
        """Representación textual de la disyunción según precedencia y asociatividad a izquierda."""
        izq_txt = self.izq.a_texto()
        der_txt = (
            f"({self.der.a_texto()})"
            if isinstance(self.der, Disyuncion)
            else self.der.a_texto()
        )
        texto = f"{izq_txt} or {der_txt}"
        return f"({texto})" if con_parentesis else texto

    def __str__(self) -> str:
        return self.a_texto()


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
