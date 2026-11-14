"""
Evaluador semántico para expresiones booleanas, proposicionales relacionales,
subárboles aritméticos y entorno de variables de boollang / rellang (Tareas 36 y 37).

Responsabilidad técnica del Integrante 4, con soporte de traza del Integrante 6.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Union

from .nodos import (
    Asignacion,
    BinOpArit,
    ComparacionRel,
    Conjuncion,
    Constante,
    Disyuncion,
    ExprArit,
    ExprBool,
    Negacion,
    Numero,
    Programa,
    Sentencia,
    UnarioArit,
    Variable,
)

ValorNumerico = Union[int, float]
EntornoVariables = Dict[str, ValorNumerico]


class ErrorSemantico(Exception):
    """Error semántico durante la evaluación (división por cero o variable no inicializada)."""


def formatear_booleano(valor: bool) -> str:
    """Serializa un booleano de Python usando la sintaxis oficial (`true` / `false`)."""
    if not isinstance(valor, bool):
        raise TypeError(f"Se esperaba un valor bool, se recibió {type(valor).__name__}")
    return "true" if valor else "false"


def evaluar_aritmetica(
    nodo: ExprArit,
    entorno: Optional[EntornoVariables] = None,
) -> ValorNumerico:
    """Evalúa recursivamente un subárbol aritmético (`ExprArit`) usando `entorno`."""
    env = entorno if entorno is not None else {}

    if isinstance(nodo, Numero):
        if isinstance(nodo.valor, bool) or not isinstance(nodo.valor, (int, float)):
            raise TypeError(
                f"Numero.valor debe ser int o float, se recibió {type(nodo.valor).__name__}"
            )
        return nodo.valor

    if isinstance(nodo, Variable):
        if nodo.nombre not in env:
            raise ErrorSemantico(
                f"ERROR semantico: variable '{nodo.nombre}' no definida"
            )
        return env[nodo.nombre]

    if isinstance(nodo, UnarioArit):
        return -evaluar_aritmetica(nodo.op, env)

    if isinstance(nodo, BinOpArit):
        izq = evaluar_aritmetica(nodo.izq, env)
        der = evaluar_aritmetica(nodo.der, env)
        if nodo.operador == "+":
            return izq + der
        if nodo.operador == "-":
            return izq - der
        if nodo.operador == "*":
            return izq * der
        if nodo.operador == "/":
            if der == 0:
                raise ErrorSemantico(
                    f"ERROR semantico: division por cero en '{nodo.a_texto()}'"
                )
            return izq / der
        raise ValueError(f"Operador aritmético desconocido: {nodo.operador!r}")

    raise TypeError(f"Nodo aritmético no soportado: {type(nodo).__name__}")


def _comparar_relacional(op: str, izq: ValorNumerico, der: ValorNumerico) -> bool:
    if op == "<=":
        return bool(izq <= der)
    if op == ">=":
        return bool(izq >= der)
    if op == "==":
        return bool(izq == der)
    if op == "!=":
        return bool(izq != der)
    if op == "<":
        return bool(izq < der)
    if op == ">":
        return bool(izq > der)
    raise ValueError(f"Operador relacional desconocido: {op!r}")


def evaluar(
    nodo: ExprBool,
    entorno: Optional[EntornoVariables] = None,
) -> bool:
    """Evalúa recursivamente un nodo AST booleano o relacional y retorna `bool`."""
    if isinstance(nodo, Constante):
        if not isinstance(nodo.valor, bool):
            raise TypeError(
                f"Constante.valor debe ser bool, se recibió {type(nodo.valor).__name__}"
            )
        return nodo.valor

    if isinstance(nodo, ComparacionRel):
        izq = evaluar_aritmetica(nodo.izq, entorno)
        der = evaluar_aritmetica(nodo.der, entorno)
        return _comparar_relacional(nodo.operador, izq, der)

    if isinstance(nodo, Negacion):
        return not evaluar(nodo.op, entorno)

    if isinstance(nodo, Conjuncion):
        izq = evaluar(nodo.izq, entorno)
        der = evaluar(nodo.der, entorno)
        return izq and der

    if isinstance(nodo, Disyuncion):
        izq = evaluar(nodo.izq, entorno)
        der = evaluar(nodo.der, entorno)
        return izq or der

    raise TypeError(f"Nodo AST no soportado: {type(nodo).__name__}")


@dataclass(frozen=True)
class ResultadoSentencia:
    """Resultado de evaluar una sentencia individual (booleana, relacional, asignación o error)."""

    linea: int
    texto: str
    valor: Optional[bool] = None
    error: Optional[str] = None
    arbol: Optional[Union[ExprBool, Asignacion]] = field(
        default=None, compare=False, repr=False
    )
    es_asignacion: bool = field(default=False, compare=False, repr=False)
    entorno_asignado: Optional[str] = field(default=None, compare=False, repr=False)
    detalle_relacional: Optional[str] = field(default=None, compare=False, repr=False)

    @property
    def es_error(self) -> bool:
        """Indica si la sentencia culminó con un error léxico, sintáctico o semántico."""
        return self.error is not None

    def formatear_linea(self) -> str:
        """Retorna la representación oficial de la línea para el archivo `.out`."""
        if self.error is not None:
            return f"[L{self.linea}] {self.texto} => {self.error}"
        if self.es_asignacion and self.entorno_asignado is not None:
            return f"[L{self.linea}] {self.texto} => {self.entorno_asignado}"
        if self.valor is None:
            return f"[L{self.linea}] {self.texto} => ERROR interno: resultado booleano ausente"
        if self.detalle_relacional is not None:
            return f"[L{self.linea}] {self.texto} => {formatear_booleano(self.valor)} ({self.detalle_relacional})"
        return f"[L{self.linea}] {self.texto} => {formatear_booleano(self.valor)}"


@dataclass(frozen=True)
class ResumenEvaluacion:
    """Resumen consolidado de todas las sentencias procesadas de un programa."""

    procesadas: int
    evaluadas: int
    con_error: int
    resultados: list[ResultadoSentencia]
    asignaciones: int = 0
    entorno: EntornoVariables = field(default_factory=dict, compare=False, repr=False)
    modo_relacional: bool = field(default=False, compare=False, repr=False)


def _contiene_nodos_relacionales(nodo: Any) -> bool:
    if isinstance(nodo, (ComparacionRel, Asignacion)):
        return True
    if hasattr(nodo, "hijos"):
        return any(_contiene_nodos_relacionales(h) for h in nodo.hijos())
    return False


def evaluar_sentencia(
    sentencia: Sentencia,
    entorno: Optional[EntornoVariables] = None,
) -> ResultadoSentencia:
    """Evalúa una `Sentencia`, respetando errores previos y actualizando `entorno` si es `Asignacion`."""
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

    env = entorno if entorno is not None else {}

    try:
        if isinstance(sentencia.arbol, Asignacion):
            val_num = evaluar_aritmetica(sentencia.arbol.expr, env)
            env[sentencia.arbol.nombre] = val_num
            return ResultadoSentencia(
                linea=sentencia.linea,
                texto=sentencia.texto,
                arbol=sentencia.arbol,
                es_asignacion=True,
                entorno_asignado=f"[Entorno: {sentencia.arbol.nombre}={val_num}]",
            )

        if isinstance(sentencia.arbol, ComparacionRel):
            izq_val = evaluar_aritmetica(sentencia.arbol.izq, env)
            der_val = evaluar_aritmetica(sentencia.arbol.der, env)
            valor = _comparar_relacional(sentencia.arbol.operador, izq_val, der_val)
            return ResultadoSentencia(
                linea=sentencia.linea,
                texto=sentencia.texto,
                valor=valor,
                arbol=sentencia.arbol,
                detalle_relacional=f"{izq_val} {sentencia.arbol.operador} {der_val}",
            )

        valor = evaluar(sentencia.arbol, env)
        return ResultadoSentencia(
            linea=sentencia.linea,
            texto=sentencia.texto,
            valor=valor,
            arbol=sentencia.arbol,
        )
    except ErrorSemantico as exc:
        return ResultadoSentencia(
            linea=sentencia.linea,
            texto=sentencia.texto,
            error=str(exc),
            arbol=sentencia.arbol,
        )


def evaluar_programa(
    programa_o_sentencias: Union[Programa, Iterable[Sentencia]],
    entorno_inicial: Optional[EntornoVariables] = None,
) -> ResumenEvaluacion:
    """Evalúa un `Programa` o secuencia de `Sentencia`, agrupando asignaciones de una misma línea."""
    lista_sentencias = list(
        programa_o_sentencias.sentencias
        if isinstance(programa_o_sentencias, Programa)
        else programa_o_sentencias
    )

    entorno: EntornoVariables = dict(entorno_inicial) if entorno_inicial else {}
    resultados: list[ResultadoSentencia] = []
    asignaciones = 0
    evaluadas = 0
    con_error = 0
    usa_relacional = False

    i = 0
    n = len(lista_sentencias)
    while i < n:
        sent = lista_sentencias[i]
        if sent.arbol is not None and _contiene_nodos_relacionales(sent.arbol):
            usa_relacional = True

        # Agrupar asignaciones consecutivas válidas en la misma línea (ej. X = 2; Y = 1; Z = 2;)
        if (
            sent.error is None
            and isinstance(sent.arbol, Asignacion)
        ):
            linea_grupo = sent.linea
            textos_grupo: list[str] = []
            pares_entorno: list[str] = []
            error_sem: Optional[str] = None

            while (
                i < n
                and lista_sentencias[i].linea == linea_grupo
                and lista_sentencias[i].error is None
                and isinstance(lista_sentencias[i].arbol, Asignacion)
            ):
                s_asig = lista_sentencias[i]
                asig_nodo = s_asig.arbol
                assert isinstance(asig_nodo, Asignacion)
                textos_grupo.append(s_asig.texto)
                try:
                    val_num = evaluar_aritmetica(asig_nodo.expr, entorno)
                    entorno[asig_nodo.nombre] = val_num
                    pares_entorno.append(f"{asig_nodo.nombre}={val_num}")
                except ErrorSemantico as exc:
                    error_sem = str(exc)
                    i += 1
                    break
                i += 1

            texto_combinado = "; ".join(textos_grupo)
            if error_sem is not None:
                resultados.append(
                    ResultadoSentencia(
                        linea=linea_grupo,
                        texto=texto_combinado,
                        error=error_sem,
                        arbol=sent.arbol,
                    )
                )
                con_error += 1
            else:
                resultados.append(
                    ResultadoSentencia(
                        linea=linea_grupo,
                        texto=texto_combinado,
                        arbol=sent.arbol,
                        es_asignacion=True,
                        entorno_asignado=f"[Entorno: {', '.join(pares_entorno)}]",
                    )
                )
                asignaciones += 1
            continue

        resultado = evaluar_sentencia(sent, entorno)
        resultados.append(resultado)
        if resultado.es_error:
            con_error += 1
        elif resultado.es_asignacion:
            asignaciones += 1
        else:
            evaluadas += 1
        i += 1

    return ResumenEvaluacion(
        procesadas=len(resultados),
        evaluadas=evaluadas,
        con_error=con_error,
        resultados=resultados,
        asignaciones=asignaciones,
        entorno=entorno,
        modo_relacional=usa_relacional or asignaciones > 0,
    )


def evaluar_con_traza(
    sentencia_o_nodo: Union[Sentencia, ExprBool, str],
    estilo_arbol: str = "unicode",
    entorno: Optional[EntornoVariables] = None,
) -> tuple[ResultadoSentencia, Optional[Any]]:
    """Evalúa una sentencia o nodo AST y genera simultáneamente su traza detallada."""
    from .traza import trazar_evaluacion

    if isinstance(sentencia_o_nodo, Sentencia):
        if (
            sentencia_o_nodo.error is not None
            or sentencia_o_nodo.arbol is None
            or isinstance(sentencia_o_nodo.arbol, Asignacion)
        ):
            return evaluar_sentencia(sentencia_o_nodo, entorno), None
        try:
            traza = trazar_evaluacion(
                sentencia_o_nodo.arbol,
                texto_original=sentencia_o_nodo.texto,
                estilo_arbol=estilo_arbol,
                entorno=entorno,
            )
            res = avaliar_res = evaluar_sentencia(sentencia_o_nodo, entorno)
            return res, traza
        except ErrorSemantico as exc:
            return (
                ResultadoSentencia(
                    linea=sentencia_o_nodo.linea,
                    texto=sentencia_o_nodo.texto,
                    error=str(exc),
                    arbol=sentencia_o_nodo.arbol,
                ),
                None,
            )

    traza = trazar_evaluacion(
        sentencia_o_nodo, estilo_arbol=estilo_arbol, entorno=entorno
    )
    res = ResultadoSentencia(
        linea=1,
        texto=traza.expresion_original,
        valor=traza.resultado_final,
    )
    return res, traza


def formatear_arbol(
    nodo: Any,
    con_valores: bool = True,
    estilo: str = "unicode",
    entorno: Optional[EntornoVariables] = None,
) -> str:
    """Formatea el AST en una representación visual jerárquica en texto (Integrante 6)."""
    from .traza import formatear_arbol as _formatear

    return _formatear(nodo, con_valores=con_valores, estilo=estilo, entorno=entorno)


def formatear_traza(traza: Any, con_arbol: bool = True) -> str:
    """Produce una representación en texto de la traza de evaluación (Integrante 6)."""
    from .traza import formatear_traza as _formatear

    return _formatear(traza, con_arbol=con_arbol)
