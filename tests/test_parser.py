"""
Pruebas del analizador sintáctico LALR(1) ``boollang.parser`` (Integrante 3).

Cubren:
- la gramática: las 8 reglas de la Figura 3 tal cual, sin ``precedence``,
  las reglas Programa/Sentencia y la tabla LALR(1) sin conflictos;
- la construcción del AST (precedencia y asociatividad), con una comparación
  exhaustiva contra la GLC del Integrante 2, el parser descendente del
  Integrante 6 y la semántica de Python;
- programas con varias sentencias separadas por ``\\n`` o ``;``;
- la recuperación de errores por línea (``error NEWLINE`` / ``error PUNTOYCOMA``);
- la integración con ``boollang.archivo`` y la CLI (archivo ``.out``).
"""

import importlib.util
import itertools
import os
import re
import subprocess
import sys

import pytest

from boollang import (
    Conjuncion,
    Constante,
    Disyuncion,
    Negacion,
    Programa,
    evaluar,
    parsear_expresion,
    procesar_archivo,
    procesar_texto,
)
from boollang.__main__ import main
from boollang.parser import ParserBoollang, parsear_programa

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if 'verificar_glc' in sys.modules:
    glc = sys.modules['verificar_glc']
else:
    _spec = importlib.util.spec_from_file_location(
        'verificar_glc', os.path.join(RAIZ, 'docs', 'numeral1', 'verificar_glc.py'))
    glc = importlib.util.module_from_spec(_spec)
    sys.modules['verificar_glc'] = glc  # ply.yacc busca el modulo en sys.modules
    _spec.loader.exec_module(glc)

T, F = Constante(True), Constante(False)

E1 = 'not (true and false) or false and not false'
E2 = 'not not (false or true and not false) and (true or false) and not (true and true)'
E3 = '(true or not false) and not or false'


def _sentencias(texto):
    return parsear_programa(texto).sentencias


def _resumen(texto):
    """[(linea, texto, arbol o error)] para comparar programas de forma compacta."""
    return [(s.linea, s.texto, s.arbol if s.error is None else s.error)
            for s in _sentencias(texto)]


def _arbol(expresion):
    (sentencia,) = _sentencias(expresion)
    assert sentencia.error is None, sentencia.error
    return sentencia.arbol


def _reglas(parser_out):
    """{numero: 'A -> x y'} de la sección Grammar de un parser.out de PLY."""
    return {int(n): r.strip() for n, r in re.findall(r'^Rule (\d+)\s+(.+)$', parser_out, re.M)}


@pytest.fixture(scope='module')
def tabla(tmp_path_factory):
    ruta = tmp_path_factory.mktemp('lalr') / 'parser.out'
    parser = ParserBoollang(archivo_tabla=ruta)
    return parser, ruta.read_text(encoding='utf-8')


# ---------------------------------------------------------------------------
# Gramática y tabla LALR(1)
# ---------------------------------------------------------------------------

class TestGramatica:
    def test_reglas_1_a_8_son_la_figura_3_tal_cual(self, tabla):
        _, texto = tabla
        with open(os.path.join(RAIZ, 'docs', 'numeral1', 'parser.out'), encoding='utf-8') as f:
            figura3 = _reglas(f.read())
        reglas = _reglas(texto)
        assert {n: reglas[n] for n in range(1, 9)} == {n: figura3[n] for n in range(1, 9)}

    def test_reglas_1_a_8_coinciden_con_las_producciones_del_numeral_1(self, tabla):
        _, texto = tabla
        reglas = _reglas(texto)
        for n, (izq, der) in enumerate(glc.PRODUCCIONES, start=1):
            simbolos = [glc.TOKEN_DE.get(s, s) for s in der]
            assert reglas[n] == f"{izq} -> {' '.join(simbolos)}"

    def test_sin_tabla_precedence(self):
        assert not hasattr(ParserBoollang, 'precedence')
        assert not hasattr(ParserBoollang(), 'precedence')

    def test_reglas_programa_sentencia_y_recuperacion(self, tabla):
        _, texto = tabla
        reglas = _reglas(texto)
        assert reglas[0] == "S' -> Programa"
        assert reglas[9] == "FactB -> ExpRel"
        assert reglas[10] == "ExpRel -> ExpA OpRel ExpA"
        assert reglas[29] == "Asignacion -> ID ASSIGN ExpA"
        assert len(reglas) == 43

    def test_lalr1_sin_conflictos(self, tabla):
        parser, texto = tabla
        assert 'Parsing method: LALR' in texto
        assert parser.conflictos_sr == 0
        assert parser.conflictos_rr == 0
        assert 'conflict' not in texto
        assert parser.avisos == []
        assert parser.estados == len(re.findall(r'^state \d+$', texto, re.M))

    def test_usa_los_tokens_del_lexer(self):
        from boollang.lexer import tokens
        assert ParserBoollang.tokens == tokens


