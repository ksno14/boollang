"""
Numeral 2 - Tres expresiones, derivaciones mas a la izquierda y arboles (Tarea 36).

Integrante 5. Genera de forma automatica la evidencia que se explica en
``derivaciones.md``:

    E1, E2 (validas):  derivacion mas a la izquierda paso a paso, arbol de
                       derivacion concreto (Figura 3), arbol anotado con el
                       valor de cada subexpresion y AST de ``boollang.nodos``
                       evaluado con ``boollang.evaluador`` (Integrante 4).
    E3 (invalida):     derivacion mas a la izquierda del prefijo viable mas
                       largo, token exacto donde se bloquea (``not or``),
                       columna, y comprobacion con el parser LALR(1).

No modifica el trabajo de los demas integrantes: reutiliza la gramatica, el
parser LALR(1) y el dibujo de arboles de ``docs/numeral1/verificar_glc.py``
(Integrante 2) y el lexer ``boollang.lexer`` (Integrante 1).

Uso (desde la raiz del repositorio):

    python docs/numeral2/derivaciones.py      # imprime y guarda salida_numeral2.txt
"""

import importlib.util
import io
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

_RUTA_GLC = os.path.join(RAIZ, 'docs', 'numeral1', 'verificar_glc.py')
if 'verificar_glc' in sys.modules:
    glc = sys.modules['verificar_glc']
else:
    _spec = importlib.util.spec_from_file_location('verificar_glc', _RUTA_GLC)
    glc = importlib.util.module_from_spec(_spec)
    sys.modules['verificar_glc'] = glc  # ply.yacc busca el modulo en sys.modules
    _spec.loader.exec_module(glc)

from boollang.lexer import find_column, tokenize  # noqa: E402
from boollang.nodos import Conjuncion, Constante, Disyuncion, Negacion  # noqa: E402
from boollang.evaluador import evaluar as evaluar_ast, formatear_booleano  # noqa: E402

# ---------------------------------------------------------------------------
# Las 3 expresiones del Numeral 2 (las mismas lineas L2, L3 y L4 del
# escenario de recuperacion del documento de la Tarea 36).
# ---------------------------------------------------------------------------

E1 = 'not (true and false) or false and not false'
E2 = 'not not (false or true and not false) and (true or false) and not (true and true)'
E3 = '(true or not false) and not or false'

EXPRESIONES = {'E1': E1, 'E2': E2, 'E3': E3}
VALIDAS = ('E1', 'E2')

VALOR_ESPERADO = {'E1': True, 'E2': False}

# Bloqueo esperado de E3: el prefijo viable mas largo y el token que sobra.
PREFIJO_E3 = ('(', 'true', 'or', 'not', 'false', ')', 'and', 'not')
TOKEN_BLOQUEO_E3 = 'or'
COLUMNA_BLOQUEO_E3 = 29

NUMERO_DE = {prod: f'P{i}' for i, prod in enumerate(glc.PRODUCCIONES, start=1)}

_PARSER = None


def parser():
    """Parser LALR(1) de la Figura 3 (construido una sola vez, sin escribir archivos)."""
    global _PARSER
    if _PARSER is None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            _PARSER = glc.construir_lalr(directorio=tmp)['parser']
    return _PARSER


def terminales_de(cadena):
    """Lista de terminales de la gramatica (no tokens) obtenida con el lexer."""
    return [glc.TERMINAL_DE[t.type] for t in glc.tokens_de(cadena) if t.type != 'NEWLINE']


def arbol_de(cadena):
    """Arbol de derivacion concreto (nodo, hijos) producido por ply.yacc."""
    return glc.analizar(cadena, parser())


# ---------------------------------------------------------------------------
# Derivacion mas a la izquierda a partir del arbol (recorrido en preorden)
# ---------------------------------------------------------------------------

def _simbolo(x):
    return x[0] if isinstance(x, tuple) else x


def produccion_de(nodo):
    """Produccion (izq, der) aplicada en un nodo interno del arbol."""
    izq, hijos = nodo
    return (izq, tuple(_simbolo(h) for h in hijos))


