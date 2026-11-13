"""
Numeral 1 - Verificacion formal de la gramatica de la Figura 3 (Tarea 36).

Este script comprueba de forma automatica cada una de las propiedades que se
demuestran en ``verificacion_glc.md``:

    1. G es una gramatica libre de contexto (GLC) bien formada.
    2. Todos los simbolos son productivos (generan alguna cadena terminal).
    3. Todos los simbolos son alcanzables desde el simbolo inicial.
    4. No hay producciones epsilon (ni no terminales anulables).
    5. No hay ciclos (derivaciones A =>+ A).
    6. No es ambigua:
         a) la tabla LALR(1) que construye ply.yacc tiene 0 conflictos
            (toda gramatica LR(k) es no ambigua), y
         b) conteo exhaustivo de arboles de derivacion: toda cadena de
            longitud <= N tiene exactamente 0 o 1 arbol.
    7. Es funcionalmente completa: las 16 funciones booleanas binarias se
       expresan con cadenas de L(G) y se evaluan correctamente.

Ademas regenera la evidencia ``parser.out`` (tabla LALR(1) de PLY) en esta
misma carpeta y guarda el informe en ``salida_verificacion.txt``.

Uso (desde la raiz del repositorio):

    python docs/numeral1/verificar_glc.py            # N = 7 por defecto
    python docs/numeral1/verificar_glc.py --max-len 8
"""

import argparse
import io
import itertools
import os
import re
import sys
from functools import lru_cache

import ply.yacc as yacc

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))

# ---------------------------------------------------------------------------
# G = (V, Sigma, P, S)  --  Figura 3, transcrita tal cual (8 producciones)
# ---------------------------------------------------------------------------

NO_TERMINALES = ('ExpB', 'TermB', 'FactB')
TERMINALES = ('or', 'and', 'not', '(', ')', 'true', 'false')
INICIAL = 'ExpB'

PRODUCCIONES = (
    ('ExpB', ('ExpB', 'or', 'TermB')),      # P1
    ('ExpB', ('TermB',)),                   # P2
    ('TermB', ('TermB', 'and', 'FactB')),   # P3
    ('TermB', ('FactB',)),                  # P4
    ('FactB', ('not', 'FactB')),            # P5
    ('FactB', ('(', 'ExpB', ')')),          # P6
    ('FactB', ('true',)),                   # P7
    ('FactB', ('false',)),                  # P8
)

# Gramatica ambigua "ingenua" usada SOLO como contraejemplo (seccion 6).
PRODUCCIONES_AMBIGUAS = (
    ('E', ('E', 'or', 'E')),
    ('E', ('E', 'and', 'E')),
    ('E', ('not', 'E')),
    ('E', ('(', 'E', ')')),
    ('E', ('true',)),
    ('E', ('false',)),
)

# Correspondencia terminal de la gramatica -> token del lexer (acuerdo tecnico).
TOKEN_DE = {
    'true': 'TRUE',
    'false': 'FALSE',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
    '(': 'LPAREN',
    ')': 'RPAREN',
}
TERMINAL_DE = {v: k for k, v in TOKEN_DE.items()}


def _fmt(simbolos):
    return ' '.join(simbolos) if simbolos else 'ε'


def produccion_str(prod):
    izq, der = prod
    return f'{izq} -> {_fmt(der)}'


# ---------------------------------------------------------------------------
# 1. GLC bien formada
# ---------------------------------------------------------------------------

def verificar_bien_formada(producciones=PRODUCCIONES, V=NO_TERMINALES,
                           T=TERMINALES, S=INICIAL):
    """Devuelve la lista de violaciones (vacia si G esta bien formada)."""
    problemas = []
    if set(V) & set(T):
        problemas.append(f'V y Sigma no son disjuntos: {set(V) & set(T)}')
    if S not in V:
        problemas.append(f'El simbolo inicial {S} no pertenece a V')
    for izq, der in producciones:
        if izq not in V:
            problemas.append(f'Lado izquierdo {izq!r} no es un no terminal')
        for s in der:
            if s not in V and s not in T:
                problemas.append(f'Simbolo {s!r} en {izq} no esta en V ∪ Sigma')
    for A in V:
        if not any(izq == A for izq, _ in producciones):
            problemas.append(f'{A} no tiene producciones')
    return problemas


