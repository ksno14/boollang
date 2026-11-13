"""
Evaluador semántico para expresiones y programas de boollang.

Incluye integración con la traza de evaluación y el formateo de AST (Integrante 6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

from .nodos import (
    Conjuncion,
    Constante,
    Disyuncion,
    ExprBool,
    Negacion,
    Programa,
    Sentencia,
)


def formatear_booleano(valor: bool) -> str:
    """Serializa un booleano de Python usando la sintaxis oficial de boollang."""
    if not isinstance(valor, bool):
        raise TypeError(f"Se esperaba un valor bool, se recibió {type(valor).__name__}")
    return "true" if valor else "false"


def evaluar(nodo: ExprBool) -> bool:
    """Evalúa recursivamente un nodo AST booleano y retorna `bool`."""
    if isinstance(nodo, Constante):
        if not isinstance(nodo.valor, bool):
            raise TypeError(
                f"Constante.valor debe ser bool, se recibió {type(nodo.valor).__name__}"
            )
        return nodo.valor

    if isinstance(nodo, Negacion):
        return not evaluar(nodo.op)

    if isinstance(nodo, Conjuncion):
        izq = evaluar(nodo.izq)
        der = evaluar(nodo.der)
        return izq and der

    if isinstance(nodo, Disyuncion):
        izq = evaluar(nodo.izq)
        der = evaluar(nodo.der)
        return izq or der

    raise TypeError(f"Nodo AST no soportado: {type(nodo).__name__}")


@dataclass(frozen=True)
class ResultadoSentencia:
    """Resultado de evaluar una sentencia individual (valor booleano o error)."""

    linea: int
    texto: str
    valor: Optional[bool] = None
    error: Optional[str] = None

    @property
    def es_error(self) -> bool:
        """Indica si la sentencia culminó con un error léxico o sintáctico."""
        return self.error is not None

    def formatear_linea(self) -> str:
        """Retorna la representación oficial de la línea para el archivo `.out`."""
        if self.error is not None:
            return f"[L{self.linea}] {self.texto} => {self.error}"
        if self.valor is None:
            return f"[L{self.linea}] {self.texto} => ERROR interno: resultado booleano ausente"
        return f"[L{self.linea}] {self.texto} => {formatear_booleano(self.valor)}"


@dataclass(frozen=True)
class ResumenEvaluacion:
    """Resumen consolidado de todas las sentencias procesadas de un programa."""

    procesadas: int
    evaluadas: int
    con_error: int
    resultados: list[ResultadoSentencia]


def evaluar_sentencia(sentencia: Sentencia) -> ResultadoSentencia:
    """Evalúa una `Sentencia`, respetando errores previos de análisis."""
    if not isinstance(sentencia, Sentencia):
        raise TypeError(f"Se esperaba Sentencia, se recibió {type(sentencia).__name__}")

    if sentencia.error is not None:
        return ResultadoSentencia(
            linea=sentencia.linea,
            texto=sentencia.texto,
            error=sentencia.error,
        )

    if sentencia.arbol is None:
        return ResultadoSentencia(
            linea=sentencia.linea,
            texto=sentencia.texto,
            error="ERROR interno: sentencia sin arbol sintactico",
        )

    valor = evaluar(sentencia.arbol)
    return ResultadoSentencia(
        linea=sentencia.linea,
        texto=sentencia.texto,
        valor=valor,
    )


def evaluar_programa(
    programa_o_sentencias: Union[Programa, Iterable[Sentencia]],
) -> ResumenEvaluacion:
    """Evalúa un `Programa` o iterable de `Sentencia` y construye su resumen."""
    sentencias = (
        programa_o_sentencias.sentencias
        if isinstance(programa_o_sentencias, Programa)
        else programa_o_sentencias
    )

    resultados: list[ResultadoSentencia] = []
    evaluadas = 0
    con_error = 0

    for sentencia in sentencias:
        resultado = evaluar_sentencia(sentencia)
        resultados.append(resultado)
        if resultado.es_error:
            con_error += 1
        else:
            evaluadas += 1

    return ResumenEvaluacion(
        procesadas=len(resultados),
        evaluadas=evaluadas,
        con_error=con_error,
        resultados=resultados,
    )


def evaluar_con_traza(
    sentencia_o_nodo: Union[Sentencia, ExprBool, str],
    estilo_arbol: str = "unicode",
) -> tuple[ResultadoSentencia, Optional[Any]]:
    """
    Evalúa una sentencia o nodo AST y genera simultáneamente su traza detallada.
    """
    from .traza import trazar_evaluacion

    if isinstance(sentencia_o_nodo, Sentencia):
        if sentencia_o_nodo.error is not None or sentencia_o_nodo.arbol is None:
            return evaluar_sentencia(sentencia_o_nodo), None
        traza = trazar_evaluacion(
            sentencia_o_nodo.arbol,
            texto_original=sentencia_o_nodo.texto,
            estilo_arbol=estilo_arbol,
        )
        res = ResultadoSentencia(
            linea=sentencia_o_nodo.linea,
            texto=sentencia_o_nodo.texto,
            valor=traza.resultado_final,
        )
        return res, traza

    traza = trazar_evaluacion(sentencia_o_nodo, estilo_arbol=estilo_arbol)
    res = ResultadoSentencia(
        linea=1,
        texto=traza.expresion_original,
        valor=traza.resultado_final,
    )
    return res, traza


def formatear_arbol(
    nodo: ExprBool,
    con_valores: bool = True,
    estilo: str = "unicode",
) -> str:
    """Formatea el AST en una representación visual jerárquica en texto (Integrante 6)."""
    from .traza import formatear_arbol as _formatear
    return _formatear(nodo, con_valores=con_valores, estilo=estilo)


def formatear_traza(traza: Any, con_arbol: bool = True) -> str:
    """Produce una representación en texto de la traza de evaluación (Integrante 6)."""
    from .traza import formatear_traza as _formatear
    return _formatear(traza, con_arbol=con_arbol)

