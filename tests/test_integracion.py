"""
Suite de pruebas de integracion de extremo a extremo para boollang (Integrante 7).

Valida la cadena completa sin mocks:
  archivo (.bool) -> lexer -> parser LALR(1) -> evaluador -> traza/AST -> archivo (.out) / CLI.
"""

from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path

import pytest

import boollang
from boollang import (
    ParserBoollang,
    Programa,
    evaluar,
    evaluar_con_traza,
    parsear_expresion,
    parsear_programa,
    procesar_archivo,
    procesar_texto,
)

RAIZ_REPO = Path(__file__).resolve().parents[1]
DIR_EJEMPLOS = RAIZ_REPO / "ejemplos"


def _ejecutar_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "boollang", *args],
        cwd=str(RAIZ_REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


# ==============================================================================
# 1. Integracion de la API publica del paquete boollang
# ==============================================================================


class TestIntegracionAPIPublica:
    """Verifica que todos los modulos de los 7 integrantes se integran desde boollang."""

    def test_exportaciones_principales_disponibles(self) -> None:
        assert hasattr(boollang, "ParserBoollang")
        assert hasattr(boollang, "parsear_programa")
        assert callable(parsear_programa)
        parser = ParserBoollang()
        programa = parser.parsear("true and not false")
        assert isinstance(programa, Programa)
        assert len(programa.sentencias) == 1
        assert evaluar(programa.sentencias[0].arbol) is True

    def test_consistencia_entre_parser_programa_y_parsear_expresion(self) -> None:
        expresiones = [
            "true",
            "false",
            "not true",
            "true and false or true",
            "not (true and false) or false and not false",
            "(not true or false) and (true or not false) or not (false or true) and true",
        ]
        for expr in expresiones:
            ast_prog = parsear_programa(expr).sentencias[0].arbol
            ast_expr = parsear_expresion(expr)
            assert ast_prog == ast_expr
            assert evaluar(ast_prog) == evaluar(ast_expr)


# ==============================================================================
# 2. Procesamiento extremo a extremo de los archivos .bool de ejemplos/
# ==============================================================================


class TestIntegracionArchivosEjemplo:
    """Ejecuta los programas fuente de ejemplos/*.bool y valida los .out generados."""

    def test_01_basicas_y_precedencia_archivo_y_cli(self, tmp_path: Path) -> None:
        fuente = DIR_EJEMPLOS / "01_basicas_y_precedencia.bool"
        salida = tmp_path / "01_basicas_y_precedencia.out"

        resumen = procesar_archivo(fuente, salida)
        assert resumen.procesadas == 14
        assert resumen.evaluadas == 14
        assert resumen.con_error == 0

        valores = [r.valor for r in resumen.resultados]
        assert valores == [
            True,   # true
            False,  # false
            False,  # not true
            True,   # not false
            False,  # true and false
            True,   # true and true
            True,   # false or true
            False,  # false or false
            True,   # true or false and false
            False,  # (true or false) and false
            False,  # not true and false
            True,   # not (true and false)
            True,   # E1
            False,  # E2
        ]

        salida_cli = tmp_path / "01_cli.out"
        proc = _ejecutar_cli(str(fuente), "-o", str(salida_cli))
        assert proc.returncode == 0
        assert salida_cli.read_text(encoding="utf-8") == salida.read_text(encoding="utf-8")

    def test_02_comentarios_y_formato(self, tmp_path: Path) -> None:
        fuente = DIR_EJEMPLOS / "02_comentarios_y_formato.bool"
        salida = tmp_path / "02_comentarios_y_formato.out"

        resumen = procesar_archivo(fuente, salida)
        assert resumen.procesadas == 6
        assert resumen.evaluadas == 6
        assert resumen.con_error == 0
        assert [r.valor for r in resumen.resultados] == [True, False, True, True, True, True]

    def test_03_errores_y_recuperacion_prioridad_lexica_y_sintactica(self, tmp_path: Path) -> None:
        fuente = DIR_EJEMPLOS / "03_errores_y_recuperacion.bool"
        salida = tmp_path / "03_errores_y_recuperacion.out"

        resumen = procesar_archivo(fuente, salida)
        assert resumen.procesadas == 8
        assert resumen.evaluadas == 3
        assert resumen.con_error == 5

        r = resumen.resultados
        assert not r[0].es_error and r[0].valor is False
        assert r[1].error and "ERROR lexico" in r[1].error and "TRUE" in r[1].error
        assert r[2].error and "ERROR sintactico (col 30)" in r[2].error
        assert r[3].error and "falta ')'" in r[3].error
        assert r[4].error and "ERROR lexico" in r[4].error and "@" in r[4].error
        assert r[5].error and "ERROR sintactico" in r[5].error
        assert not r[6].es_error and r[6].valor is True
        assert not r[7].es_error and r[7].valor is True

        contenido_out = salida.read_text(encoding="utf-8")
        assert "# Resumen: 8 expresiones procesadas | 3 evaluadas | 5 con error" in contenido_out

    def test_04_leyes_logicas(self, tmp_path: Path) -> None:
        fuente = DIR_EJEMPLOS / "04_leyes_logicas.bool"
        salida = tmp_path / "04_leyes_logicas.out"

        resumen = procesar_archivo(fuente, salida)
        assert resumen.procesadas == 9
        assert resumen.evaluadas == 9
        assert resumen.con_error == 0
        assert [r.valor for r in resumen.resultados] == [
            True,   # doble negacion
            True,   # tercero excluido
            False,  # contradiccion
            True,   # De Morgan 1
            True,   # De Morgan 2
            False,  # De Morgan 3
            False,  # De Morgan 4
            True,   # absorcion
            True,   # distributividad
        ]


# ==============================================================================
# 3. Verificacion exhaustiva de leyes booleanas e integracion CLI con --traza
# ==============================================================================


class TestIntegracionExhaustivaYCLI:
    """Pruebas exhaustivas de algebra booleana, anidamiento profundo y CLI real."""

    @pytest.mark.parametrize("a,b,c", list(itertools.product([False, True], repeat=3)))
    def test_leyes_de_morgan_y_distributividad_via_pipeline_completo(
        self, a: bool, b: bool, c: bool
    ) -> None:
        sa = "true" if a else "false"
        sb = "true" if b else "false"
        sc = "true" if c else "false"

        fuente = "\n".join(
            [
                f"not ({sa} and {sb})",
                f"not {sa} or not {sb}",
                f"not ({sa} or {sb})",
                f"not {sa} and not {sb}",
                f"{sa} and ({sb} or {sc})",
                f"({sa} and {sb}) or ({sa} and {sc})",
            ]
        )
        _, resumen = procesar_texto(fuente)
        assert resumen.procesadas == 6
        assert resumen.con_error == 0
        vals = [r.valor for r in resumen.resultados]
        assert vals[0] == vals[1] == (not (a and b))
        assert vals[2] == vals[3] == (not (a or b))
        assert vals[4] == vals[5] == (a and (b or c))

    def test_anidamiento_profundo_y_programa_largo(self, tmp_path: Path) -> None:
        # 20 niveles de parentesis y negaciones pares
        expr = "true"
        for _ in range(20):
            expr = f"(not {expr})"
        lineas = [expr for _ in range(30)]
        archivo = tmp_path / "largo.bool"
        archivo.write_text("\n".join(lineas), encoding="utf-8")

        resumen = procesar_archivo(archivo, tmp_path / "largo.out")
        assert resumen.procesadas == 30
        assert resumen.evaluadas == 30
        assert all(r.valor is True for r in resumen.resultados)

    def test_ultima_linea_con_error_sin_salto_de_linea(self) -> None:
        _, resumen = procesar_texto("true\nfalse and")
        assert resumen.procesadas == 2
        assert resumen.evaluadas == 1
        assert resumen.con_error == 1
        assert resumen.resultados[0].valor is True
        assert "ERROR sintactico" in (resumen.resultados[1].error or "")

    def test_cli_archivo_con_traza_y_ascii(self, tmp_path: Path) -> None:
        fuente = DIR_EJEMPLOS / "01_basicas_y_precedencia.bool"
        salida = tmp_path / "salida_traza.out"
        proc = _ejecutar_cli(str(fuente), "-o", str(salida), "--traza", "--ascii")
        assert proc.returncode == 0
        assert salida.exists()
        assert "Traza de Evaluacion" in proc.stdout
        assert "Pasos de reduccion" in proc.stdout
        assert "|--" in proc.stdout or "\\--" in proc.stdout

    def test_cli_expresion_directa_y_evaluar_con_traza(self) -> None:
        expr = "(true or false) and not false"
        res_sent, traza = evaluar_con_traza(expr)
        assert res_sent.valor is True
        assert res_sent.error is None
        assert traza.resultado_final is True
        assert traza.total_pasos == 3

        proc = _ejecutar_cli("-e", expr, "--traza", "--ascii")
        assert proc.returncode == 0
        assert "Resultado final:    true" in proc.stdout
        assert "Pasos de reduccion (3 pasos):" in proc.stdout

    def test_cli_salida_por_defecto_crea_archivo_out_junto_al_fuente(self, tmp_path: Path) -> None:
        fuente = tmp_path / "prueba_defecto.bool"
        fuente.write_text("true or false\nnot true\n", encoding="utf-8")

        proc = _ejecutar_cli(str(fuente))
        assert proc.returncode == 0
        salida_esperada = tmp_path / "prueba_defecto.out"
        assert salida_esperada.exists()
        contenido = salida_esperada.read_text(encoding="utf-8")
        assert "[L1] true or false => true" in contenido
        assert "[L2] not true => false" in contenido
        assert "# Resumen: 2 expresiones procesadas | 2 evaluadas | 0 con error" in contenido


# ==============================================================================
# 4. Integracion extremo a extremo de expresiones relacionales (Tarea 37)
# ==============================================================================


class TestIntegracionRelacionalTarea37:
    """Valida el paquete rellang, CLI -m rellang y los 3 escenarios .rel (Integrante 7)."""

    @staticmethod
    def _ejecutar_rellang_cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "rellang", *args],
            cwd=str(RAIZ_REPO),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_paquete_rellang_y_expresion_directa_cli(self) -> None:
        import rellang

        assert hasattr(rellang, "ParserRellang")
        proc = self._ejecutar_rellang_cli("-e", "X = 2; Y = 1; Z = 2; (3X+5Y) <= X/(3-Z)", "--traza", "--ascii")
        assert proc.returncode == 0
        assert "Resultado final:    false" in proc.stdout
        assert "Pasos de reduccion (8 pasos):" in proc.stdout

    def test_escenario1_enunciado_rel_archivo_y_cli_con_traza(self, tmp_path: Path) -> None:
        fuente = DIR_EJEMPLOS / "escenario1_enunciado.rel"
        salida = tmp_path / "escenario1_enunciado.out"

        resumen = procesar_archivo(fuente, salida)
        assert resumen.procesadas == 6
        assert resumen.asignaciones == 2
        assert resumen.evaluadas == 2
        assert resumen.con_error == 2

        contenido = salida.read_text(encoding="utf-8")
        assert "[L5] (3X+5Y) <= X/(3-Z) => false (11 <= 2.0)" in contenido
        assert "[L8] not ((3X+5Y) <= X/(3-Z)) and (2X + Y == 5) or false => true" in contenido
        assert "ERROR semantico: division por cero en 'X/(3-Z)'" in contenido
        assert "ERROR sintactico (col 12): token inesperado '<='" in contenido
        assert "# Resumen: 6 lineas procesadas | 2 asignaciones | 2 expresiones evaluadas | 2 con error" in contenido

        proc = self._ejecutar_rellang_cli(str(fuente), "-o", str(tmp_path / "cli1.out"), "--traza", "--ascii")
        assert proc.returncode == 0
        assert "Resultado final:    false" in proc.stdout
        assert "Resultado final:    true" in proc.stdout

    def test_escenario2_combinado_rel_todos_los_operadores(self, tmp_path: Path) -> None:
        fuente = DIR_EJEMPLOS / "escenario2_combinado.rel"
        salida = tmp_path / "escenario2_combinado.out"

        resumen = procesar_archivo(fuente, salida)
        assert resumen.procesadas == 13
        assert resumen.asignaciones == 2
        assert resumen.evaluadas == 11
        assert resumen.con_error == 0
        contenido = salida.read_text(encoding="utf-8")
        assert "# Resumen: 13 lineas procesadas | 2 asignaciones | 11 expresiones evaluadas | 0 con error" in contenido

    def test_escenario3_errores_rel_tres_clases_y_recuperacion(self, tmp_path: Path) -> None:
        fuente = DIR_EJEMPLOS / "escenario3_errores.rel"
        salida = tmp_path / "escenario3_errores.out"

        resumen = procesar_archivo(fuente, salida)
        assert resumen.procesadas == 10
        assert resumen.asignaciones == 2
        assert resumen.evaluadas == 2
        assert resumen.con_error == 6

        contenido = salida.read_text(encoding="utf-8")
        assert "ERROR semantico: variable 'W' no definida" in contenido
        assert "ERROR semantico: division por cero en 'X/(3-Z)'" in contenido
        assert "ERROR sintactico (col 7): token inesperado '<'" in contenido
        assert "ERROR sintactico (col 13): token inesperado '<='" in contenido
        assert "ERROR lexico (col 7): caracter ilegal '@'" in contenido
        assert "ERROR lexico (col 3): caracter ilegal '$'" in contenido
        assert "[L23] (X + Y) / (3 - Z) == 7 and not false => true" in contenido
