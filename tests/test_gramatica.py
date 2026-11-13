"""
Pruebas del Numeral 1: verificacion automatica de la GLC de la Figura 3.

Usa el script docs/numeral1/verificar_glc.py (Integrante 2).
"""

import importlib.util
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA = os.path.join(RAIZ, 'docs', 'numeral1', 'verificar_glc.py')

_spec = importlib.util.spec_from_file_location('verificar_glc', RUTA)
glc = importlib.util.module_from_spec(_spec)
sys.modules['verificar_glc'] = glc  # ply.yacc busca el modulo en sys.modules
_spec.loader.exec_module(glc)


@pytest.fixture(scope='module')
def lalr(tmp_path_factory):
    return glc.construir_lalr(directorio=str(tmp_path_factory.mktemp('lalr')))


def test_ocho_producciones_de_la_figura_3():
    assert len(glc.PRODUCCIONES) == 8
    assert {izq for izq, _ in glc.PRODUCCIONES} == set(glc.NO_TERMINALES)


def test_terminales_coinciden_con_tokens_del_lexer():
    from boollang.lexer import tokens, reserved
    assert set(glc.TOKEN_DE.values()) <= set(tokens)
    for palabra in ('true', 'false', 'and', 'or', 'not'):
        assert reserved[palabra] == glc.TOKEN_DE[palabra]


def test_glc_bien_formada():
    assert glc.verificar_bien_formada() == []


def test_todos_los_simbolos_son_productivos():
    assert set(glc.productivos()[-1]) == set(glc.NO_TERMINALES)


def test_todos_los_simbolos_son_alcanzables():
    assert set(glc.alcanzables()[-1]) == set(glc.NO_TERMINALES) | set(glc.TERMINALES)


def test_sin_producciones_epsilon_ni_anulables():
    assert glc.producciones_epsilon() == []
    assert glc.anulables() == set()


def test_sin_ciclos():
    assert glc.ciclos() == []
    assert glc.pares_unitarios() == {
        ('ExpB', 'TermB'), ('TermB', 'FactB'), ('ExpB', 'FactB')}


def test_lalr1_sin_conflictos(lalr):
    assert lalr['errores'] == []
    assert lalr['sr'] == 0
    assert lalr['rr'] == 0
    assert lalr['marcas_conflicto_en_parser_out'] == 0
    assert lalr['estados'] == 15


def test_parser_out_versionado_tiene_cero_conflictos():
    with open(os.path.join(RAIZ, 'docs', 'numeral1', 'parser.out'), encoding='utf-8') as f:
        texto = f.read()
    assert 'Parsing method: LALR' in texto
    assert 'conflict' not in texto


class _Ambigua:
    """Gramatica ingenua E -> E or E | E and E | not E | ( E ) | true | false."""
    tokens = ('TRUE', 'FALSE', 'AND', 'OR', 'NOT', 'LPAREN', 'RPAREN')

    def p_or(self, p):
        'E : E OR E'

    def p_and(self, p):
        'E : E AND E'

    def p_not(self, p):
        'E : NOT E'

    def p_par(self, p):
        'E : LPAREN E RPAREN'

    def p_cte(self, p):
        '''E : TRUE
             | FALSE'''

    def p_error(self, p):
        pass


def test_el_detector_de_conflictos_si_detecta_la_gramatica_ambigua(tmp_path):
    r = glc.construir_lalr(directorio=str(tmp_path), reglas=_Ambigua())
    assert r['sr'] > 0


@pytest.mark.parametrize('cadena, arboles_fig3, arboles_ingenua', [
    ('true or false and false', 1, 2),
    ('true and false and true', 1, 2),
    ('true or false or true', 1, 2),
    ('not true and false', 1, 2),
    ('( true or false ) and false', 1, 1),
    ('not or false', 0, 0),
])
def test_conteo_de_arboles(cadena, arboles_fig3, arboles_ingenua):
    w = cadena.split()
    assert glc.contar_arboles(w) == arboles_fig3
    assert glc.contar_arboles(w, glc.PRODUCCIONES_AMBIGUAS, 'E') == arboles_ingenua


def test_no_ambigua_exhaustivo_hasta_longitud_5():
    _, por_longitud, malas = glc.verificar_no_ambiguedad_exhaustiva(5)
    assert malas == []
    assert por_longitud == {1: 2, 2: 2, 3: 12, 4: 22, 5: 90}


def test_precedencia_and_sobre_or(lalr):
    arbol = glc.analizar('true or false and false', lalr['parser'])
    # la raiz se parte en el 'or': ExpB -> ExpB or TermB
    assert arbol[0] == 'ExpB' and arbol[1][1] == 'or'
    assert glc.evaluar(arbol) is True


def test_asociatividad_izquierda_de_and(lalr):
    arbol = glc.analizar('true and false and true', lalr['parser'])
    term = arbol[1][0]
    # TermB -> TermB and FactB, y el TermB izquierdo contiene 'true and false'
    assert term[1][1] == 'and'
    assert term[1][0][1][1] == 'and'


def test_not_liga_mas_fuerte_que_and(lalr):
    arbol = glc.analizar('not true and false', lalr['parser'])
    term = arbol[1][0]
    assert term[1][1] == 'and'
    assert term[1][0][1][0][1][0] == 'not'


def test_completitud_funcional_16_funciones(lalr):
    resultados = glc.verificar_completitud_funcional(lalr['parser'])
    assert len(resultados) == 16
    assert all(ok for *_, ok in resultados)