# ---------------------------------------------------------------------------
# 2-3. Productivos y alcanzables (algoritmos de punto fijo)
# ---------------------------------------------------------------------------

def productivos(producciones=PRODUCCIONES, T=TERMINALES):
    """Iteraciones del algoritmo de simbolos productivos.

    Prod_0 = {}; Prod_{i+1} = Prod_i ∪ {A | A -> α, α ∈ (Sigma ∪ Prod_i)*}.
    Devuelve la lista de conjuntos Prod_1, Prod_2, ... hasta el punto fijo.
    """
    actual, pasos = set(), []
    while True:
        nuevo = set(actual)
        for izq, der in producciones:
            if all(s in T or s in actual for s in der):
                nuevo.add(izq)
        if nuevo == actual:
            return pasos
        pasos.append(frozenset(nuevo))
        actual = nuevo


def alcanzables(producciones=PRODUCCIONES, S=INICIAL):
    """Iteraciones del algoritmo de simbolos alcanzables desde S."""
    actual = {S}
    pasos = [frozenset(actual)]
    while True:
        nuevo = set(actual)
        for izq, der in producciones:
            if izq in actual:
                nuevo.update(der)
        if nuevo == actual:
            return pasos
        pasos.append(frozenset(nuevo))
        actual = nuevo


# ---------------------------------------------------------------------------
# 4-5. Producciones epsilon, anulables y ciclos
# ---------------------------------------------------------------------------

def producciones_epsilon(producciones=PRODUCCIONES):
    return [p for p in producciones if len(p[1]) == 0]


def anulables(producciones=PRODUCCIONES):
    nulos = set()
    while True:
        nuevo = set(nulos)
        for izq, der in producciones:
            if all(s in nulos for s in der):
                nuevo.add(izq)
        if nuevo == nulos:
            return nulos
        nulos = nuevo


def pares_unitarios(producciones=PRODUCCIONES, V=NO_TERMINALES):
    """Cierre transitivo de las producciones unitarias A -> B.

    Devuelve el conjunto de pares (A, B) con A =>+ B usando solo
    producciones unitarias. Como G no tiene producciones epsilon, una
    derivacion A =>+ A (ciclo) solo puede ocurrir a traves de ellas.
    """
    pares = {(izq, der[0]) for izq, der in producciones
             if len(der) == 1 and der[0] in V}
    while True:
        nuevo = set(pares)
        for (a, b) in pares:
            for (c, d) in pares:
                if b == c:
                    nuevo.add((a, d))
        if nuevo == pares:
            return pares
        pares = nuevo


def ciclos(producciones=PRODUCCIONES, V=NO_TERMINALES):
    return sorted(a for (a, b) in pares_unitarios(producciones, V) if a == b)


# ---------------------------------------------------------------------------
# Conjuntos PRIMERO / SIGUIENTE (apoyan la discusion LALR(1))
# ---------------------------------------------------------------------------

def primeros(producciones=PRODUCCIONES, V=NO_TERMINALES):
    prim = {A: set() for A in V}
    cambio = True
    while cambio:
        cambio = False
        for izq, der in producciones:
            s = der[0]  # no hay producciones epsilon
            agregar = prim[s] if s in V else {s}
            if not agregar <= prim[izq]:
                prim[izq] |= agregar
                cambio = True
    return prim