def derivacion_izquierda(arbol):
    """Devuelve [(forma_sentencial, 'Pk' que se aplico para llegar a ella)].

    La primera forma es el simbolo inicial (sin produccion). En cada paso se
    reemplaza el no terminal MAS A LA IZQUIERDA por los hijos de su nodo.
    """
    forma = [arbol]
    pasos = [(['ExpB'], None)]
    while True:
        i = next((k for k, x in enumerate(forma) if isinstance(x, tuple)), None)
        if i is None:
            return pasos
        nodo = forma[i]
        forma = forma[:i] + list(nodo[1]) + forma[i + 1:]
        pasos.append(([_simbolo(x) for x in forma], NUMERO_DE[produccion_de(nodo)]))


def formatear_derivacion(pasos):
    lineas = []
    ancho = len(str(len(pasos) - 1))
    for n, (forma, prod) in enumerate(pasos):
        flecha = '   ' if prod is None else '=> '
        etiqueta = ' ' * (ancho + 5) if prod is None else f'{n:>{ancho}}. {prod:<3}'
        lineas.append(f'{etiqueta}{flecha}{" ".join(forma)}')
    return '\n'.join(lineas)


# ---------------------------------------------------------------------------
# Arbol anotado con valores y AST de boollang.nodos (Integrante 4)
# ---------------------------------------------------------------------------

def a_ast(arbol):
    """Convierte el arbol concreto en el AST acordado (Constante, Negacion, ...)."""
    _, h = arbol
    if len(h) == 1:
        return Constante(h[0] == 'true') if isinstance(h[0], str) else a_ast(h[0])
    if h[0] == 'not':
        return Negacion(a_ast(h[1]))
    if h[0] == '(':
        return a_ast(h[1])
    if h[1] == 'and':
        return Conjuncion(a_ast(h[0]), a_ast(h[2]))
    return Disyuncion(a_ast(h[0]), a_ast(h[2]))


def anotar(arbol):
    """Copia del arbol con cada no terminal etiquetado como 'X = valor'."""
    if isinstance(arbol, str):
        return arbol
    etiqueta, hijos = arbol
    valor = formatear_booleano(glc.evaluar(arbol))
    return (f'{etiqueta} = {valor}', [anotar(h) for h in hijos])


def dibujar_ast(nodo, prefijo='', ultimo=True, raiz=True):
    nombre = {Constante: lambda n: formatear_booleano(n.valor),
              Negacion: lambda n: 'not', Conjuncion: lambda n: 'and',
              Disyuncion: lambda n: 'or'}[type(nodo)](nodo)
    hijos = {Constante: (), Negacion: ('op',), Conjuncion: ('izq', 'der'),
             Disyuncion: ('izq', 'der')}[type(nodo)]
    etiqueta = f'{nombre}   [{formatear_booleano(evaluar_ast(nodo))}]'
    if raiz:
        lineas, nuevo = [etiqueta], ''
    else:
        lineas = [prefijo + ('└── ' if ultimo else '├── ') + etiqueta]
        nuevo = prefijo + ('    ' if ultimo else '│   ')
    for i, campo in enumerate(hijos):
        lineas.extend(dibujar_ast(getattr(nodo, campo), nuevo, i == len(hijos) - 1, False))
    return lineas if not raiz else '\n'.join(lineas)


def contar_pasos(pasos):
    """Cuantas veces se uso cada produccion en la derivacion."""
    cuenta = {f'P{i}': 0 for i in range(1, 9)}
    for _, prod in pasos[1:]:
        cuenta[prod] += 1
    return cuenta


# ---------------------------------------------------------------------------
# E3: donde y por que se bloquea
# ---------------------------------------------------------------------------

def ultimos(producciones=glc.PRODUCCIONES, V=glc.NO_TERMINALES):
    """ULTIMOS(X): terminales con los que puede terminar una cadena de L(X)."""
    ult = {A: set() for A in V}
    cambio = True
    while cambio:
        cambio = False
        for izq, der in producciones:
            s = der[-1]  # no hay producciones epsilon
            agregar = ult[s] if s in V else {s}
            if not agregar <= ult[izq]:
                ult[izq] |= agregar
                cambio = True
    return ult


def derivacion_prefijo_e3():
    """Derivacion mas a la izquierda ExpB =>* ( true or not false ) and not FactB.

    Se obtiene derivando una cadena valida que comparte el prefijo de E3 y
    deteniendose en el primer paso cuya forma sentencial es exactamente
    PREFIJO_E3 seguido de un unico FactB pendiente.
    """
    testigo = '(true or not false) and not true'
    objetivo = list(PREFIJO_E3) + ['FactB']
    pasos = derivacion_izquierda(arbol_de(testigo))
    for k, (forma, _) in enumerate(pasos):
        if forma == objetivo:
            return pasos[:k + 1]
    raise AssertionError('no se encontro la forma sentencial del prefijo')


