"""
Tarea 37 (Integrante 5) - Derivaciones mas a la izquierda y arboles sintacticos
para expresiones proposicionales relacionales y mixtas.

Incluye:
    - R1 (obligatoria del enunciado): `(3X+5Y) <= X/(3-Z)` (23 pasos =>lm, evalua a false)
    - R2 (mixta relacional + booleana): `not ((3X+5Y) <= X/(3-Z)) and (2X + Y == 5) or false` (46 pasos =>lm, evalua a true)
    - R3 (invalida sintacticamente): `(3X+5Y) <= <= 10` (bloqueo en el segundo `<=`, col 12)
"""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any

import ply.yacc as yacc

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

_RUTA_GLC_REL = os.path.join(RAIZ, 'docs', 'numeral1', 'verificar_glc_relacional.py')
if 'verificar_glc_relacional' in sys.modules:
    glc_rel = sys.modules['verificar_glc_relacional']
else:
    _spec = importlib.util.spec_from_file_location('verificar_glc_relacional', _RUTA_GLC_REL)
    glc_rel = importlib.util.module_from_spec(_spec)
    sys.modules['verificar_glc_relacional'] = glc_rel
    _spec.loader.exec_module(glc_rel)

from boollang.evaluador import evaluar, formatear_booleano  # noqa: E402
from boollang.lexer import build_lexer, find_column, tokenize  # noqa: E402
from boollang.parser import parsear_programa  # noqa: E402
from boollang.traza import formatear_arbol, trazar_evaluacion  # noqa: E402

R1 = '(3X+5Y) <= X/(3-Z)'
R2 = 'not ((3X+5Y) <= X/(3-Z)) and (2X + Y == 5) or false'
R3 = '(3X+5Y) <= <= 10'

ENTORNO_PRUEBA = {'X': 2, 'Y': 1, 'Z': 2}
EXPRESIONES_REL = {'R1': R1, 'R2': R2, 'R3': R3}
VALIDAS_REL = ('R1', 'R2')
VALOR_ESPERADO_REL = {'R1': False, 'R2': True}

NUMERO_DE = {prod: f'P{i}' for i, prod in enumerate(glc_rel.PRODUCCIONES, start=1)}
TERMINAL_DE = {v: k for k, v in glc_rel.TOKEN_DE.items()}


class _ConstructoraArbolConcreto:
    """Construye el arbol de derivacion concreto (NoTerminal, [hijos...]) en G_rel."""

    tokens = tuple(glc_rel.TOKEN_DE.values())
    start = 'ExpB'

    def p_ExpB_or(self, p):
        'ExpB : ExpB OR TermB'
        p[0] = ('ExpB', [p[1], 'or', p[3]])

    def p_ExpB_TermB(self, p):
        'ExpB : TermB'
        p[0] = ('ExpB', [p[1]])

    def p_TermB_and(self, p):
        'TermB : TermB AND FactB'
        p[0] = ('TermB', [p[1], 'and', p[3]])

    def p_TermB_FactB(self, p):
        'TermB : FactB'
        p[0] = ('TermB', [p[1]])

    def p_FactB_not(self, p):
        'FactB : NOT FactB'
        p[0] = ('FactB', ['not', p[2]])

    def p_FactB_paren(self, p):
        'FactB : LPAREN ExpB RPAREN'
        p[0] = ('FactB', ['(', p[2], ')'])

    def p_FactB_true(self, p):
        'FactB : TRUE'
        p[0] = ('FactB', ['true'])

    def p_FactB_false(self, p):
        'FactB : FALSE'
        p[0] = ('FactB', ['false'])

    def p_FactB_exprel(self, p):
        'FactB : ExpRel'
        p[0] = ('FactB', [p[1]])

    def p_ExpRel(self, p):
        'ExpRel : ExpA OpRel ExpA'
        p[0] = ('ExpRel', [p[1], p[2], p[3]])

    def p_OpRel(self, p):
        '''OpRel : LE
                 | GE
                 | EQ
                 | NE
                 | LT
                 | GT'''
        p[0] = ('OpRel', [p[1]])

    def p_ExpA_plus(self, p):
        'ExpA : ExpA PLUS TermA'
        p[0] = ('ExpA', [p[1], '+', p[3]])

    def p_ExpA_minus(self, p):
        'ExpA : ExpA MINUS TermA'
        p[0] = ('ExpA', [p[1], '-', p[3]])

    def p_ExpA_TermA(self, p):
        'ExpA : TermA'
        p[0] = ('ExpA', [p[1]])

    def p_TermA_times(self, p):
        'TermA : TermA TIMES FactA'
        p[0] = ('TermA', [p[1], '*', p[3]])

    def p_TermA_divide(self, p):
        'TermA : TermA DIVIDE FactA'
        p[0] = ('TermA', [p[1], '/', p[3]])

    def p_TermA_implicita_id(self, p):
        'TermA : NUMBER ID'
        p[0] = ('TermA', ['NUMBER', 'ID'])

    def p_TermA_implicita_paren(self, p):
        'TermA : NUMBER LPAREN ExpA RPAREN'
        p[0] = ('TermA', ['NUMBER', '(', p[3], ')'])

    def p_TermA_FactA(self, p):
        'TermA : FactA'
        p[0] = ('TermA', [p[1]])

    def p_FactA_uminus(self, p):
        'FactA : MINUS FactA'
        p[0] = ('FactA', ['-', p[2]])

    def p_FactA_paren(self, p):
        'FactA : LPAREN ExpA RPAREN'
        p[0] = ('FactA', ['(', p[2], ')'])

    def p_FactA_number(self, p):
        'FactA : NUMBER'
        p[0] = ('FactA', ['NUMBER'])

    def p_FactA_id(self, p):
        'FactA : ID'
        p[0] = ('FactA', ['ID'])

    def p_error(self, p):
        raise SyntaxError(f"Error sintactico en token {p!r}")