# ---------------------------------------------------------------------------
# Construcción del AST (reglas 1 a 8)
# ---------------------------------------------------------------------------

class TestExpresiones:
    @pytest.mark.parametrize('expresion, esperado', [
        ('true', T),
        ('false', F),
        ('not true', Negacion(T)),
        ('not not false', Negacion(Negacion(F))),
        ('(true)', T),
        ('((false))', F),
        ('true and false', Conjuncion(T, F)),
        ('true or false', Disyuncion(T, F)),
        # and liga más fuerte que or
        ('true or false and false', Disyuncion(T, Conjuncion(F, F))),
        ('true and false or false', Disyuncion(Conjuncion(T, F), F)),
        # asociatividad izquierda
        ('true and false and true', Conjuncion(Conjuncion(T, F), T)),
        ('true or false or true', Disyuncion(Disyuncion(T, F), T)),
        # not solo afecta a su FactB
        ('not true and false', Conjuncion(Negacion(T), F)),
        ('not true or false', Disyuncion(Negacion(T), F)),
        ('not (true and false)', Negacion(Conjuncion(T, F))),
        # los paréntesis cambian la agrupación
        ('(true or false) and false', Conjuncion(Disyuncion(T, F), F)),
        ('true and (false or true)', Conjuncion(T, Disyuncion(F, T))),
    ])
    def test_ast(self, expresion, esperado):
        assert _arbol(expresion) == esperado

    def test_e1_y_e2_del_numeral_2(self):
        e1 = _arbol(E1)
        assert e1 == Disyuncion(
            Negacion(Conjuncion(T, F)),
            Conjuncion(F, Negacion(F)),
        )
        assert evaluar(e1) is True

        e2 = _arbol(E2)
        assert e2 == Conjuncion(
            Conjuncion(
                Negacion(Negacion(Disyuncion(F, Conjuncion(T, Negacion(F))))),
                Disyuncion(T, F),
            ),
            Negacion(Conjuncion(T, T)),
        )
        assert evaluar(e2) is False

    def test_exhaustivo_hasta_longitud_5_contra_otras_implementaciones(self):
        """Toda cadena de hasta 5 terminales (19 607 cadenas).

        - Se acepta si y solo si tiene exactamente un árbol en la Figura 3
          (conteo por programación dinámica del Integrante 2).
        - Si se acepta, el AST es el mismo que construye el parser descendente
          del Integrante 6 y su valor es el de Python (misma precedencia
          not > and > or y asociatividad izquierda).
        - Si se rechaza, la línea produce exactamente una sentencia con error.
        """
        terminales = ('or', 'and', 'not', '(', ')', 'true', 'false')
        python = {'true': 'True', 'false': 'False'}
        aceptadas = 0
        for n in range(1, 6):
            for w in itertools.product(terminales, repeat=n):
                texto = ' '.join(w)
                sentencias = _sentencias(texto)
                assert len(sentencias) == 1, texto
                (s,) = sentencias
                if glc.contar_arboles(w) == 1:
                    aceptadas += 1
                    assert s.error is None, (texto, s.error)
                    assert s.arbol == parsear_expresion(texto), texto
                    assert evaluar(s.arbol) is eval(' '.join(python.get(x, x) for x in w)), texto
                else:
                    assert s.arbol is None and s.error.startswith('ERROR sintactico'), texto
        assert aceptadas == 2 + 2 + 12 + 22 + 90  # tabla 6.5 de verificacion_glc.md


# ---------------------------------------------------------------------------
# Programa y Sentencia: varias sentencias separadas por \n o ;
# ---------------------------------------------------------------------------