def siguientes(producciones=PRODUCCIONES, V=NO_TERMINALES, S=INICIAL):
    prim = primeros(producciones, V)
    sig = {A: set() for A in V}
    sig[S].add('$')
    cambio = True
    while cambio:
        cambio = False
        for izq, der in producciones:
            for i, s in enumerate(der):
                if s not in V:
                    continue
                if i + 1 < len(der):
                    t = der[i + 1]
                    agregar = prim[t] if t in V else {t}
                else:
                    agregar = sig[izq]
                if not agregar <= sig[s]:
                    sig[s] |= agregar
                    cambio = True
    return sig


# ---------------------------------------------------------------------------
# 6b. Conteo de arboles de derivacion (prueba exhaustiva de no ambiguedad)
# ---------------------------------------------------------------------------

def contar_arboles(cadena, producciones=PRODUCCIONES, simbolo=INICIAL):
    """Numero de arboles de derivacion distintos de ``cadena`` desde ``simbolo``.

    ``cadena`` es una secuencia de terminales. Termina porque la gramatica no
    tiene producciones epsilon ni ciclos: cada llamada recursiva reduce el
    tramo [i, j) o desciende en la cadena unitaria ExpB -> TermB -> FactB.
    """
    w = tuple(cadena)
    lados = {}
    for izq, der in producciones:
        lados.setdefault(izq, []).append(der)

    @lru_cache(maxsize=None)
    def cuenta(sim, i, j):
        if sim not in lados:  # terminal
            return 1 if j == i + 1 and w[i] == sim else 0
        return sum(cuenta_seq(der, i, j) for der in lados[sim])

    @lru_cache(maxsize=None)
    def cuenta_seq(der, i, j):
        if not der:
            return 1 if i == j else 0
        primero, resto = der[0], der[1:]
        total = 0
        # cada simbolo cubre al menos un terminal (no hay epsilon)
        for k in range(i + 1, j - len(resto) + 1):
            c = cuenta(primero, i, k)
            if c:
                total += c * cuenta_seq(resto, k, j)
        return total

    if not w:
        return 0
    return cuenta(simbolo, 0, len(w))


def verificar_no_ambiguedad_exhaustiva(max_len=7):
    """Recorre TODAS las cadenas de Sigma^n (1 <= n <= max_len).

    Devuelve (cadenas_revisadas, por_longitud, contraejemplos) donde
    ``por_longitud[n]`` es el numero de cadenas de longitud n en L(G) y
    ``contraejemplos`` lista las cadenas con mas de un arbol (debe ser vacia).
    """
    revisadas, por_longitud, malas = 0, {}, []
    for n in range(1, max_len + 1):
        en_lenguaje = 0
        for w in itertools.product(TERMINALES, repeat=n):
            revisadas += 1
            # poda trivial: toda cadena de L(G) empieza por not ( true false
            # y termina por ) true false; las demas tienen 0 arboles.
            if w[0] in ('or', 'and', ')') or w[-1] in ('or', 'and', 'not', '('):
                continue
            k = contar_arboles(w)
            if k >= 1:
                en_lenguaje += 1
            if k > 1:
                malas.append((' '.join(w), k))
        por_longitud[n] = en_lenguaje
    return revisadas, por_longitud, malas


# ---------------------------------------------------------------------------
# 6a. Construccion LALR(1) con ply.yacc y evidencia parser.out
# ---------------------------------------------------------------------------

class ReglasFigura3:
    """Las 8 reglas de la Figura 3 transcritas tal cual para ply.yacc.

    Sin tabla ``precedence``: la precedencia y la asociatividad deben salir
    de la propia estratificacion ExpB > TermB > FactB. Las acciones construyen
    el arbol de derivacion concreto (nodo, hijos) para poder mostrarlo.
    """

    tokens = ('TRUE', 'FALSE', 'AND', 'OR', 'NOT', 'LPAREN', 'RPAREN')
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

    def p_error(self, p):
        if p is None:
            raise SyntaxError('fin de entrada inesperado')
        raise SyntaxError(f'token inesperado {p.value!r} (col {p.lexpos + 1})')