def bloqueo_e3():
    """Analiza E3 con el lexer y el parser LALR(1). Devuelve un dict de evidencia."""
    toks, errores_lexicos = tokenize(E3)
    toks = [t for t in toks if t.type != 'NEWLINE']
    terms = [glc.TERMINAL_DE[t.type] for t in toks]
    # posicion del primer 'or' que sigue inmediatamente a un 'not'
    k = next(i for i in range(1, len(terms)) if terms[i - 1] == 'not' and terms[i] == 'or')
    columna = find_column(E3, toks[k])
    try:
        parser().parse(lexer=glc._LexerLista(toks))
        mensaje = None
    except SyntaxError as e:
        mensaje = str(e)
    prim = glc.primeros()
    ult = ultimos()
    return {
        'errores_lexicos': errores_lexicos,
        'terminales': terms,
        'indice': k,
        'prefijo': tuple(terms[:k]),
        'token': terms[k],
        'columna': columna,
        'mensaje_parser': mensaje,
        'primeros_factb': prim['FactB'],
        'ultimos_expb': ult['ExpB'],
        'ultimos': ult,
    }


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------

def _conj(s):
    return '{' + ', '.join(sorted(s)) + '}'


def informe():
    out = io.StringIO()

    def p(s=''):
        out.write(s + '\n')

    p('=' * 78)
    p(' Numeral 2 - Derivaciones mas a la izquierda y arboles (Integrante 5)')
    p('=' * 78)
    for nombre in VALIDAS:
        cadena = EXPRESIONES[nombre]
        arbol = arbol_de(cadena)
        pasos = derivacion_izquierda(arbol)
        ast = a_ast(arbol)
        p()
        p(f'{nombre} = {cadena}')
        p('-' * 78)
        p(f'Tokens ({len(terminales_de(cadena))}): {" ".join(terminales_de(cadena))}')
        p(f'Arboles de derivacion distintos (Integrante 2): {glc.contar_arboles(tuple(terminales_de(cadena)))}')
        p()
        p(f'Derivacion mas a la izquierda ({len(pasos) - 1} pasos):')
        p(formatear_derivacion(pasos))
        p()
        uso = contar_pasos(pasos)
        p('Producciones usadas: ' + ', '.join(f'{k}x{v}' for k, v in uso.items()))
        p()
        p('Arbol de derivacion (Figura 3):')
        p(glc.dibujar(arbol))
        p()
        p('Arbol anotado con el valor de cada subexpresion:')
        p(glc.dibujar(anotar(arbol)))
        p()
        p('AST (boollang.nodos) evaluado con boollang.evaluador:')
        p(dibujar_ast(ast))
        p()
        p(f'Valor: {formatear_booleano(evaluar_ast(ast))}')

    b = bloqueo_e3()
    p()
    p(f'E3 = {E3}')
    p('-' * 78)
    p(f'Tokens: {" ".join(b["terminales"])}')
    p(f'Errores lexicos: {len(b["errores_lexicos"])} (todas las palabras son reservadas validas)')
    p()
    pasos = derivacion_prefijo_e3()
    p(f'Derivacion mas a la izquierda del prefijo viable ({len(pasos) - 1} pasos):')
    p(formatear_derivacion(pasos))
    p()
    p(f'Prefijo aceptado: {" ".join(b["prefijo"])}')
    p(f'Token de bloqueo: {b["token"]!r} (token #{b["indice"] + 1}, columna {b["columna"]})')
    p(f'PRIMEROS(FactB) = {_conj(b["primeros_factb"])}   ->  {b["token"]!r} no pertenece')
    p(f'ULTIMOS(ExpB)   = {_conj(b["ultimos_expb"])}       ->  "not" no pertenece')
    p(f'Parser LALR(1): SyntaxError: {b["mensaje_parser"]}')
    p(f'Arboles de derivacion de E3: {glc.contar_arboles(tuple(b["terminales"]))}  (E3 no pertenece a L(G))')
    return out.getvalue()


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    texto = informe()
    print(texto)
    with open(os.path.join(AQUI, 'salida_numeral2.txt'), 'w', encoding='utf-8') as f:
        f.write(texto)


if __name__ == '__main__':
    main()