class TestPrograma:
    def test_devuelve_programa(self):
        assert isinstance(parsear_programa('true\n'), Programa)

    def test_varias_lineas(self):
        assert _resumen('true\nfalse and true\nnot false\n') == [
            (1, 'true', T),
            (2, 'false and true', Conjuncion(F, T)),
            (3, 'not false', Negacion(F)),
        ]

    def test_varias_sentencias_en_una_linea_con_punto_y_coma(self):
        assert _resumen('true and false; not true;false\n') == [
            (1, 'true and false', Conjuncion(T, F)),
            (1, 'not true', Negacion(T)),
            (1, 'false', F),
        ]

    def test_ultima_sentencia_sin_terminador(self):
        assert _resumen('true\nfalse or true') == [
            (1, 'true', T),
            (2, 'false or true', Disyuncion(F, T)),
        ]
        assert _resumen('true; false') == [(1, 'true', T), (1, 'false', F)]

    @pytest.mark.parametrize('texto', [
        '', '\n', '\n\n\n', ';', ';;\n;', '   \t \n',
        '// solo comentario', '/* bloque\n de varias lineas */\n', '// a\n// b\n',
    ])
    def test_sentencias_vacias_se_omiten(self, texto):
        assert _sentencias(texto) == []

    def test_numeros_de_linea_con_lineas_vacias_y_comentarios(self):
        texto = (
            '// encabezado\n'
            '\n'
            'true // comentario al final\n'
            '/* bloque\n'
            '   de dos lineas */ false\n'
            '  not true  \n'
        )
        assert _resumen(texto) == [
            (3, 'true', T),
            (5, 'false', F),
            (6, 'not true', Negacion(T)),
        ]

    def test_texto_conserva_el_espaciado_original_sin_comentarios(self):
        (s,) = _sentencias('  not (true   and false) /* x */ // y\n')
        assert s.texto == 'not (true   and false)'

    def test_saltos_de_linea_windows(self):
        assert _resumen('true\r\nfalse\r\n') == [(1, 'true', T), (2, 'false', F)]

    def test_una_instancia_se_puede_reutilizar(self):
        parser = ParserBoollang()
        primero = parser.parsear('true\n(true or\n')
        segundo = parser.parsear('false\n')
        assert [(s.linea, s.error) for s in primero.sentencias] == [
            (1, None), (2, "ERROR sintactico: fin de linea inesperado, falta ')'")]
        assert [(s.linea, s.arbol) for s in segundo.sentencias] == [(1, F)]

    def test_rechaza_entrada_que_no_es_texto(self):
        with pytest.raises(TypeError):
            parsear_programa(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Recuperación de errores por línea (error NEWLINE / error PUNTOYCOMA)
# ---------------------------------------------------------------------------

class TestRecuperacion:
    def test_e3_se_reporta_en_col_29_y_se_sigue_con_la_linea_siguiente(self):
        assert _resumen(f'{E3}\nnot false\n') == [
            (1, E3, "ERROR sintactico (col 29): token inesperado 'or'"),
            (2, 'not false', Negacion(F)),
        ]

    def test_fin_de_linea_inesperado(self):
        assert _resumen('true and\ntrue\n') == [
            (1, 'true and', 'ERROR sintactico: fin de linea inesperado'),
            (2, 'true', T),
        ]

    def test_fin_de_linea_con_parentesis_sin_cerrar(self):
        assert _resumen('true and (false or true\nnot false and true\n') == [
            (1, 'true and (false or true', "ERROR sintactico: fin de linea inesperado, falta ')'"),
            (2, 'not false and true', Conjuncion(Negacion(F), T)),
        ]

    def test_parentesis_de_cierre_sobrante(self):
        assert _resumen('(true))\n') == [
            (1, '(true))', "ERROR sintactico (col 7): token inesperado ')'"),
        ]

    def test_error_punto_y_coma_recupera_dentro_de_la_misma_linea(self):
        assert _resumen('true and ; false or true\n') == [
            (1, 'true and', "ERROR sintactico (col 10): token inesperado ';'"),
            (1, 'false or true', Disyuncion(F, T)),
        ]
        assert _resumen('true and (false; true\n') == [
            (1, 'true and (false', "ERROR sintactico (col 16): token inesperado ';', falta ')'"),
            (1, 'true', T),
        ]

    def test_recuperacion_descarta_tokens_hasta_el_primer_terminador(self):
        # tras el error se descartan tokens hasta el primer ';' o '\n'
        assert _resumen('true true; false\nnot true\n') == [
            (1, 'true true', "ERROR sintactico (col 6): token inesperado 'true'"),
            (1, 'false', F),
            (2, 'not true', Negacion(T)),
        ]
        assert _resumen('not or false and ( true\nfalse\n') == [
            (1, 'not or false and ( true', "ERROR sintactico (col 5): token inesperado 'or'"),
            (2, 'false', F),
        ]

    @pytest.mark.parametrize('primera, col, token', [
        ('or true', 1, 'or'),
        ('and false', 1, 'and'),
        (') true', 1, ')'),
    ])
    def test_error_en_el_primer_token_del_archivo(self, primera, col, token):
        # PLY descartaría el token en el estado 0 y aceptaría el resto de la línea.
        assert _resumen(f'{primera}\nfalse\n') == [
            (1, primera, f"ERROR sintactico (col {col}): token inesperado '{token}'"),
            (2, 'false', F),
        ]

    def test_cada_linea_erronea_consecutiva_se_reporta(self):
        # errok() en la regla de error: sin él PLY callaría los errores siguientes
        assert _resumen('and\n  or true\ntrue (\n)\ntrue\n') == [
            (1, 'and', "ERROR sintactico (col 1): token inesperado 'and'"),
            (2, 'or true', "ERROR sintactico (col 3): token inesperado 'or'"),
            (3, 'true (', "ERROR sintactico (col 6): token inesperado '('"),
            (4, ')', "ERROR sintactico (col 1): token inesperado ')'"),
            (5, 'true', T),
        ]

    def test_error_en_la_ultima_linea_sin_salto_de_linea(self):
        # PLY abandona en $end; las sentencias anteriores no se pierden
        assert _resumen('true\nfalse and') == [
            (1, 'true', T),
            (2, 'false and', 'ERROR sintactico: fin de linea inesperado'),
        ]
        assert _resumen('true\n(false or') == [
            (1, 'true', T),
            (2, '(false or', "ERROR sintactico: fin de linea inesperado, falta ')'"),
        ]
        assert _resumen('true; false false') == [
            (1, 'true', T),
            (1, 'false false', "ERROR sintactico (col 13): token inesperado 'false'"),
        ]

    def test_errores_lexicos_dejan_un_error_sintactico_en_cascada(self):
        # El parser no ve 'TRUE' (el lexer lo descarta); archivo.procesar_texto
        # le da prioridad al error léxico (ver TestIntegracion).
        assert _resumen('true and TRUE\n') == [
            (1, 'true and TRUE', 'ERROR sintactico: fin de linea inesperado'),
        ]


# ---------------------------------------------------------------------------
# Integración con boollang.archivo y la CLI
# ---------------------------------------------------------------------------

ESCENARIO_3 = (
    '// Programa con errores recuperables\n'
    f'{E1}\n'
    f'{E2}\n'
    f'{E3}\n'
    'true and TRUE\n'
    'true and (false or true\n'
    'not false and true\n'
)

SALIDA_ESCENARIO_3 = (
    '# Evaluaciones de: ejemplos/escenario3_recuperacion.bool\n'
    f'[L2] {E1} => true\n'
    f'[L3] {E2} => false\n'
    f"[L4] {E3} => ERROR sintactico (col 29): token inesperado 'or'\n"
    "[L5] true and TRUE => ERROR lexico (col 10): palabra no valida 'TRUE'\n"
    "[L6] true and (false or true => ERROR sintactico: fin de linea inesperado, falta ')'\n"
    '[L7] not false and true => true\n'
    '# Resumen: 6 expresiones procesadas | 3 evaluadas | 3 con error\n'
)


class TestIntegracion:
    def test_escenario_3_con_el_parser_real(self):
        salida, resumen = procesar_texto(
            ESCENARIO_3, nombre_fuente='ejemplos/escenario3_recuperacion.bool')
        assert salida == SALIDA_ESCENARIO_3
        assert (resumen.procesadas, resumen.evaluadas, resumen.con_error) == (6, 3, 3)

    def test_varias_sentencias_y_linea_solo_con_error_lexico(self):
        salida, resumen = procesar_texto('true and false; not true\nBADWORD', nombre_fuente='mix.bool')
        assert salida == (
            '# Evaluaciones de: mix.bool\n'
            '[L1] true and false => false\n'
            '[L1] not true => false\n'
            "[L2] BADWORD => ERROR lexico (col 1): palabra no valida 'BADWORD'\n"
            '# Resumen: 3 expresiones procesadas | 2 evaluadas | 1 con error\n'
        )
        assert resumen.procesadas == 3

    def test_procesar_archivo_escribe_el_out(self, tmp_path):
        src = tmp_path / 'escenario3.bool'
        dst = tmp_path / 'salida' / 'escenario3.out'
        src.write_text(ESCENARIO_3, encoding='utf-8')
        procesar_archivo(src, dst, nombre_fuente='ejemplos/escenario3_recuperacion.bool')
        assert dst.read_text(encoding='utf-8') == SALIDA_ESCENARIO_3

    def test_cli_genera_el_out(self, tmp_path, capsys):
        src = tmp_path / 'entrada.bool'
        dst = tmp_path / 'entrada.out'
        src.write_text(ESCENARIO_3, encoding='utf-8')
        assert main([str(src), '-o', str(dst)]) == 0
        assert '6 procesadas, 3 evaluadas, 3 con error' in capsys.readouterr().out
        assert dst.read_text(encoding='utf-8').splitlines()[1:] == SALIDA_ESCENARIO_3.splitlines()[1:]

    def test_cli_traza_usa_el_ast_del_parser(self, tmp_path, capsys):
        src = tmp_path / 'traza.bool'
        src.write_text(f'{E1}\n', encoding='utf-8')
        assert main([str(src), '-o', str(tmp_path / 'traza.out'), '--traza', '--ascii']) == 0
        salida = capsys.readouterr().out
        assert f'[Línea 1] {E1}' in salida
        assert 'Resultado final:    true' in salida
        assert 'Pasos de reduccion (5 pasos):' in salida

    def test_subproceso_python_m_boollang(self, tmp_path):
        src = tmp_path / 'prog.bool'
        dst = tmp_path / 'prog.out'
        src.write_text('true or false; not true\n(true\n', encoding='utf-8')
        proc = subprocess.run(
            [sys.executable, '-m', 'boollang', str(src), '-o', str(dst)],
            capture_output=True, text=True, cwd=RAIZ, check=False,
        )
        assert proc.returncode == 0, proc.stderr
        assert dst.read_text(encoding='utf-8').splitlines()[1:] == [
            '[L1] true or false => true',
            '[L1] not true => false',
            "[L2] (true => ERROR sintactico: fin de linea inesperado, falta ')'",
            '# Resumen: 3 expresiones procesadas | 2 evaluadas | 1 con error',
        ]


# ---------------------------------------------------------------------------
# Tarea 37: Expresiones proposicionales relacionales, aritméticas y asignación
# ---------------------------------------------------------------------------

from boollang.nodos import (
    Asignacion,
    BinOpArit,
    ComparacionRel,
    Numero,
    UnarioArit,
    Variable,
)


class TestParserRelacionalTarea37:
    """Pruebas del parser LALR(1) extendido para la Tarea 37 (Integrante 3)."""

    def test_ejemplo_exacto_del_enunciado(self):
        ast = _arbol('(3X+5Y) <= X/(3-Z)')
        assert ast == ComparacionRel(
            '<=',
            BinOpArit(
                '+',
                BinOpArit('*', Numero(3), Variable('X'), implicita=True),
                BinOpArit('*', Numero(5), Variable('Y'), implicita=True),
            ),
            BinOpArit('/', Variable('X'), BinOpArit('-', Numero(3), Variable('Z'))),
        )
        assert ast.a_texto() == '3X+5Y <= X/(3-Z)'

    def test_multiplicacion_implicita_con_parentesis_y_unario(self):
        ast = _arbol('2(X+1) == -3 * Y')
        assert ast == ComparacionRel(
            '==',
            BinOpArit('*', Numero(2), BinOpArit('+', Variable('X'), Numero(1)), implicita=True),
            BinOpArit('*', UnarioArit(Numero(3)), Variable('Y')),
        )

    def test_combinacion_proposicional_relacional_y_booleana(self):
        ast = _arbol('not ((3X+5Y) <= X/(3-Z)) and (2X + Y == 5) or false')
        assert isinstance(ast, Disyuncion)
        assert isinstance(ast.izq, Conjuncion)
        assert isinstance(ast.izq.izq, Negacion)
        assert isinstance(ast.izq.izq.op, ComparacionRel)
        assert isinstance(ast.izq.der, ComparacionRel)
        assert ast.der == Constante(False)

    def test_asignaciones_separadas_por_punto_y_coma(self):
        res = _resumen('X = 2; Y = 1; Z = 2;\n')
        assert res == [
            (1, 'X = 2', Asignacion('X', Numero(2))),
            (1, 'Y = 1', Asignacion('Y', Numero(1))),
            (1, 'Z = 2', Asignacion('Z', Numero(2))),
        ]

    def test_error_sintactico_doble_operador_relacional(self):
        res = _resumen('(3X+5Y) <= <= 10\nX = 3\n')
        assert res == [
            (1, '(3X+5Y) <= <= 10', "ERROR sintactico (col 12): token inesperado '<='"),
            (2, 'X = 3', Asignacion('X', Numero(3))),
        ]


    def test_multiplicacion_implicita_combinada_con_unario_y_division(self):
        from boollang.evaluador import evaluar

        env = {'X': 2, 'Y': 1}
        assert evaluar(_arbol('-2X <= 0'), env) is True
        assert evaluar(_arbol('2 * 3X == 12'), env) is True
        assert evaluar(_arbol('6 / 2X == 1.5'), env) is True
        assert evaluar(_arbol('3X * 5Y == 30'), env) is True
        assert evaluar(_arbol('-2(X+1) == -6'), env) is True