class _RegistroPly:
    """errorlog para ply.yacc que guarda los avisos en lugar de imprimirlos."""

    def __init__(self):
        self.avisos, self.errores = [], []

    def debug(self, msg, *args, **kw):
        pass

    info = debug

    def warning(self, msg, *args, **kw):
        self.avisos.append(msg % args)

    def error(self, msg, *args, **kw):
        self.errores.append(msg % args)

    critical = error


def construir_lalr(directorio=AQUI, archivo='parser.out', reglas=None):
    """Construye el parser LALR(1) y escribe ``parser.out`` en ``directorio``.

    ``reglas`` es el objeto con ``tokens`` y funciones ``p_`` (por defecto,
    la Figura 3). Devuelve un dict con el parser, el numero de estados y los
    conflictos shift/reduce y reduce/reduce detectados por PLY.
    """
    registro = _RegistroPly()
    parser = yacc.yacc(module=reglas or ReglasFigura3(), method='LALR', debug=True,
                       debugfile=archivo, outputdir=directorio,
                       write_tables=False, errorlog=registro)
    ruta = os.path.join(directorio, archivo)
    with open(ruta, encoding='utf-8', errors='replace') as f:
        texto = f.read()
    estados = len(re.findall(r'^state \d+$', texto, flags=re.M))
    sr = sum(int(m) for m in re.findall(r'(\d+) shift/reduce conflicts?', ' '.join(registro.avisos)))
    rr = sum(int(m) for m in re.findall(r'(\d+) reduce/reduce conflicts?', ' '.join(registro.avisos)))
    marcas = len(re.findall(r'conflict', texto))  # PLY marca cada conflicto con "! ... conflict"
    return {
        'parser': parser,
        'ruta': ruta,
        'estados': estados,
        'sr': sr,
        'rr': rr,
        'marcas_conflicto_en_parser_out': marcas,
        'avisos': registro.avisos,
        'errores': registro.errores,
    }


def tokens_de(cadena):
    """Tokeniza con el lexer del Integrante 1 (boollang.lexer)."""
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    from boollang.lexer import tokenize
    toks, errores = tokenize(cadena)
    if errores:
        raise ValueError('; '.join(str(e) for e in errores))
    return toks


class _LexerLista:
    """Adaptador minimo para entregarle a ply.yacc una lista de tokens."""

    def __init__(self, toks):
        self._it = iter(toks)

    def token(self):
        return next(self._it, None)


def analizar(cadena, parser=None):
    """Devuelve el arbol de derivacion concreto de ``cadena`` (Figura 3)."""
    parser = parser or construir_lalr()['parser']
    toks = [t for t in tokens_de(cadena) if t.type != 'NEWLINE']
    return parser.parse(lexer=_LexerLista(toks))


def dibujar(arbol, prefijo='', ultimo=True, raiz=True):
    """Dibuja el arbol de derivacion en texto."""
    lineas = []
    etiqueta = arbol[0] if isinstance(arbol, tuple) else arbol
    if raiz:
        lineas.append(etiqueta)
        nuevo_prefijo = ''
    else:
        lineas.append(prefijo + ('└── ' if ultimo else '├── ') + etiqueta)
        nuevo_prefijo = prefijo + ('    ' if ultimo else '│   ')
    if isinstance(arbol, tuple):
        hijos = arbol[1]
        for i, h in enumerate(hijos):
            lineas.extend(dibujar(h, nuevo_prefijo, i == len(hijos) - 1, False))
    return lineas if not raiz else '\n'.join(lineas)


def evaluar(arbol):
    """Semantica de referencia sobre el arbol concreto (solo para el script)."""
    if isinstance(arbol, str):
        raise ValueError(arbol)
    _, h = arbol
    if len(h) == 1:
        return h[0] == 'true' if isinstance(h[0], str) else evaluar(h[0])
    if h[0] == 'not':
        return not evaluar(h[1])
    if h[0] == '(':
        return evaluar(h[1])
    if h[1] == 'and':
        return evaluar(h[0]) and evaluar(h[2])
    return evaluar(h[0]) or evaluar(h[2])


