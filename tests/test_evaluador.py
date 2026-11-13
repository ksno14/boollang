"""
Pruebas unitarias para los módulos del Integrante 4:
- boollang.nodos (definición mínima de nodos AST)
- boollang.evaluador (evaluación semántica y resumen)
- boollang.archivo (lectura .bool, conciliación de errores y escritura .out)
- boollang.__main__ (interfaz CLI)
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from boollang import (
    Conjuncion,
    Constante,
    Disyuncion,
    Negacion,
    ParserNoDisponibleError,
    Programa,
    Sentencia,
    evaluar,
    evaluar_programa,
    evaluar_sentencia,
    formatear_booleano,
    procesar_archivo,
    procesar_texto,
)
from boollang.__main__ import main


class TestNodos:
    def test_construccion_y_comparacion_ast(self):
        c_true = Constante(True)
        c_false = Constante(False)
        nodo = Disyuncion(Negacion(c_false), Conjuncion(c_true, c_false))

        assert nodo.izq == Negacion(Constante(False))
        assert nodo.der == Conjuncion(Constante(True), Constante(False))

    def test_sentencia_y_programa(self):
        sent = Sentencia(linea=1, texto="true", arbol=Constante(True))
        prog = Programa(sentencias=[sent])
        assert len(prog.sentencias) == 1
        assert prog.sentencias[0].error is None


class TestEvaluador:
    def test_formatear_booleano(self):
        assert formatear_booleano(True) == "true"
        assert formatear_booleano(False) == "false"
        with pytest.raises(TypeError):
            formatear_booleano(1)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "nodo,esperado",
        [
            (Constante(True), True),
            (Constante(False), False),
            (Negacion(Constante(True)), False),
            (Negacion(Constante(False)), True),
            (Negacion(Negacion(Constante(True))), True),
            (Conjuncion(Constante(True), Constante(True)), True),
            (Conjuncion(Constante(True), Constante(False)), False),
            (Conjuncion(Constante(False), Constante(True)), False),
            (Conjuncion(Constante(False), Constante(False)), False),
            (Disyuncion(Constante(True), Constante(True)), True),
            (Disyuncion(Constante(True), Constante(False)), True),
            (Disyuncion(Constante(False), Constante(True)), True),
            (Disyuncion(Constante(False), Constante(False)), False),
        ],
    )
    def test_tablas_verdad_basicas(self, nodo, esperado):
        assert evaluar(nodo) is esperado

    def test_expresiones_anidadas_escenario3(self):
        # L2: not (true and false) or false and not false => true
        l2 = Disyuncion(
            Negacion(Conjuncion(Constante(True), Constante(False))),
            Conjuncion(Constante(False), Negacion(Constante(False))),
        )
        assert evaluar(l2) is True

        # L3: not not (false or true and not false) and (true or false) and not (true and true) => false
        parte_a = Negacion(
            Negacion(
                Disyuncion(
                    Constante(False),
                    Conjuncion(Constante(True), Negacion(Constante(False))),
                )
            )
        )
        parte_b = Disyuncion(Constante(True), Constante(False))
        parte_c = Negacion(Conjuncion(Constante(True), Constante(True)))
        l3 = Conjuncion(Conjuncion(parte_a, parte_b), parte_c)
        assert evaluar(l3) is False

        # L7: not false and true => true
        l7 = Conjuncion(Negacion(Constante(False)), Constante(True))
        assert evaluar(l7) is True

    def test_evaluar_tipos_invalidos(self):
        with pytest.raises(TypeError):
            evaluar(None)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            evaluar(Constante("true"))  # type: ignore[arg-type]

    def test_evaluar_sentencia_y_programa(self):
        sentencias = [
            Sentencia(linea=1, texto="true and false", arbol=Conjuncion(Constante(True), Constante(False))),
            Sentencia(linea=2, texto="true and", arbol=None, error="ERROR sintactico: fin de linea"),
            Sentencia(linea=3, texto="vacio", arbol=None, error=None),
        ]
        resumen = evaluar_programa(Programa(sentencias))
        assert resumen.procesadas == 3
        assert resumen.evaluadas == 1
        assert resumen.con_error == 2
        assert resumen.resultados[0].formatear_linea() == "[L1] true and false => false"
        assert resumen.resultados[1].formatear_linea() == "[L2] true and => ERROR sintactico: fin de linea"
        assert "ERROR interno" in resumen.resultados[2].formatear_linea()

        individual = evaluar_sentencia(sentencias[0])
        assert individual.valor is False
        assert not individual.es_error


class TestArchivo:
    def test_escenario3_completo_y_prioridad_error_lexico(self):
        contenido = (
            "// Programa con errores recuperables\n"
            "not (true and false) or false and not false\n"
            "not not (false or true and not false) and (true or false) and not (true and true)\n"
            "(true or not false) and not or false\n"
            "true and TRUE\n"
            "true and (false or true\n"
            "not false and true\n"
        )

        # Simula un parser del Integrante 3 que incluso reporta error sintáctico en cascada en L5
        def parser_simulado(_src: str) -> Programa:
            return Programa(
                [
                    Sentencia(
                        linea=2,
                        texto="not (true and false) or false and not false",
                        arbol=Disyuncion(
                            Negacion(Conjuncion(Constante(True), Constante(False))),
                            Conjuncion(Constante(False), Negacion(Constante(False))),
                        ),
                    ),
                    Sentencia(
                        linea=3,
                        texto="not not (false or true and not false) and (true or false) and not (true and true)",
                        arbol=Conjuncion(
                            Conjuncion(
                                Negacion(
                                    Negacion(
                                        Disyuncion(
                                            Constante(False),
                                            Conjuncion(Constante(True), Negacion(Constante(False))),
                                        )
                                    )
                                ),
                                Disyuncion(Constante(True), Constante(False)),
                            ),
                            Negacion(Conjuncion(Constante(True), Constante(True))),
                        ),
                    ),
                    Sentencia(
                        linea=4,
                        texto="(true or not false) and not or false",
                        error="ERROR sintactico (col 29): token inesperado 'or'",
                    ),
                    Sentencia(
                        linea=5,
                        texto="true and TRUE",
                        error="ERROR sintactico (col 10): error en cascada que debe perder prioridad",
                    ),
                    Sentencia(
                        linea=6,
                        texto="true and (false or true",
                        error="ERROR sintactico: fin de linea inesperado, falta ')'",
                    ),
                    Sentencia(
                        linea=7,
                        texto="not false and true",
                        arbol=Conjuncion(Negacion(Constante(False)), Constante(True)),
                    ),
                ]
            )

        salida, resumen = procesar_texto(
            contenido,
            nombre_fuente="ejemplos/escenario3_recuperacion.bool",
            parser_fn=parser_simulado,
        )

        esperado = (
            "# Evaluaciones de: ejemplos/escenario3_recuperacion.bool\n"
            "[L2] not (true and false) or false and not false => true\n"
            "[L3] not not (false or true and not false) and (true or false) and not (true and true) => false\n"
            "[L4] (true or not false) and not or false => ERROR sintactico (col 29): token inesperado 'or'\n"
            "[L5] true and TRUE => ERROR lexico (col 10): palabra no valida 'TRUE'\n"
            "[L6] true and (false or true => ERROR sintactico: fin de linea inesperado, falta ')'\n"
            "[L7] not false and true => true\n"
            "# Resumen: 6 expresiones procesadas | 3 evaluadas | 3 con error\n"
        )
        assert salida == esperado
        assert resumen.procesadas == 6
        assert resumen.evaluadas == 3
        assert resumen.con_error == 3

    def test_sintetiza_linea_con_error_lexico_omitida_por_parser_y_multiples_sentencias(self):
        contenido = "true and false; not true\nBADWORD"

        def parser_sin_error_lexico(_src: str) -> list[Sentencia]:
            return [
                Sentencia(
                    linea=1,
                    texto="true and false",
                    arbol=Conjuncion(Constante(True), Constante(False)),
                ),
                Sentencia(
                    linea=1,
                    texto="not true",
                    arbol=Negacion(Constante(True)),
                ),
            ]

        salida, resumen = procesar_texto(contenido, nombre_fuente="mix.bool", parser_fn=parser_sin_error_lexico)
        assert "[L1] true and false => false" in salida
        assert "[L1] not true => false" in salida
        assert "[L2] BADWORD => ERROR lexico (col 1): palabra no valida 'BADWORD'" in salida
        assert "# Resumen: 3 expresiones procesadas | 2 evaluadas | 1 con error" in salida
        assert resumen.procesadas == 3

    def test_procesar_archivo_disco(self, tmp_path: Path):
        src = tmp_path / "prueba.bool"
        dst = tmp_path / "out" / "resultado.out"
        src.write_text("not false\n", encoding="utf-8")

        def parser_ok(_src: str) -> list[Sentencia]:
            return [Sentencia(linea=1, texto="", arbol=Negacion(Constante(False)))]

        resumen = procesar_archivo(src, dst, parser_fn=parser_ok)
        assert resumen.procesadas == 1
        assert resumen.evaluadas == 1
        contenido_out = dst.read_text(encoding="utf-8")
        assert "[L1] not false => true" in contenido_out

    def test_error_si_parser_no_esta_disponible(self):
        with pytest.raises(ParserNoDisponibleError):
            procesar_texto("true\n")


class TestCLI:
    def test_main_exitoso_con_parser_inyectado(self, tmp_path: Path):
        src = tmp_path / "entrada.bool"
        dst = tmp_path / "salida.out"
        src.write_text("true or false\n", encoding="utf-8")

        def fake_procesar(ruta_in, ruta_out):
            return procesar_archivo(
                ruta_in,
                ruta_out,
                parser_fn=lambda _s: [
                    Sentencia(linea=1, texto="true or false", arbol=Disyuncion(Constante(True), Constante(False)))
                ],
            )

        with patch("boollang.__main__.procesar_archivo", side_effect=fake_procesar):
            codigo = main([str(src), "-o", str(dst)])

        assert codigo == 0
        assert "[L1] true or false => true" in dst.read_text(encoding="utf-8")

    def test_main_archivo_inexistente(self, tmp_path: Path, capsys):
        inexistente = tmp_path / "no_existe.bool"
        codigo = main([str(inexistente), "-o", str(tmp_path / "out.out")])
        capturado = capsys.readouterr()
        assert codigo == 1
        assert "no se encontró" in capturado.err

    def test_subproceso_help_cli(self):
        proc = subprocess.run(
            [sys.executable, "-m", "boollang", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert "-o" in proc.stdout
        assert "--salida" in proc.stdout
