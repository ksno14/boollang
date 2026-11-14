"""
Suite de pruebas unitarias para el trabajo del Integrante 6:
- Estructura y métodos del AST (boollang.nodos)
- Formateo visual en texto del árbol sintáctico (formatear_arbol)
- Motor de traza paso a paso por precedencia (trazar_evaluacion, PasoTraza, TrazaEvaluacion)
- Formateo textual de traza (formatear_traza)
- Verificación automatizada de las 3 expresiones del Numeral 2 (verificar_numeral2)
- Integración con la interfaz CLI (--traza, -e, --numeral2)
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from boollang import (
    Conjuncion,
    Constante,
    Disyuncion,
    Negacion,
    PasoTraza,
    Sentencia,
    TrazaEvaluacion,
    evaluar,
    evaluar_con_traza,
    formatear_arbol,
    formatear_booleano,
    formatear_traza,
    parsear_expresion,
    trazar_evaluacion,
    verificar_numeral2,
)
from boollang.__main__ import main


class TestASTNodosMetodos:
    """Pruebas de introspección, propiedades y reconstrucción textual de los nodos del AST."""

    def test_constante_propiedades(self):
        c_true = Constante(True)
        c_false = Constante(False)

        assert c_true.nombre_op == "const"
        assert c_true.prioridad == 4
        assert c_true.hijos() == ()
        assert c_true.a_texto() == "true"
        assert str(c_true) == "true"

        assert c_false.nombre_op == "const"
        assert c_false.prioridad == 4
        assert c_false.hijos() == ()
        assert c_false.a_texto() == "false"
        assert str(c_false) == "false"

    def test_negacion_propiedades_y_texto(self):
        neg_simple = Negacion(Constante(False))
        assert neg_simple.nombre_op == "not"
        assert neg_simple.prioridad == 3
        assert neg_simple.hijos() == (Constante(False),)
        assert neg_simple.a_texto() == "not false"
        assert str(neg_simple) == "not false"

        # Negación doble
        doble_neg = Negacion(neg_simple)
        assert doble_neg.a_texto() == "not not false"

        # Negación sobre binario debe poner paréntesis
        neg_bin = Negacion(Conjuncion(Constante(True), Constante(False)))
        assert neg_bin.a_texto() == "not (true and false)"

    def test_conjuncion_propiedades_y_texto(self):
        c1 = Constante(True)
        c2 = Constante(False)
        conj = Conjuncion(c1, c2)

        assert conj.nombre_op == "and"
        assert conj.prioridad == 2
        assert conj.hijos() == (c1, c2)
        assert conj.a_texto() == "true and false"

        # Asociatividad a la izquierda: (A and B) and C no requiere paréntesis
        conj_asoc_izq = Conjuncion(conj, Constante(True))
        assert conj_asoc_izq.a_texto() == "true and false and true"

        # Hijo derecho con conjunción sí requiere paréntesis para forzar orden
        conj_asoc_der = Conjuncion(Constante(True), conj)
        assert conj_asoc_der.a_texto() == "true and (true and false)"

        # Hijo con disyunción (menor precedencia) debe llevar paréntesis
        disy = Disyuncion(c1, c2)
        conj_con_disy = Conjuncion(disy, c1)
        assert conj_con_disy.a_texto() == "(true or false) and true"

    def test_disyuncion_propiedades_y_texto(self):
        c1 = Constante(True)
        c2 = Constante(False)
        disy = Disyuncion(c1, c2)

        assert disy.nombre_op == "or"
        assert disy.prioridad == 1
        assert disy.hijos() == (c1, c2)
        assert disy.a_texto() == "true or false"

        # Asociatividad a la izquierda: (A or B) or C
        disy_izq = Disyuncion(disy, Constante(True))
        assert disy_izq.a_texto() == "true or false or true"

        # Hijo derecho con disyunción
        disy_der = Disyuncion(Constante(True), disy)
        assert disy_der.a_texto() == "true or (true or false)"


class TestFormateadorArbol:
    """Pruebas del formateador visual en texto jerárquico."""

    def test_formatear_constante(self):
        c = Constante(True)
        assert formatear_arbol(c, con_valores=True) == "true   [true]"
        assert formatear_arbol(c, con_valores=False) == "true"

    def test_formatear_negacion(self):
        nodo = Negacion(Constante(False))
        salida_unicode = formatear_arbol(nodo, con_valores=True, estilo="unicode")
        assert "not   [true]" in salida_unicode
        assert "└── false   [false]" in salida_unicode

        salida_ascii = formatear_arbol(nodo, con_valores=True, estilo="ascii")
        assert "\\-- false   [false]" in salida_ascii

    def test_formatear_expresion_e1(self):
        # E1: not (true and false) or false and not false
        c_t = Constante(True)
        c_f = Constante(False)
        e1 = Disyuncion(
            Negacion(Conjuncion(c_t, c_f)),
            Conjuncion(c_f, Negacion(c_f)),
        )
        salida = formatear_arbol(e1, con_valores=True)
        esperado = (
            "or   [true]\n"
            "├── not   [true]\n"
            "│   └── and   [false]\n"
            "│       ├── true   [true]\n"
            "│       └── false   [false]\n"
            "└── and   [false]\n"
            "    ├── false   [false]\n"
            "    └── not   [true]\n"
            "        └── false   [false]"
        )
        assert salida == esperado

    def test_formatear_arbol_estilo_invalido(self):
        with pytest.raises(ValueError, match="estilo no soportado"):
            formatear_arbol(Constante(True), estilo="emoji")


class TestMotorTrazaEvaluacion:
    """Pruebas del motor de traza paso a paso según precedencia de operadores."""

    def test_traza_constante(self):
        traza = trazar_evaluacion(Constante(True))
        assert traza.resultado_final is True
        assert traza.total_pasos == 1
        assert traza.pasos[0].operador == "CONST"

    def test_traza_precedencia_not_antes_de_and(self):
        # not false and false => paso 1: not false -> true, paso 2: true and false -> false
        ast = parsear_expresion("not false and false")
        traza = trazar_evaluacion(ast)
        assert traza.resultado_final is False
        assert traza.total_pasos == 2
        assert traza.pasos[0].operador == "NOT"
        assert traza.pasos[0].subexpresion == "not false"
        assert traza.pasos[0].resultado is True
        assert traza.pasos[1].operador == "AND"
        assert traza.pasos[1].resultado is False

    def test_traza_precedencia_and_antes_de_or(self):
        # true or false and false => and debe evaluarse antes que or
        ast = parsear_expresion("true or false and false")
        traza = trazar_evaluacion(ast)
        assert traza.resultado_final is True
        assert traza.total_pasos == 2
        assert traza.pasos[0].operador == "AND"
        assert traza.pasos[0].subexpresion == "false and false"
        assert traza.pasos[0].resultado is False
        assert traza.pasos[1].operador == "OR"
        assert traza.pasos[1].resultado is True

    def test_traza_parentesis_alteran_precedencia(self):
        # (true or false) and false => or se evalúa antes de and por el paréntesis
        ast = parsear_expresion("(true or false) and false")
        traza = trazar_evaluacion(ast)
        assert traza.resultado_final is False
        assert traza.total_pasos == 2
        assert traza.pasos[0].operador == "OR"
        assert traza.pasos[0].subexpresion == "true or false"
        assert traza.pasos[0].resultado is True
        assert traza.pasos[1].operador == "AND"

    def test_traza_asociatividad_izquierda(self):
        # true and false and true => primero el AND de la izquierda
        ast = parsear_expresion("true and false and true")
        traza = trazar_evaluacion(ast)
        assert traza.resultado_final is False
        assert traza.total_pasos == 2
        assert traza.pasos[0].operador == "AND"
        assert traza.pasos[0].subexpresion == "true and false"
        assert traza.pasos[0].resultado is False
        assert traza.pasos[1].subexpresion == "false and true"

    def test_formatear_traza_texto(self):
        traza = trazar_evaluacion("not false and true")
        texto_traza = formatear_traza(traza)
        assert "Traza de Evaluacion (Precedencia: not > and > or)" in texto_traza
        assert "Expresion original: not false and true" in texto_traza
        assert "Resultado final:    true" in texto_traza
        assert "[NOT] not false => true" in texto_traza
        assert "[AND] true and true => true" in texto_traza

    def test_evaluar_con_traza(self):
        sent = Sentencia(linea=3, texto="true or false", arbol=parsear_expresion("true or false"))
        res, traza = evaluar_con_traza(sent)
        assert res.linea == 3
        assert res.valor is True
        assert traza is not None
        assert traza.resultado_final is True


class TestVerificacionNumeral2:
    """Pruebas para la verificación automatizada de las 3 expresiones del Numeral 2."""

    def test_numeral2_completo(self):
        resultados = verificar_numeral2()

        # E1
        e1 = resultados["E1"]
        assert e1["valida"] is True
        assert e1["valor"] is True
        assert e1["coincide"] is True
        assert e1["total_pasos"] == 5

        # E2
        e2 = resultados["E2"]
        assert e2["valida"] is True
        assert e2["valor"] is False
        assert e2["coincide"] is True
        assert e2["total_pasos"] == 10

        # E3
        e3 = resultados["E3"]
        assert e3["valida"] is False
        assert e3["bloqueo_detectado"] is True
        assert e3["bloqueo_correcto"] is True
        assert "col 29" in e3["mensaje_error"]
        assert "'or'" in e3["mensaje_error"]


class TestCLIIntegrante6:
    """Pruebas de la integración en la línea de comandos (__main__.py)."""

    def test_cli_numeral2(self, capsys):
        codigo = main(["--numeral2"])
        assert codigo == 0
        salida = capsys.readouterr().out
        assert "VERIFICACIÓN AUTOMATIZADA — NUMERAL 2" in salida
        assert "[E1]" in salida
        assert "[E2]" in salida
        assert "[E3]" in salida
        assert "columna 29" in salida

    def test_cli_expresion_directa_con_traza(self, capsys):
        codigo = main(["-e", "not (true and false) or false", "-t"])
        assert codigo == 0
        salida = capsys.readouterr().out
        assert "Traza de Evaluacion" in salida
        assert "Resultado final:    true" in salida
        assert "[AND]" in salida
        assert "[NOT]" in salida
        assert "[OR ]" in salida

    def test_cli_expresion_directa_simple(self, capsys):
        codigo = main(["-e", "true and not false"])
        assert codigo == 0
        salida = capsys.readouterr().out.strip()
        assert salida == "true"

    def test_cli_expresion_invalida(self, capsys):
        codigo = main(["-e", "true not false"])
        assert codigo == 1
        err = capsys.readouterr().err
        assert "Error" in err

    def test_cli_archivo_con_traza(self, tmp_path: Path, capsys):
        src = tmp_path / "prueba.bool"
        dst = tmp_path / "prueba.out"
        src.write_text("not false and true\n", encoding="utf-8")

        from boollang.evaluador import ResumenEvaluacion, ResultadoSentencia

        def fake_procesar(ruta_in, ruta_out):
            res = ResultadoSentencia(
                linea=1,
                texto="not false and true",
                valor=True,
            )
            return ResumenEvaluacion(
                procesadas=1,
                evaluadas=1,
                con_error=0,
                resultados=[res],
            )

        with patch("boollang.__main__.procesar_archivo", side_effect=fake_procesar):
            codigo = main([str(src), "-o", str(dst), "--traza"])

        assert codigo == 0
        salida = capsys.readouterr().out
        assert "TRAZA DETALLADA DE EVALUACIÓN" in salida
        assert "[Línea 1] not false and true" in salida
        assert "not false => true" in salida

    def test_cli_archivo_con_traza_reutiliza_ast(self, capsys):
        from boollang.evaluador import ResumenEvaluacion, ResultadoSentencia

        arbol = parsear_expresion("not false and true")

        def fake_procesar(ruta_in, ruta_out):
            res = ResultadoSentencia(
                linea=7,
                texto="not false and true",
                valor=True,
                arbol=arbol,
            )
            return ResumenEvaluacion(
                procesadas=1,
                evaluadas=1,
                con_error=0,
                resultados=[res],
            )

        with patch("boollang.__main__.procesar_archivo", side_effect=fake_procesar):
            codigo = main(["fake.bool", "--traza"])

        assert codigo == 0
        salida = capsys.readouterr().out
        assert "[Línea 7] not false and true" in salida
        assert "not false => true" in salida

    def test_cli_numeral2_ascii(self, capsys):
        codigo = main(["--numeral2", "--ascii"])
        assert codigo == 0
        salida = capsys.readouterr().out
        assert "|--" in salida
        assert "├" not in salida
        assert "└" not in salida


from boollang import BinOpArit, ComparacionRel, Numero, Variable


class TestTrazaRelacionalTarea37:
    """Pruebas de nodos AST extendidos y traza paso a paso para la Tarea 37 (Integrante 6)."""

    def test_nodos_relacionales_y_aritmeticos_a_texto(self):
        nodo = ComparacionRel(
            "<=",
            BinOpArit(
                "+",
                BinOpArit("*", Numero(3), Variable("X"), implicita=True),
                BinOpArit("*", Numero(5), Variable("Y"), implicita=True),
            ),
            BinOpArit("/", Variable("X"), BinOpArit("-", Numero(3), Variable("Z"))),
        )
        assert nodo.a_texto() == "3X+5Y <= X/(3-Z)"
        assert Negacion(nodo).a_texto() == "not (3X+5Y <= X/(3-Z))"

    def test_traza_relacional_muestra_valores_numericos_intermedios_y_booleano_final(self):
        env = {"X": 2, "Y": 1, "Z": 2}
        traza = trazar_evaluacion("(3X+5Y) <= X/(3-Z)", entorno=env)
        assert traza.resultado_final is False
        # Verifica que se hayan reducido 3X -> 6, 5Y -> 5, 6+5 -> 11, 3-2 -> 1, 2/1 -> 2.0 y 11 <= 2.0 -> false
        subexpresiones = [p.subexpresion for p in traza.pasos]
        resultados = [p.resultado for p in traza.pasos]
        assert "3X" in subexpresiones
        assert 6 in resultados
        assert 11 in resultados
        assert 2.0 in resultados
        assert traza.pasos[-1].operador == "<="
        assert traza.pasos[-1].resultado is False

        texto_arbol = formatear_arbol(parsear_expresion("(3X+5Y) <= X/(3-Z)"), con_valores=True, entorno=env)
        assert "<=   [false]" in texto_arbol
        assert "+   [11]" in texto_arbol
        assert "/   [2.0]" in texto_arbol