# ---------------------------------------------------------------------------
# 7. Completitud funcional
# ---------------------------------------------------------------------------

def plantilla_fnd(tabla):
    """Forma normal disyuntiva de una funcion booleana binaria f(x, y).

    ``tabla`` es una tupla de 4 bools: f(F,F), f(F,T), f(T,F), f(T,T).
    Devuelve una plantilla con los marcadores {x} y {y} que siempre es una
    cadena de L(G) al sustituirlos por true/false.
    """
    filas = [(False, False), (False, True), (True, False), (True, True)]
    minterminos = []
    for (a, b), valor in zip(filas, tabla):
        if valor:
            lx = '{x}' if a else 'not {x}'
            ly = '{y}' if b else 'not {y}'
            minterminos.append(f'{lx} and {ly}')
    if not minterminos:
        return '{x} and not {x}'  # contradiccion
    return ' or '.join(minterminos)


def verificar_completitud_funcional(parser=None):
    """Comprueba las 16 funciones booleanas binarias.

    Devuelve una lista de (tabla, plantilla, ok).
    """
    parser = parser or construir_lalr()['parser']
    lit = {True: 'true', False: 'false'}
    resultados = []
    for tabla in itertools.product((False, True), repeat=4):
        plantilla = plantilla_fnd(tabla)
        ok = True
        for (a, b), esperado in zip(itertools.product((False, True), repeat=2), tabla):
            cadena = plantilla.format(x=lit[a], y=lit[b])
            arbol = analizar(cadena, parser)
            w = [TERMINAL_DE[t.type] for t in tokens_de(cadena) if t.type != 'NEWLINE']
            if evaluar(arbol) != esperado or contar_arboles(w) != 1:
                ok = False
        resultados.append((tabla, plantilla, ok))
    return resultados


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------

def _conj(s):
    return '{' + ', '.join(sorted(s, key=lambda x: (x not in NO_TERMINALES, x))) + '}'