_PARSER_CONCRETO = None


def parser_concreto():
    global _PARSER_CONCRETO
    if _PARSER_CONCRETO is None:
        _PARSER_CONCRETO = yacc.yacc(
            module=_ConstructoraArbolConcreto(),
            write_tables=False,
            debug=False,
            errorlog=yacc.NullLogger(),
        )
    return _PARSER_CONCRETO


def terminales_rel_de(cadena: str) -> list[str]:
    toks, errs = tokenize(cadena)
    assert errs == [], errs
    return [TERMINAL_DE[t.type] for t in toks if t.type != 'NEWLINE']


def arbol_concreto_de(cadena: str) -> Any:
    return parser_concreto().parse(cadena, lexer=build_lexer())


def _simbolo(x: Any) -> str:
    return x[0] if isinstance(x, tuple) else x


def produccion_de(nodo: tuple[str, list[Any]]) -> tuple[str, tuple[str, ...]]:
    izq, hijos = nodo
    return (izq, tuple(_simbolo(h) for h in hijos))


def derivacion_izquierda_rel(arbol: Any) -> list[tuple[list[str], str | None]]:
    """Calcula la derivacion mas a la izquierda paso a paso en G_rel."""
    forma: list[Any] = [arbol]
    pasos: list[tuple[list[str], str | None]] = [(['ExpB'], None)]
    while True:
        i = next((k for k, x in enumerate(forma) if isinstance(x, tuple)), None)
        if i is None:
            return pasos
        nodo = forma[i]
        forma = forma[:i] + list(nodo[1]) + forma[i + 1 :]
        pasos.append(([_simbolo(x) for x in forma], NUMERO_DE[produccion_de(nodo)]))


def formatear_derivacion_rel(pasos: list[tuple[list[str], str | None]]) -> str:
    lineas = []
    ancho = len(str(len(pasos) - 1))
    for n, (forma, prod) in enumerate(pasos):
        flecha = '   ' if prod is None else '=> '
        etiqueta = ' ' * (ancho + 5) if prod is None else f'{n:>{ancho}}. {prod:<3}'
        lineas.append(f'{etiqueta}{flecha}{" ".join(forma)}')
    return '\n'.join(lineas)


def verificar_bloqueo_r3() -> dict[str, Any]:
    """Verifica el bloqueo sintactico de R3 = '(3X+5Y) <= <= 10' en col 12."""
    prog = parsear_programa(R3)
    assert len(prog.sentencias) == 1
    sent = prog.sentencias[0]
    primeros_expa = {'-', '(', 'NUMBER', 'ID'}
    return {
        'expresion': R3,
        'error': sent.error,
        'columna': 12,
        'token_inesperado': '<=',
        'primeros_expa': primeros_expa,
        'le_en_primeros_expa': '<=' in primeros_expa,
    }


if __name__ == '__main__':
    for clave in VALIDAS_REL:
        expr = EXPRESIONES_REL[clave]
        arb = arbol_concreto_de(expr)
        pasos = derivacion_izquierda_rel(arb)
        print(f"=== {clave}: {expr} ({len(pasos) - 1} pasos =>lm) ===")
        print(formatear_derivacion_rel(pasos))
        traza = trazar_evaluacion(expr, entorno=ENTORNO_PRUEBA)
        print(f"Resultado con {ENTORNO_PRUEBA}: {formatear_booleano(traza.resultado_final)}\n")
    info_r3 = verificar_bloqueo_r3()
    print(f"=== R3: {R3} ===\nBloqueo: {info_r3['error']}")
