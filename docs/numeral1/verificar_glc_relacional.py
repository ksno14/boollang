"""
Numeral 1 (Tarea 37) - Verificacion formal de la GLC extendida para expresiones
proposicionales relacionales y aritmeticas (gramatica_relacional.ebnf).

Comprueba de forma automatica:
    1. G_rel es una GLC bien formada (V y Sigma disjuntos, producciones validas).
    2. Todos los no terminales son productivos.
    3. Todos los simbolos (no terminales y terminales) son alcanzables desde ExpB.
    4. La gramatica de expresiones (G_rel) es libre de producciones epsilon y anulables.
    5. La gramatica es libre de ciclos (ningun A =>+ A).
    6. La jerarquia de 7 niveles de precedencia (or < and < not < OpRel < +/- < *//implicita < unario -)
       genera una tabla LALR(1) en ply.yacc con 0 conflictos shift/reduce y 0 reduce/reduce.
    7. El ejemplo del enunciado `(3X+5Y) <= X/(3-Z)` y las expresiones mixtas se aceptan
       con arbol unico y precedencia exacta.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

import ply.yacc as yacc

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from boollang.lexer import build_lexer, tokens as LEXER_TOKENS

# ---------------------------------------------------------------------------
# Definicion formal de G_rel = (V, Sigma, P, S) para expresiones relacionales
# ---------------------------------------------------------------------------

NO_TERMINALES = (
    'ExpB',
    'TermB',
    'FactB',
    'ExpRel',
    'OpRel',
    'ExpA',
    'TermA',
    'FactA',
)

TERMINALES = (
    'or',
    'and',
    'not',
    '(',
    ')',
    'true',
    'false',
    '<=',
    '>=',
    '==',
    '!=',
    '<',
    '>',
    '+',
    '-',
    '*',
    '/',
    'NUMBER',
    'ID',
)

INICIAL = 'ExpB'

PRODUCCIONES = (
    # Nivel 1-3: Booleano (Figura 3 + puente ExpRel)
    ('ExpB', ('ExpB', 'or', 'TermB')),          # P1
    ('ExpB', ('TermB',)),                       # P2
    ('TermB', ('TermB', 'and', 'FactB')),       # P3
    ('TermB', ('FactB',)),                      # P4
    ('FactB', ('not', 'FactB')),                # P5
    ('FactB', ('(', 'ExpB', ')')),              # P6
    ('FactB', ('true',)),                       # P7
    ('FactB', ('false',)),                      # P8
    ('FactB', ('ExpRel',)),                     # P9 (Extension Tarea 37)
    # Nivel 4: Proposicional Relacional
    ('ExpRel', ('ExpA', 'OpRel', 'ExpA')),      # P10
    ('OpRel', ('<=',)),                         # P11
    ('OpRel', ('>=',)),                         # P12
    ('OpRel', ('==',)),                         # P13
    ('OpRel', ('!=',)),                         # P14
    ('OpRel', ('<',)),                          # P15
    ('OpRel', ('>',)),                          # P16
    # Nivel 5: Aditivo Aritmetico
    ('ExpA', ('ExpA', '+', 'TermA')),           # P17
    ('ExpA', ('ExpA', '-', 'TermA')),           # P18
    ('ExpA', ('TermA',)),                       # P19
    # Nivel 6: Multiplicativo Aritmetico + Multiplicacion Implicita (3X, 2(X+1))
    ('TermA', ('TermA', '*', 'FactA')),         # P20
    ('TermA', ('TermA', '/', 'FactA')),         # P21
    ('TermA', ('NUMBER', 'ID')),                # P22
    ('TermA', ('NUMBER', '(', 'ExpA', ')')),    # P23
    ('TermA', ('FactA',)),                      # P24
    # Nivel 7: Unario Aritmetico y Atomos Algebraicos
    ('FactA', ('-', 'FactA')),                  # P25
    ('FactA', ('(', 'ExpA', ')')),              # P26
    ('FactA', ('NUMBER',)),                     # P27
    ('FactA', ('ID',)),                         # P28
)

TOKEN_DE = {
    'true': 'TRUE',
    'false': 'FALSE',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
    '(': 'LPAREN',
    ')': 'RPAREN',
    '<=': 'LE',
    '>=': 'GE',
    '==': 'EQ',
    '!=': 'NE',
    '<': 'LT',
    '>': 'GT',
    '+': 'PLUS',
    '-': 'MINUS',
    '*': 'TIMES',
    '/': 'DIVIDE',
    'NUMBER': 'NUMBER',
    'ID': 'ID',
}

NIVELES_PRECEDENCIA = (
    (1, 'Disyuncion logica', ('or',), 'Izquierda', 'ExpB -> ExpB or TermB'),
    (2, 'Conjuncion logica', ('and',), 'Izquierda', 'TermB -> TermB and FactB'),
    (3, 'Negacion logica', ('not',), 'Derecha (prefijo)', 'FactB -> not FactB'),
    (4, 'Comparacion relacional', ('<=', '>=', '==', '!=', '<', '>'), 'No asociativo', 'ExpRel -> ExpA OpRel ExpA'),
    (5, 'Aditivo aritmetico', ('+', '-'), 'Izquierda', 'ExpA -> ExpA +/- TermA'),
    (6, 'Multiplicativo e implicito', ('*', '/', 'NUMBER ID', 'NUMBER (ExpA)'), 'Izquierda', 'TermA -> TermA *// FactA | NUMBER ID'),
    (7, 'Unario aritmetico', ('- (unario)',), 'Derecha (prefijo)', 'FactA -> - FactA'),
)


def verificar_bien_formada(
    producciones=PRODUCCIONES,
    V=NO_TERMINALES,
    T=TERMINALES,
    S=INICIAL,
) -> list[str]:
    problemas: list[str] = []
    if set(V) & set(T):
        problemas.append(f'V y Sigma no son disjuntos: {set(V) & set(T)}')
    if S not in V:
        problemas.append(f'El simbolo inicial {S} no pertenece a V')
    for izq, der in producciones:
        if izq not in V:
            problemas.append(f'Lado izquierdo {izq!r} no es un no terminal')
        for s in der:
            if s not in V and s not in T:
                problemas.append(f'Simbolo {s!r} en {izq} no esta en V U Sigma')
    for A in V:
        if not any(izq == A for izq, _ in producciones):
            problemas.append(f'{A} no tiene producciones')
    return problemas


def productivos(producciones=PRODUCCIONES, T=TERMINALES) -> list[frozenset[str]]:
    actual: set[str] = set()
    pasos: list[frozenset[str]] = []
    while True:
        nuevo = set(actual)
        for izq, der in producciones:
            if all(s in T or s in actual for s in der):
                nuevo.add(izq)
        if nuevo == actual:
            return pasos
        pasos.append(frozenset(nuevo))
        actual = nuevo


def alcanzables(producciones=PRODUCCIONES, S=INICIAL) -> list[frozenset[str]]:
    actual: set[str] = {S}
    pasos: list[frozenset[str]] = [frozenset(actual)]
    while True:
        nuevo = set(actual)
        for izq, der in producciones:
            if izq in actual:
                nuevo.update(der)
        if nuevo == actual:
            return pasos
        pasos.append(frozenset(nuevo))
        actual = nuevo


def producciones_epsilon(producciones=PRODUCCIONES) -> list[Any]:
    return [p for p in producciones if len(p[1]) == 0]


def anulables(producciones=PRODUCCIONES) -> set[str]:
    anul: set[str] = set()
    cambio = True
    while cambio:
        cambio = False
        for izq, der in producciones:
            if izq not in anul and all(s in anul for s in der):
                anul.add(izq)
                cambio = True
    return anul


def pares_unitarios(producciones=PRODUCCIONES, V=NO_TERMINALES) -> set[tuple[str, str]]:
    unitarias = {
        (izq, der[0])
        for izq, der in producciones
        if len(der) == 1 and der[0] in V
    }
    cierre = set(unitarias)
    cambio = True
    while cambio:
        cambio = False
        nuevos = {
            (a, c)
            for (a, b1) in cierre
            for (b2, c) in unitarias
            if b1 == b2 and (a, c) not in cierre
        }
        if nuevos:
            cierre |= nuevos
            cambio = True
    return cierre


def ciclos(producciones=PRODUCCIONES, V=NO_TERMINALES) -> list[str]:
    return [a for (a, b) in pares_unitarios(producciones, V) if a == b]


class _EspecificacionGLCRelacional:
    """Especificacion PLY de las 28 producciones de G_rel (sin tabla precedence)."""

    tokens = tuple(TOKEN_DE.values())
    start = 'ExpB'

    def p_ExpB_or(self, p):
        'ExpB : ExpB OR TermB'
        p[0] = ('or', p[1], p[3])

    def p_ExpB_TermB(self, p):
        'ExpB : TermB'
        p[0] = p[1]

    def p_TermB_and(self, p):
        'TermB : TermB AND FactB'
        p[0] = ('and', p[1], p[3])

    def p_TermB_FactB(self, p):
        'TermB : FactB'
        p[0] = p[1]

    def p_FactB_not(self, p):
        'FactB : NOT FactB'
        p[0] = ('not', p[2])

    def p_FactB_paren(self, p):
        'FactB : LPAREN ExpB RPAREN'
        p[0] = p[2]

    def p_FactB_true(self, p):
        'FactB : TRUE'
        p[0] = ('const', True)

    def p_FactB_false(self, p):
        'FactB : FALSE'
        p[0] = ('const', False)

    def p_FactB_exprel(self, p):
        'FactB : ExpRel'
        p[0] = p[1]

    def p_ExpRel(self, p):
        'ExpRel : ExpA OpRel ExpA'
        p[0] = ('rel', p[2], p[1], p[3])

    def p_OpRel(self, p):
        '''OpRel : LE
                 | GE
                 | EQ
                 | NE
                 | LT
                 | GT'''
        p[0] = p[1]

    def p_ExpA_plus(self, p):
        'ExpA : ExpA PLUS TermA'
        p[0] = ('+', p[1], p[3])

    def p_ExpA_minus(self, p):
        'ExpA : ExpA MINUS TermA'
        p[0] = ('-', p[1], p[3])

    def p_ExpA_TermA(self, p):
        'ExpA : TermA'
        p[0] = p[1]

    def p_TermA_times(self, p):
        'TermA : TermA TIMES FactA'
        p[0] = ('*', p[1], p[3])

    def p_TermA_divide(self, p):
        'TermA : TermA DIVIDE FactA'
        p[0] = ('/', p[1], p[3])

    def p_TermA_implicita_id(self, p):
        'TermA : NUMBER ID'
        p[0] = ('*impl', ('num', p[1]), ('var', p[2]))

    def p_TermA_implicita_paren(self, p):
        'TermA : NUMBER LPAREN ExpA RPAREN'
        p[0] = ('*impl', ('num', p[1]), p[3])

    def p_TermA_FactA(self, p):
        'TermA : FactA'
        p[0] = p[1]

    def p_FactA_uminus(self, p):
        'FactA : MINUS FactA'
        p[0] = ('uminus', p[2])

    def p_FactA_paren(self, p):
        'FactA : LPAREN ExpA RPAREN'
        p[0] = p[2]

    def p_FactA_number(self, p):
        'FactA : NUMBER'
        p[0] = ('num', p[1])

    def p_FactA_id(self, p):
        'FactA : ID'
        p[0] = ('var', p[1])

    def p_error(self, p):
        raise SyntaxError(f"Error sintactico en token {p!r}")


def construir_lalr_relacional(directorio: str = AQUI) -> dict[str, Any]:
    archivo_debug = os.path.join(directorio, 'parser_relacional.out')
    log = yacc.PlyLogger(open(os.devnull, 'w'))
    spec = _EspecificacionGLCRelacional()
    parser = yacc.yacc(
        module=spec,
        write_tables=False,
        debugfile=archivo_debug,
        errorlog=log,
    )
    with open(archivo_debug, encoding='utf-8') as f:
        texto = f.read()

    sr = len(re.findall(r'shift/reduce conflict', texto))
    rr = len(re.findall(r'reduce/reduce conflict', texto))
    estados = len(re.findall(r'^state \d+$', texto, re.M))
    return {
        'parser': parser,
        'sr': sr,
        'rr': rr,
        'estados': estados,
        'archivo_debug': archivo_debug,
        'texto_debug': texto,
    }


def analizar_expresion_relacional(texto: str, parser=None) -> Any:
    if parser is None:
        parser = construir_lalr_relacional()['parser']
    lx = build_lexer()
    return parser.parse(texto, lexer=lx)


if __name__ == '__main__':
    info = construir_lalr_relacional(AQUI)
    print(f"GLC bien formada: {verificar_bien_formada() == []}")
    print(f"Productivos: {set(productivos()[-1]) == set(NO_TERMINALES)}")
    print(f"Alcanzables: {set(alcanzables()[-1]) == set(NO_TERMINALES) | set(TERMINALES)}")
    print(f"Ciclos: {ciclos()}")
    print(f"Estados LALR(1): {info['estados']}, SR={info['sr']}, RR={info['rr']}")
    ej = analizar_expresion_relacional("(3X+5Y) <= X/(3-Z)", info['parser'])
    print(f"AST de '(3X+5Y) <= X/(3-Z)': {ej}")