def informe(max_len=7):
    out = io.StringIO()
    p = lambda *a: print(*a, file=out)  # noqa: E731

    p('=' * 72)
    p(' Numeral 1 - Verificacion de la GLC de la Figura 3 (boollang)')
    p('=' * 72)
    p(f'V = {_conj(NO_TERMINALES)}')
    p(f'Sigma = {_conj(TERMINALES)}')
    p(f'S = {INICIAL}')
    p('P:')
    for i, prod in enumerate(PRODUCCIONES, 1):
        p(f'  P{i}: {produccion_str(prod)}')

    p('\n[1] GLC bien formada')
    prob = verificar_bien_formada()
    p('  OK: todo lado izquierdo es un unico no terminal y todo lado derecho'
      ' esta en (V ∪ Sigma)+' if not prob else '  FALLA: ' + '; '.join(prob))

    p('\n[2] Simbolos productivos')
    pasos = productivos()
    for i, s in enumerate(pasos, 1):
        p(f'  Prod_{i} = {_conj(s)}')
    p(f'  Punto fijo: {_conj(pasos[-1])} == V  ->  '
      f'{"OK" if set(pasos[-1]) == set(NO_TERMINALES) else "FALLA"}')

    p('\n[3] Simbolos alcanzables')
    pasos = alcanzables()
    for i, s in enumerate(pasos):
        p(f'  Alc_{i} = {_conj(s)}')
    todos = set(NO_TERMINALES) | set(TERMINALES)
    p(f'  Punto fijo == V ∪ Sigma  ->  {"OK" if set(pasos[-1]) == todos else "FALLA"}')

    p('\n[4] Producciones epsilon')
    eps = producciones_epsilon()
    p(f'  Producciones A -> ε: {len(eps)}   Anulables: {_conj(anulables())}  ->  '
      f'{"OK" if not eps and not anulables() else "FALLA"}')

    p('\n[5] Ciclos (A =>+ A)')
    unit = sorted(pares_unitarios())
    p(f'  Pares unitarios (A =>+ B): {", ".join(f"({a},{b})" for a, b in unit)}')
    c = ciclos()
    p(f'  Ciclos: {c if c else "ninguno"}  ->  {"OK" if not c else "FALLA"}')

    p('\n[*] PRIMERO / SIGUIENTE')
    prim, sig = primeros(), siguientes()
    for A in NO_TERMINALES:
        p(f'  PRIMERO({A}) = {_conj(prim[A])}   SIGUIENTE({A}) = {_conj(sig[A])}')

    p('\n[6a] Tabla LALR(1) con ply.yacc (sin tabla precedence)')
    r = construir_lalr()
    p(f'  Archivo: {os.path.relpath(r["ruta"], RAIZ).replace(os.sep, "/")}')
    p(f'  Estados LALR(1): {r["estados"]}')
    p(f'  Conflictos shift/reduce: {r["sr"]}')
    p(f'  Conflictos reduce/reduce: {r["rr"]}')
    p(f'  Lineas "conflict" en parser.out: {r["marcas_conflicto_en_parser_out"]}')
    ok = r['sr'] == r['rr'] == r['marcas_conflicto_en_parser_out'] == 0 and not r['errores']
    p(f'  ->  {"OK: G es LALR(1), por tanto no ambigua" if ok else "FALLA"}')

    p(f'\n[6b] Conteo exhaustivo de arboles, todas las cadenas de Sigma^n, n <= {max_len}')
    revisadas, por_long, malas = verificar_no_ambiguedad_exhaustiva(max_len)
    p(f'  Cadenas revisadas: {revisadas}')
    p('  Cadenas de L(G) por longitud: ' +
      ', '.join(f'n={n}: {k}' for n, k in por_long.items()))
    p(f'  Cadenas con 2 o mas arboles: {len(malas)}  ->  {"OK" if not malas else "FALLA " + str(malas[:5])}')
    ej = 'true or false and false'.split()
    p(f'  Contraejemplo con la gramatica ingenua E -> E or E | E and E | ...:')
    p(f'    arboles("{" ".join(ej)}") = {contar_arboles(ej, PRODUCCIONES_AMBIGUAS, "E")}'
      f' en la ingenua vs {contar_arboles(ej)} en la Figura 3')

    p('\n[6c] Arboles unicos: precedencia not > and > or y asociatividad izquierda')
    for cadena in ('true or false and false', 'true and false and true', 'not true and false'):
        arbol = r['parser'].parse(lexer=_LexerLista(
            [t for t in tokens_de(cadena) if t.type != 'NEWLINE']))
        p(f'\n  {cadena}   =>  {str(evaluar(arbol)).lower()}')
        for linea in dibujar(arbol).splitlines():
            p('    ' + linea)

    p('\n[7] Completitud funcional: las 16 funciones booleanas binarias f(x, y)')
    res = verificar_completitud_funcional(r['parser'])
    for tabla, plantilla, ok in res:
        bits = ''.join('1' if v else '0' for v in tabla)
        p(f'  f={bits}  {"OK " if ok else "MAL"}  {plantilla}')
    p(f'  ->  {"OK: 16/16 funciones expresables en L(G)" if all(o for *_, o in res) else "FALLA"}')
    return out.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('--max-len', type=int, default=7,
                    help='longitud maxima para el conteo exhaustivo de arboles')
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    texto = informe(args.max_len)
    print(texto)
    with open(os.path.join(AQUI, 'salida_verificacion.txt'), 'w', encoding='utf-8') as f:
        f.write(texto)


if __name__ == '__main__':
    main()
