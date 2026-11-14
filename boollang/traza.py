"""
Módulo de traza de evaluación y formateo del Árbol de Sintaxis Abstracta (AST).

Responsabilidad técnica del Integrante 6 (Estructura del árbol AST y traza de evaluación)
para las Tareas 36 (booleana) y 37 (proposicional relacional y aritmética).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union

from .evaluador import (
    EntornoVariables,
    ValorNumerico,
    _comparar_relacional,
    evaluar,
    evaluar_aritmetica,
    formatear_booleano,
)
from .lexer import find_column, tokenize
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
    NodoAST,
    Numero,
    UnarioArit,
    Variable,
)


@dataclass(frozen=True)
class PasoTraza:
    """Representa un paso individual en la evaluación de una expresión booleana o relacional."""

    numero: int
    operador: str
    precedencia: int
    subexpresion: str
    resultado: Union[bool, int, float]
    expresion_actual: str


@dataclass(frozen=True)
class TrazaEvaluacion:
    """Traza consolidada de la evaluación completa de una expresión."""

    expresion_original: str
    arbol_texto: str
    pasos: list[PasoTraza] = field(default_factory=list)
    resultado_final: bool = False

    @property
    def total_pasos(self) -> int:
        """Número total de pasos de reducción realizados."""
        return len(self.pasos)


def _formatear_valor_nodo(
    nodo: Any,
    entorno: Optional[EntornoVariables] = None,
) -> str:
    if isinstance(nodo, (Numero, Variable, UnarioArit, BinOpArit)):
        val = evaluar_aritmetica(nodo, entorno)
        return str(val)
    if isinstance(nodo, Asignacion):
        val = evaluar_aritmetica(nodo.expr, entorno)
        return f"{nodo.nombre}={val}"
    val_bool = evaluar(nodo, entorno)
    return formatear_booleano(val_bool)


def formatear_arbol(
    nodo: Any,
    con_valores: bool = True,
    estilo: str = "unicode",
    prefijo: str = "",
    ultimo: bool = True,
    raiz: bool = True,
    entorno: Optional[EntornoVariables] = None,
) -> str:
    """
    Formatea el AST (booleano, relacional o aritmético) en una representación visual jerárquica.
    """
    if estilo not in ("unicode", "ascii"):
        raise ValueError(f"estilo no soportado: {estilo!r} (use 'unicode' o 'ascii')")

    if estilo == "ascii":
        rama_mid = "|-- "
        rama_end = "\\-- "
        pipe = "|   "
    else:
        rama_mid = "├── "
        rama_end = "└── "
        pipe = "│   "
    space = "    "

    if isinstance(nodo, Constante):
        nombre = "true" if nodo.valor else "false"
    elif isinstance(nodo, Negacion):
        nombre = "not"
    elif isinstance(nodo, Conjuncion):
        nombre = "and"
    elif isinstance(nodo, Disyuncion):
        nombre = "or"
    elif isinstance(nodo, ComparacionRel):
        nombre = nodo.operador
    elif isinstance(nodo, BinOpArit):
        nombre = f"{nodo.operador} (impl)" if nodo.implicita else nodo.operador
    elif isinstance(nodo, UnarioArit):
        nombre = "- (unario)"
    elif isinstance(nodo, Numero):
        nombre = str(nodo.valor)
    elif isinstance(nodo, Variable):
        nombre = nodo.nombre
    elif isinstance(nodo, Asignacion):
        nombre = f"= ({nodo.nombre})"
    else:
        nombre = type(nodo).__name__

    if con_valores:
        valor_str = _formatear_valor_nodo(nodo, entorno)
        etiqueta = f"{nombre}   [{valor_str}]"
    else:
        etiqueta = nombre

    if raiz:
        lineas = [etiqueta]
        nuevo_prefijo = ""
    else:
        rama = rama_end if ultimo else rama_mid
        lineas = [prefijo + rama + etiqueta]
        nuevo_prefijo = prefijo + (space if ultimo else pipe)

    hijos = nodo.hijos() if hasattr(nodo, "hijos") else ()
    for i, hijo in enumerate(hijos):
        es_ultimo = i == len(hijos) - 1
        sub_lineas = formatear_arbol(
            hijo,
            con_valores=con_valores,
            estilo=estilo,
            prefijo=nuevo_prefijo,
            ultimo=es_ultimo,
            raiz=False,
            entorno=entorno,
        )
        lineas.append(sub_lineas)

    return "\n".join(lineas)


def _es_reducible_arit(nodo: ExprArit) -> bool:
    if isinstance(nodo, Numero):
        return False
    if isinstance(nodo, Variable):
        return True
    if isinstance(nodo, UnarioArit):
        return isinstance(nodo.op, Numero)
    if isinstance(nodo, BinOpArit):
        if nodo.implicita and isinstance(nodo.izq, Numero) and isinstance(nodo.der, (Numero, Variable)):
            return True
        return isinstance(nodo.izq, Numero) and isinstance(nodo.der, Numero)
    return False


def _encontrar_siguiente_reducible_arit(nodo: ExprArit) -> Optional[ExprArit]:
    if isinstance(nodo, Numero):
        return None
    if isinstance(nodo, Variable):
        return nodo
    if isinstance(nodo, UnarioArit):
        if _es_reducible_arit(nodo):
            return nodo
        return _encontrar_siguiente_reducible_arit(nodo.op)
    if isinstance(nodo, BinOpArit):
        if nodo.implicita and isinstance(nodo.izq, Numero) and isinstance(nodo.der, Variable):
            return nodo
        sub_izq = _encontrar_siguiente_reducible_arit(nodo.izq)
        if sub_izq is not None:
            return sub_izq
        sub_der = _encontrar_siguiente_reducible_arit(nodo.der)
        if sub_der is not None:
            return sub_der
        if _es_reducible_arit(nodo):
            return nodo
    return None


def _es_reducible(nodo: Any) -> bool:
    """Determina si un nodo puede ser evaluado en un paso inmediato."""
    if isinstance(nodo, Constante):
        return False
    if isinstance(nodo, (Numero, Variable, UnarioArit, BinOpArit)):
        return _es_reducible_arit(nodo)
    if isinstance(nodo, ComparacionRel):
        return isinstance(nodo.izq, Numero) and isinstance(nodo.der, Numero)
    if isinstance(nodo, Negacion):
        return isinstance(nodo.op, Constante)
    if isinstance(nodo, (Conjuncion, Disyuncion)):
        return isinstance(nodo.izq, Constante) and isinstance(nodo.der, Constante)
    return False


def _encontrar_siguiente_reducible(nodo: Any) -> Optional[Any]:
    """
    Encuentra el siguiente nodo reducible respetando los 7 niveles de precedencia:
    primero reduce subárboles aritméticos (unario - > * / implícita > + -),
    luego la comparación relacional (<=, >=, ==, !=, <, >) y finalmente los
    conectivos booleanos (not > and > or).
    """
    if isinstance(nodo, Constante):
        return None

    if isinstance(nodo, (Numero, Variable, UnarioArit, BinOpArit)):
        return _encontrar_siguiente_reducible_arit(nodo)

    if isinstance(nodo, ComparacionRel):
        sub_izq = _encontrar_siguiente_reducible_arit(nodo.izq)
        if sub_izq is not None:
            return sub_izq
        sub_der = _encontrar_siguiente_reducible_arit(nodo.der)
        if sub_der is not None:
            return sub_der
        if _es_reducible(nodo):
            return nodo
        return None

    if isinstance(nodo, Negacion):
        if _es_reducible(nodo):
            return nodo
        return _encontrar_siguiente_reducible(nodo.op)

    if isinstance(nodo, (Conjuncion, Disyuncion)):
        sub_izq = _encontrar_siguiente_reducible(nodo.izq)
        if sub_izq is not None:
            return sub_izq
        sub_der = _encontrar_siguiente_reducible(nodo.der)
        if sub_der is not None:
            return sub_der
        if _es_reducible(nodo):
            return nodo

    return None


def _reemplazar_subarbol_una_vez(
    arbol: Any,
    objetivo: Any,
    reemplazo: Any,
) -> Tuple[Any, bool]:
    """Reemplaza la primera aparición física del subárbol `objetivo` por `reemplazo`."""
    if arbol is objetivo:
        return reemplazo, True

    if isinstance(arbol, (Constante, Numero, Variable)):
        return arbol, False

    if isinstance(arbol, UnarioArit):
        nuevo_op, hecho = _reemplazar_subarbol_una_vez(arbol.op, objetivo, reemplazo)
        if hecho:
            return UnarioArit(nuevo_op), True
        return arbol, False

    if isinstance(arbol, BinOpArit):
        nuevo_izq, hecho = _reemplazar_subarbol_una_vez(arbol.izq, objetivo, reemplazo)
        if hecho:
            return BinOpArit(arbol.operador, nuevo_izq, arbol.der, arbol.implicita), True
        nuevo_der, hecho = _reemplazar_subarbol_una_vez(arbol.der, objetivo, reemplazo)
        if hecho:
            return BinOpArit(arbol.operador, arbol.izq, nuevo_der, arbol.implicita), True
        return arbol, False

    if isinstance(arbol, ComparacionRel):
        nuevo_izq, hecho = _reemplazar_subarbol_una_vez(arbol.izq, objetivo, reemplazo)
        if hecho:
            return ComparacionRel(arbol.operador, nuevo_izq, arbol.der), True
        nuevo_der, hecho = _reemplazar_subarbol_una_vez(arbol.der, objetivo, reemplazo)
        if hecho:
            return ComparacionRel(arbol.operador, arbol.izq, nuevo_der), True
        return arbol, False

    if isinstance(arbol, Negacion):
        nuevo_op, hecho = _reemplazar_subarbol_una_vez(arbol.op, objetivo, reemplazo)
        if hecho:
            return Negacion(nuevo_op), True
        return arbol, False

    if isinstance(arbol, Conjuncion):
        nuevo_izq, hecho = _reemplazar_subarbol_una_vez(arbol.izq, objetivo, reemplazo)
        if hecho:
            return Conjuncion(nuevo_izq, arbol.der), True
        nuevo_der, hecho = _reemplazar_subarbol_una_vez(arbol.der, objetivo, reemplazo)
        if hecho:
            return Conjuncion(arbol.izq, nuevo_der), True
        return arbol, False

    if isinstance(arbol, Disyuncion):
        nuevo_izq, hecho = _reemplazar_subarbol_una_vez(arbol.izq, objetivo, reemplazo)
        if hecho:
            return Disyuncion(nuevo_izq, arbol.der), True
        nuevo_der, hecho = _reemplazar_subarbol_una_vez(arbol.der, objetivo, reemplazo)
        if hecho:
            return Disyuncion(arbol.izq, nuevo_der), True
        return arbol, False

    return arbol, False


_TOKENS_SOLO_BOOLEANOS = frozenset({"TRUE", "FALSE", "AND", "OR", "NOT", "LPAREN", "RPAREN", "NEWLINE"})


def parsear_expresion(texto: str) -> ExprBool:
    """
    Analiza una expresión booleana o proposicional relacional y construye su AST.
    Lanza `SyntaxError` si la expresión no pertenece al lenguaje.
    """
    tokens, errores_lex = tokenize(texto)
    if errores_lex:
        err = errores_lex[0]
        raise SyntaxError(f"ERROR lexico (col {err.column}): {err.message}")

    toks = [t for t in tokens if t.type != "NEWLINE"]
    if not toks:
        raise SyntaxError("Expresion vacia")

    # Si contiene tokens relacionales o aritméticos (Tarea 37), delegar al parser LALR(1)
    if any(t.type not in _TOKENS_SOLO_BOOLEANOS for t in toks):
        from .parser import parsear_programa

        prog = parsear_programa(texto)
        if not prog.sentencias:
            raise SyntaxError("Expresion vacia")
        sent = prog.sentencias[0]
        if sent.error is not None or sent.arbol is None:
            raise SyntaxError(sent.error or "ERROR sintactico")
        if isinstance(sent.arbol, Asignacion):
            raise SyntaxError("Se esperaba una expresion booleana/relacional, no una asignacion")
        return sent.arbol

    pos = 0

    def actual():
        return toks[pos] if pos < len(toks) else None

    def consumir(esperado: Optional[str] = None):
        nonlocal pos
        t = actual()
        if t is None:
            raise SyntaxError("Fin de expresion inesperado")
        if esperado is not None and t.type != esperado:
            col = find_column(texto, t)
            raise SyntaxError(
                f"ERROR sintactico (col {col}): token inesperado {t.value!r}, se esperaba '{esperado.lower()}'"
            )
        pos += 1
        return t

    def fact_b() -> ExprBool:
        t = actual()
        if t is None:
            raise SyntaxError("Fin de expresion inesperado al esperar un factor (FactB)")
        if t.type == "NOT":
            consumir("NOT")
            return Negacion(fact_b())
        elif t.type == "LPAREN":
            consumir("LPAREN")
            nodo = exp_b()
            if actual() is None or actual().type != "RPAREN":
                raise SyntaxError("ERROR sintactico: falta ')' de cierre")
            consumir("RPAREN")
            return nodo
        elif t.type == "TRUE":
            consumir("TRUE")
            return Constante(True)
        elif t.type == "FALSE":
            consumir("FALSE")
            return Constante(False)
        else:
            col = find_column(texto, t)
            raise SyntaxError(f"ERROR sintactico (col {col}): token inesperado {t.value!r}")

    def term_b() -> ExprBool:
        nodo = fact_b()
        while actual() is not None and actual().type == "AND":
            consumir("AND")
            der = fact_b()
            nodo = Conjuncion(nodo, der)
        return nodo

    def exp_b() -> ExprBool:
        nodo = term_b()
        while actual() is not None and actual().type == "OR":
            consumir("OR")
            der = term_b()
            nodo = Disyuncion(nodo, der)
        return nodo

    resultado = exp_b()
    if pos < len(toks):
        sobrante = actual()
        col = find_column(texto, sobrante)
        raise SyntaxError(
            f"ERROR sintactico (col {col}): token inesperado {sobrante.value!r}"
        )

    return resultado


def trazar_evaluacion(
    nodo_o_cadena: Union[ExprBool, str],
    texto_original: Optional[str] = None,
    estilo_arbol: str = "unicode",
    entorno: Optional[EntornoVariables] = None,
) -> TrazaEvaluacion:
    """
    Ejecuta la evaluación paso a paso registrando los valores numéricos intermedios
    y las reducciones booleanas según la jerarquía de 7 niveles de precedencia.
    """
    if isinstance(nodo_o_cadena, str):
        texto = texto_original or nodo_o_cadena.strip()
        arbol_raiz = parsear_expresion(nodo_o_cadena)
    else:
        arbol_raiz = nodo_o_cadena
        texto = (
            texto_original
            if texto_original is not None
            else (arbol_raiz.a_texto() if hasattr(arbol_raiz, "a_texto") else str(arbol_raiz))
        )

    arbol_texto = formatear_arbol(
        arbol_raiz, con_valores=True, estilo=estilo_arbol, entorno=entorno
    )
    resultado_final = evaluar(arbol_raiz, entorno)

    if isinstance(arbol_raiz, Constante):
        paso_unico = PasoTraza(
            numero=1,
            operador="CONST",
            precedencia=4,
            subexpresion=arbol_raiz.a_texto(),
            resultado=arbol_raiz.valor,
            expresion_actual=arbol_raiz.a_texto(),
        )
        return TrazaEvaluacion(
            expresion_original=texto,
            arbol_texto=arbol_texto,
            pasos=[paso_unico],
            resultado_final=resultado_final,
        )

    pasos: list[PasoTraza] = []
    arbol_actual: Any = arbol_raiz
    numero_paso = 1

    while not isinstance(arbol_actual, Constante):
        siguiente = _encontrar_siguiente_reducible(arbol_actual)
        if siguiente is None:
            break

        sub_txt = siguiente.a_texto() if hasattr(siguiente, "a_texto") else str(siguiente)

        if isinstance(siguiente, (Variable, UnarioArit, BinOpArit)):
            val_num = evaluar_aritmetica(siguiente, entorno)
            if isinstance(siguiente, Variable):
                op_nombre = "VAR"
                prec = 8
            elif isinstance(siguiente, UnarioArit):
                op_nombre = "UMINUS"
                prec = 7
            else:
                op_nombre = siguiente.operador
                prec = siguiente.prioridad
            reemplazo: Any = Numero(val_num)
            val_res: Union[bool, int, float] = val_num
        elif isinstance(siguiente, ComparacionRel):
            val_bool = evaluar(siguiente, entorno)
            op_nombre = siguiente.operador
            prec = 4
            reemplazo = Constante(val_bool)
            val_res = val_bool
        else:
            val_bool = evaluar(siguiente, entorno)
            if isinstance(siguiente, Negacion):
                op_nombre = "NOT"
                prec = 3
            elif isinstance(siguiente, Conjuncion):
                op_nombre = "AND"
                prec = 2
            elif isinstance(siguiente, Disyuncion):
                op_nombre = "OR"
                prec = 1
            else:
                op_nombre = "CONST"
                prec = 4
            reemplazo = Constante(val_bool)
            val_res = val_bool

        arbol_actual, _ = _reemplazar_subarbol_una_vez(
            arbol_actual, siguiente, reemplazo
        )
        exp_actual_txt = (
            arbol_actual.a_texto()
            if hasattr(arbol_actual, "a_texto")
            else str(arbol_actual)
        )

        paso = PasoTraza(
            numero=numero_paso,
            operador=op_nombre,
            precedencia=prec,
            subexpresion=sub_txt,
            resultado=val_res,
            expresion_actual=exp_actual_txt,
        )
        pasos.append(paso)
        numero_paso += 1

    return TrazaEvaluacion(
        expresion_original=texto,
        arbol_texto=arbol_texto,
        pasos=pasos,
        resultado_final=resultado_final,
    )


def formatear_traza(traza: TrazaEvaluacion, con_arbol: bool = True) -> str:
    """Produce una representación en texto enriquecido de la traza de evaluación."""
    lineas = [
        "=" * 78,
        "Traza de Evaluacion (Precedencia: not > and > or)",
        "=" * 78,
        f"Expresion original: {traza.expresion_original}",
        f"Resultado final:    {formatear_booleano(traza.resultado_final)}",
    ]

    if con_arbol:
        lineas.extend([
            "",
            "Arbol Sintactico (AST) con valores por subexpresion:",
            traza.arbol_texto,
        ])

    lineas.extend([
        "",
        f"Pasos de reduccion ({traza.total_pasos} pasos):",
    ])

    for paso in traza.pasos:
        val_str = (
            formatear_booleano(paso.resultado)
            if isinstance(paso.resultado, bool)
            else str(paso.resultado)
        )
        lineas.append(f" {paso.numero:2d}. [{paso.operador:3s}] {paso.subexpresion} => {val_str}")
        lineas.append(f"     Estado: {paso.expresion_actual}")

    lineas.append("=" * 78)
    return "\n".join(lineas)


def verificar_numeral2(estilo_arbol: str = "unicode") -> dict[str, Any]:
    """
    Verifica automáticamente las 3 expresiones del Numeral 2 (E1, E2 y E3).
    """
    if estilo_arbol not in ("unicode", "ascii"):
        raise ValueError(
            f"estilo_arbol no soportado: {estilo_arbol!r} (use 'unicode' o 'ascii')"
        )

    e1_texto = "not (true and false) or false and not false"
    e2_texto = (
        "not not (false or true and not false) and (true or false) and not (true and true)"
    )
    e3_texto = "(true or not false) and not or false"

    resultados: dict[str, Any] = {}

    traza_e1 = trazar_evaluacion(e1_texto, estilo_arbol=estilo_arbol)
    resultados["E1"] = {
        "texto": e1_texto,
        "valida": True,
        "valor": traza_e1.resultado_final,
        "esperado": True,
        "coincide": traza_e1.resultado_final is True,
        "traza": traza_e1,
        "total_pasos": traza_e1.total_pasos,
    }

    traza_e2 = trazar_evaluacion(e2_texto, estilo_arbol=estilo_arbol)
    resultados["E2"] = {
        "texto": e2_texto,
        "valida": True,
        "valor": traza_e2.resultado_final,
        "esperado": False,
        "coincide": traza_e2.resultado_final is False,
        "traza": traza_e2,
        "total_pasos": traza_e2.total_pasos,
    }

    try:
        parsear_expresion(e3_texto)
        fallo_sintactico = False
        err_msg = ""
    except SyntaxError as exc:
        fallo_sintactico = True
        err_msg = str(exc)

    resultados["E3"] = {
        "texto": e3_texto,
        "valida": False,
        "bloqueo_detectado": fallo_sintactico,
        "mensaje_error": err_msg,
        "token_bloqueo": "or",
        "columna_esperada": 29,
        "bloqueo_correcto": ("col 29" in err_msg and "'or'" in err_msg),
    }

    return resultados
