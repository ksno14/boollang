"""
Módulo de traza de evaluación y formateo del Árbol de Sintaxis Abstracta (AST).

Responsabilidad técnica del Integrante 6 (Estructura del árbol AST y traza de evaluación).

Este módulo proporciona:
- Representación en texto estructurado del AST (`formatear_arbol`).
- Simulación paso a paso de la evaluación según precedencia de operadores (not > and > or) (`trazar_evaluacion`).
- Formateo legible de la traza de evaluación (`formatear_traza`).
- Verificación automatizada de las 3 expresiones del Numeral 2 (`verificar_numeral2`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple, Union

from .evaluador import evaluar, formatear_booleano
from .lexer import find_column, tokenize
from .nodos import Conjuncion, Constante, Disyuncion, ExprBool, Negacion


@dataclass(frozen=True)
class PasoTraza:
    """Representa un paso individual en la evaluación de una expresión booleana."""

    numero: int
    operador: str
    precedencia: int
    subexpresion: str
    resultado: bool
    expresion_actual: str

    def formatear(self) -> str:
        """Formatea el paso en una línea descriptiva con su estado resultante."""
        val_str = formatear_booleano(self.resultado)
        return (
            f" {self.numero:2d}. [{self.operador:3s}] {self.subexpresion} => {val_str}\n"
            f"     Estado: {self.expresion_actual}"
        )


@dataclass(frozen=True)
class TrazaEvaluacion:
    """Traza consolidada de la evaluación completa de una expresión booleana."""

    expresion_original: str
    arbol_texto: str
    pasos: list[PasoTraza] = field(default_factory=list)
    resultado_final: bool = False

    @property
    def total_pasos(self) -> int:
        """Número total de pasos de reducción realizados."""
        return len(self.pasos)


def formatear_arbol(
    nodo: ExprBool,
    con_valores: bool = True,
    estilo: str = "unicode",
    prefijo: str = "",
    ultimo: bool = True,
    raiz: bool = True,
) -> str:
    """
    Formatea el AST en una representación visual jerárquica en texto.

    Parámetros:
        nodo: Nodo raíz o subárbol de tipo `ExprBool`.
        con_valores: Si es True, añade el valor evaluado `[true]` o `[false]` de cada subárbol.
        estilo: "unicode" para ramas `├── `, `└── `, `│   `; "ascii" para `|-- `, `\\-- `, `|   `.
        prefijo: Cadena interna de indentación para recursión.
        ultimo: Booleano que indica si es el último hijo en su nivel.
        raiz: Booleano que indica si es la raíz del árbol.
    """
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
    else:
        nombre = type(nodo).__name__

    if con_valores:
        valor_str = formatear_booleano(evaluar(nodo))
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
        )
        lineas.append(sub_lineas)

    return "\n".join(lineas)


def _es_reducible(nodo: ExprBool) -> bool:
    """Determina si un nodo puede ser evaluado directamente porque todos sus hijos son constantes."""
    if isinstance(nodo, Constante):
        return False
    if isinstance(nodo, Negacion):
        return isinstance(nodo.op, Constante)
    if isinstance(nodo, (Conjuncion, Disyuncion)):
        return isinstance(nodo.izq, Constante) and isinstance(nodo.der, Constante)
    return False


def _encontrar_siguiente_reducible(nodo: ExprBool) -> Optional[ExprBool]:
    """
    Encuentra el siguiente nodo reducible en orden de evaluación natural (post-orden):
    evalúa subárboles agrupados (paréntesis), y dentro de cada subexpresión
    respeta la precedencia (not > and > or) y asociatividad a izquierda.
    """
    if isinstance(nodo, Constante):
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
    arbol: ExprBool,
    objetivo: ExprBool,
    reemplazo: ExprBool,
) -> Tuple[ExprBool, bool]:
    """Reemplaza la primera aparición física del subárbol `objetivo` por `reemplazo`."""
    if arbol is objetivo:
        return reemplazo, True

    if isinstance(arbol, Constante):
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


def parsear_expresion(texto: str) -> ExprBool:
    """
    Analiza una expresión booleana individual según la gramática de la Figura 3
    y construye directamente su Árbol de Sintaxis Abstracta (AST).
    Lanza `SyntaxError` si la expresión no pertenece al lenguaje.
    """
    tokens, errores_lex = tokenize(texto)
    if errores_lex:
        err = errores_lex[0]
        raise SyntaxError(f"ERROR lexico (col {err.column}): {err.message}")

    toks = [t for t in tokens if t.type != "NEWLINE"]
    if not toks:
        raise SyntaxError("Expresion vacia")

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
) -> TrazaEvaluacion:
    """
    Ejecuta la evaluación paso a paso registrando el orden de precedencia y las reducciones.

    Retorna un objeto `TrazaEvaluacion` con el árbol formateado y la lista de `PasoTraza`.
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

    arbol_texto = formatear_arbol(arbol_raiz, con_valores=True, estilo=estilo_arbol)
    resultado_final = evaluar(arbol_raiz)

    # Si la expresión es una constante atómica
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
    arbol_actual = arbol_raiz
    numero_paso = 1

    while not isinstance(arbol_actual, Constante):
        siguiente = _encontrar_siguiente_reducible(arbol_actual)
        if siguiente is None:
            break

        val = evaluar(siguiente)
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

        sub_txt = siguiente.a_texto() if hasattr(siguiente, "a_texto") else str(siguiente)
        arbol_actual, _ = _reemplazar_subarbol_una_vez(
            arbol_actual, siguiente, Constante(val)
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
            resultado=val,
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
        val_str = formatear_booleano(paso.resultado)
        lineas.append(f" {paso.numero:2d}. [{paso.operador:3s}] {paso.subexpresion} => {val_str}")
        lineas.append(f"     Estado: {paso.expresion_actual}")

    lineas.append("=" * 78)
    return "\n".join(lineas)


def verificar_numeral2(con_traza: bool = True) -> dict[str, Any]:
    """
    Verifica automáticamente las 3 expresiones del Numeral 2 (E1, E2 y E3).

    - E1: 'not (true and false) or false and not false' (válida, evalúa a true)
    - E2: 'not not (false or true and not false) and (true or false) and not (true and true)' (válida, evalúa a false)
    - E3: '(true or not false) and not or false' (inválida, error sintáctico en token 'or', col 29)

    Retorna un diccionario estructurado con los resultados, trazas y mensajes.
    """
    e1_texto = "not (true and false) or false and not false"
    e2_texto = (
        "not not (false or true and not false) and (true or false) and not (true and true)"
    )
    e3_texto = "(true or not false) and not or false"

    resultados: dict[str, Any] = {}

    # E1
    traza_e1 = trazar_evaluacion(e1_texto)
    resultados["E1"] = {
        "texto": e1_texto,
        "valida": True,
        "valor": traza_e1.resultado_final,
        "esperado": True,
        "coincide": traza_e1.resultado_final is True,
        "traza": traza_e1,
        "total_pasos": traza_e1.total_pasos,
    }

    # E2
    traza_e2 = trazar_evaluacion(e2_texto)
    resultados["E2"] = {
        "texto": e2_texto,
        "valida": True,
        "valor": traza_e2.resultado_final,
        "esperado": False,
        "coincide": traza_e2.resultado_final is False,
        "traza": traza_e2,
        "total_pasos": traza_e2.total_pasos,
    }

    # E3 (debe fallar con error de sintaxis en col 29 ante 'or')
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
