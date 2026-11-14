"""
Pruebas del Numeral 2: las 3 expresiones, sus derivaciones y arboles.

Usa el script docs/numeral2/derivaciones.py (Integrante 5).
"""

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA = os.path.join(RAIZ, 'docs', 'numeral2', 'derivaciones.py')

_spec = importlib.util.spec_from_file_location('derivaciones_numeral2', RUTA)
n2 = importlib.util.module_from_spec(_spec)
sys.modules['derivaciones_numeral2'] = n2
_spec.loader.exec_module(n2)

glc = n2.glc
from boollang.evaluador import evaluar  # noqa: E402


def _aplicar(forma, prod):
    """Aplica una produccion al no terminal mas a la izquierda de ``forma``."""
    i = next(k for k, s in enumerate(forma) if s in glc.NO_TERMINALES)
    izq, der = prod
    assert forma[i] == izq, f'el no terminal mas a la izquierda es {forma[i]}, no {izq}'
    return forma[:i] + list(der) + forma[i + 1:]


PROD_DE = {f'P{i}': p for i, p in enumerate(glc.PRODUCCIONES, start=1)}


def _verificar_derivacion(pasos):
    forma = ['ExpB']
    assert pasos[0] == (forma, None)
    for siguiente, prod in pasos[1:]:
        forma = _aplicar(forma, PROD_DE[prod])
        assert forma == siguiente
    return forma


# --- E1 y E2: validas ------------------------------------------------------

def test_dos_validas_una_invalida():
    assert set(n2.EXPRESIONES) == {'E1', 'E2', 'E3'}
    assert n2.VALIDAS == ('E1', 'E2')


def test_validas_sin_errores_lexicos():
    for nombre in n2.VALIDAS:
        _, errores = n2.tokenize(n2.EXPRESIONES[nombre])
        assert errores == []


def test_derivaciones_son_mas_a_la_izquierda_y_producen_la_cadena():
    for nombre in n2.VALIDAS:
        cadena = n2.EXPRESIONES[nombre]
        pasos = n2.derivacion_izquierda(n2.arbol_de(cadena))
        assert _verificar_derivacion(pasos) == n2.terminales_de(cadena)


def test_numero_de_pasos():
    # un paso por cada nodo interno del arbol
    assert len(n2.derivacion_izquierda(n2.arbol_de(n2.E1))) - 1 == 15
    assert len(n2.derivacion_izquierda(n2.arbol_de(n2.E2))) - 1 == 30


def test_usan_las_ocho_producciones():
    for nombre in n2.VALIDAS:
        pasos = n2.derivacion_izquierda(n2.arbol_de(n2.EXPRESIONES[nombre]))
        assert all(v > 0 for v in n2.contar_pasos(pasos).values()), nombre


def test_arbol_unico():
    for nombre in n2.VALIDAS:
        assert glc.contar_arboles(tuple(n2.terminales_de(n2.EXPRESIONES[nombre]))) == 1


def test_valores_con_el_evaluador_del_proyecto():
    for nombre in n2.VALIDAS:
        ast = n2.a_ast(n2.arbol_de(n2.EXPRESIONES[nombre]))
        assert evaluar(ast) is n2.VALOR_ESPERADO[nombre]
        assert glc.evaluar(n2.arbol_de(n2.EXPRESIONES[nombre])) is n2.VALOR_ESPERADO[nombre]


def test_precedencia_en_e1():
    # E1 = (not (true and false)) or (false and (not false))
    ast = n2.a_ast(n2.arbol_de(n2.E1))
    assert type(ast).__name__ == 'Disyuncion'
    assert type(ast.izq).__name__ == 'Negacion'
    assert type(ast.der).__name__ == 'Conjuncion'


def test_asociatividad_izquierda_en_e2():
    # E2 = ((A and B) and C): la raiz es un and cuyo hijo izquierdo es otro and
    ast = n2.a_ast(n2.arbol_de(n2.E2))
    assert type(ast).__name__ == 'Conjuncion'
    assert type(ast.izq).__name__ == 'Conjuncion'
    assert type(ast.der).__name__ == 'Negacion'


# --- E3: invalida ----------------------------------------------------------

def test_e3_es_lexicamente_correcta():
    _, errores = n2.tokenize(n2.E3)
    assert errores == []


def test_e3_se_bloquea_en_not_or():
    b = n2.bloqueo_e3()
    assert b['prefijo'] == n2.PREFIJO_E3
    assert b['token'] == n2.TOKEN_BLOQUEO_E3
    assert b['columna'] == n2.COLUMNA_BLOQUEO_E3
    assert b['mensaje_parser'] == "token inesperado 'or' (col 29)"


def test_e3_argumento_formal():
    b = n2.bloqueo_e3()
    assert 'or' not in b['primeros_factb']
    assert 'not' not in b['ultimos_expb']
    assert glc.contar_arboles(tuple(b['terminales'])) == 0


def test_e3_prefijo_viable():
    pasos = n2.derivacion_prefijo_e3()
    forma = _verificar_derivacion(pasos)
    assert forma == list(n2.PREFIJO_E3) + ['FactB']


def test_informe_coincide_con_salida_guardada():
    with open(os.path.join(RAIZ, 'docs', 'numeral2', 'salida_numeral2.txt'), encoding='utf-8') as f:
        assert f.read() == n2.informe()


class TestNumeral2RelacionalTarea37:
    """Verificacion formal de derivaciones relacionales (Tarea 37)."""

    def test_r1_enunciado_23_pasos(self):
        from docs.numeral2.derivaciones_relacionales import (
            ENTORNO_PRUEBA,
            R1,
            arbol_concreto_de,
            derivacion_izquierda_rel,
            terminales_rel_de,
        )
        from boollang.evaluador import evaluar
        from boollang.parser import parsear_programa

        pasos = derivacion_izquierda_rel(arbol_concreto_de(R1))
        assert len(pasos) - 1 == 23
        assert pasos[-1][0] == terminales_rel_de(R1)
        prog = parsear_programa(R1)
        assert evaluar(prog.sentencias[0].arbol, ENTORNO_PRUEBA) is False

    def test_r2_compuesta_45_pasos(self):
        from docs.numeral2.derivaciones_relacionales import (
            ENTORNO_PRUEBA,
            R2,
            arbol_concreto_de,
            derivacion_izquierda_rel,
            terminales_rel_de,
        )
        from boollang.evaluador import evaluar
        from boollang.parser import parsear_programa

        pasos = derivacion_izquierda_rel(arbol_concreto_de(R2))
        assert len(pasos) - 1 == 45
        assert pasos[-1][0] == terminales_rel_de(R2)
        prog = parsear_programa(R2)
        assert evaluar(prog.sentencias[0].arbol, ENTORNO_PRUEBA) is True

    def test_r3_bloqueo_sintactico_doble_relacional(self):
        from docs.numeral2.derivaciones_relacionales import verificar_bloqueo_r3

        info = verificar_bloqueo_r3()
        assert info["error"] is not None
        assert info["le_en_primeros_expa"] is False
        assert "col 12" in info["error"]
        assert "'<='" in info["error"]
