"""
Punto de entrada CLI para ejecutar `python -m boollang <fuente.bool> -o <destino.out>`.

Soporta opciones avanzadas implementadas por el Integrante 6:
- `--traza` (`-t`): Muestra el AST formateado en texto y la traza de evaluación paso a paso.
- `--ascii`: Fuerza el árbol en ASCII puro (la consola lo elige automáticamente
  cuando no soporta los bordes Unicode, p. ej. cp1252 en Windows).
- `--expresion` (`-e`): Evalúa una expresión booleana directamente desde la línea de comandos.
- `--numeral2`: Verifica de forma automática las 3 expresiones del Numeral 2 con árbol y traza.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .archivo import ParserNoDisponibleError, procesar_archivo
from .evaluador import evaluar_con_traza, formatear_booleano
from .nodos import Sentencia
from .traza import (
    formatear_traza,
    parsear_expresion,
    trazar_evaluacion,
    verificar_numeral2,
)

_CARACTERES_ARBOL_UNICODE = "├└│─"


def _estilo_para(stream) -> str:
    """Elige 'unicode' o 'ascii' para el árbol según lo que soporte `stream`.

    Las consolas Windows con codificación heredada (p. ej. cp1252) no pueden
    imprimir los bordes `├──` / `└──` sin lanzar UnicodeEncodeError, así que
    se cae automáticamente a ASCII. Si la codificación es desconocida (p. ej.
    streams capturados en pruebas), se conserva unicode.
    """
    encoding = getattr(stream, "encoding", None)
    if encoding is None:
        return "unicode"
    try:
        _CARACTERES_ARBOL_UNICODE.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return "ascii"
    return "unicode"


def construir_argparser() -> argparse.ArgumentParser:
    """Construye el analizador de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="python -m boollang",
        description="Evalúa expresiones booleanas (.bool), genera archivos .out y muestra trazas de AST.",
    )
    parser.add_argument(
        "fuente",
        nargs="?",
        default=None,
        help="Ruta al archivo fuente (.bool) con las expresiones booleanas.",
    )
    parser.add_argument(
        "-o",
        "--salida",
        dest="salida",
        default=None,
        help="Ruta al archivo destino (.out). Si se omite, usa <fuente>.out.",
    )
    parser.add_argument(
        "-t",
        "--traza",
        dest="traza",
        action="store_true",
        help="Muestra el árbol sintáctico (AST) y la traza detallada de evaluación paso a paso por precedencia.",
    )
    parser.add_argument(
        "--ascii",
        dest="ascii",
        action="store_true",
        help="Fuerza la salida del árbol en ASCII puro (|--, \\--, |), sin caracteres Unicode.",
    )
    parser.add_argument(
        "-e",
        "--expresion",
        dest="expresion",
        default=None,
        help="Evalúa una expresión booleana directa desde la línea de comandos.",
    )
    parser.add_argument(
        "--numeral2",
        "--verificar-numeral2",
        dest="numeral2",
        action="store_true",
        help="Ejecuta la verificación automatizada de las 3 expresiones del Numeral 2 (Tarea 36) con árbol y traza.",
    )
    parser.add_argument(
        "--numeral2-rel",
        dest="numeral2_rel",
        action="store_true",
        help="Ejecuta la verificación automatizada de R1, R2 y R3 (Tarea 37) con entorno X=2, Y=1, Z=2.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Ejecuta la interfaz CLI de boollang y retorna el código de salida."""
    argparser = construir_argparser()
    args = argparser.parse_args(argv)
    estilo = "ascii" if args.ascii else _estilo_para(sys.stdout)

    # 1. Modo Verificación Numeral 2 (Tarea 36 y Tarea 37)
    if args.numeral2_rel:
        entorno_demo = {"X": 2, "Y": 1, "Z": 2}
        exprs = [
            ("R1", "(3X+5Y) <= X/(3-Z)"),
            ("R2", "not ((3X+5Y) <= X/(3-Z)) and (2X + Y == 5) or false"),
        ]
        print("=" * 78)
        print(" VERIFICACIÓN AUTOMATIZADA RELACIONAL — TAREA 37 (Entorno: X=2, Y=1, Z=2)")
        print("=" * 78)
        for clave, expr in exprs:
            traza = trazar_evaluacion(expr, estilo_arbol=estilo, entorno=entorno_demo)
            print(f"\n[{clave}] {expr}")
            print(f"Estado: VÁLIDA | Valor: {formatear_booleano(traza.resultado_final)}")
            print(formatear_traza(traza))
        from .parser import parsear_programa as _parsear_prog_rel

        err_r3 = _parsear_prog_rel("(3X+5Y) <= <= 10").sentencias[0].error
        print("\n[R3] (3X+5Y) <= <= 10")
        print(f"Estado: RECHAZADA CORRECTAMENTE | Error: {err_r3}")
        print("=" * 78)
        return 0

    if args.numeral2:
        resultados = verificar_numeral2(estilo_arbol=estilo)
        print("=" * 78)
        print(" VERIFICACIÓN AUTOMATIZADA — NUMERAL 2 (Integrante 6 / Tarea 36)")
        print("=" * 78)
        for clave in ("E1", "E2"):
            info = resultados[clave]
            print(f"\n[{clave}] {info['texto']}")
            print(f"Estado: {'VÁLIDA' if info['valida'] else 'INVÁLIDA'} | "
                  f"Valor: {formatear_booleano(info['valor'])} | "
                  f"Coincide con esperado: {info['coincide']}")
            print(formatear_traza(info["traza"]))

        info_e3 = resultados["E3"]
        print(f"\n[E3] {info_e3['texto']}")
        print(f"Estado: RECHAZADA CORRECTAMENTE (inválida sintácticamente)")
        print(f"Error detectado: {info_e3['mensaje_error']}")
        print(f"Bloqueo exacto en columna {info_e3['columna_esperada']} ante token '{info_e3['token_bloqueo']}': {info_e3['bloqueo_correcto']}")
        print("=" * 78)
        return 0

    # 2. Modo Expresión directa en línea de comandos
    if args.expresion is not None:
        try:
            if ";" in args.expresion or "=" in args.expresion:
                from .parser import parsear_programa
                from .evaluador import evaluar_programa, ErrorSemantico

                prog = parsear_programa(args.expresion)
                res_prog = evaluar_programa(prog)
                if res_prog.con_error > 0:
                    for r in res_prog.resultados:
                        if r.es_error:
                            print(f"Error: {r.error}", file=sys.stderr)
                    return 1
                ult = res_prog.resultados[-1]
                if args.traza and ult.arbol is not None and not ult.es_asignacion:
                    traza = trazar_evaluacion(
                        ult.arbol,
                        texto_original=ult.texto,
                        estilo_arbol=estilo,
                        entorno=res_prog.entorno,
                    )
                    print(formatear_traza(traza))
                elif ult.valor is not None:
                    print(formatear_booleano(ult.valor))
                else:
                    print(ult.entorno_asignado or "")
                return 0

            if args.traza:
                traza = trazar_evaluacion(args.expresion, estilo_arbol=estilo)
                print(formatear_traza(traza))
            else:
                arbol = parsear_expresion(args.expresion)
                from .evaluador import evaluar
                valor = evaluar(arbol)
                print(formatear_booleano(valor))
            return 0
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    # 3. Modo Archivo fuente
    if args.fuente is not None:
        ruta_salida = (
            args.salida
            if args.salida is not None
            else str(Path(args.fuente).with_suffix(".out"))
        )

        try:
            resumen = procesar_archivo(args.fuente, ruta_salida)
        except FileNotFoundError:
            print(f"Error: no se encontró el archivo fuente '{args.fuente}'.", file=sys.stderr)
            return 1
        except ParserNoDisponibleError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"Error de entrada/salida al procesar '{args.fuente}': {exc}", file=sys.stderr)
            return 1

        print(
            f"Archivo generado: {ruta_salida} "
            f"({resumen.procesadas} procesadas, {resumen.evaluadas} evaluadas, {resumen.con_error} con error)"
        )

        # Si se solicitó la opción --traza, imprimir el desglose detallado
        if args.traza:
            print("\n" + "=" * 78)
            print(f"TRAZA DETALLADA DE EVALUACIÓN (opción --traza): {args.fuente}")
            print("=" * 78)
            entorno_traza: dict[str, int | float] = {}
            for res in resumen.resultados:
                if getattr(res, "es_asignacion", False):
                    asig_txt = res.entorno_asignado or ""
                    if asig_txt.startswith("[Entorno:") and asig_txt.endswith("]"):
                        cuerpo = asig_txt[len("[Entorno:"):-1].strip()
                        for par in cuerpo.split(","):
                            if "=" in par:
                                k, v = par.split("=", 1)
                                k, v = k.strip(), v.strip()
                                try:
                                    entorno_traza[k] = float(v) if ("." in v or "e" in v.lower()) else int(v)
                                except ValueError:
                                    pass
                    print(f"\n[Línea {res.linea}] {res.texto} => {res.entorno_asignado}")
                    continue
                if not res.es_error:
                    try:
                        if res.arbol is not None:
                            sentencia = Sentencia(
                                linea=res.linea, texto=res.texto, arbol=res.arbol
                            )
                            _, traza = evaluar_con_traza(
                                sentencia, estilo_arbol=estilo, entorno=entorno_traza
                            )
                        else:
                            traza = trazar_evaluacion(
                                res.texto, estilo_arbol=estilo, entorno=entorno_traza
                            )
                        print(f"\n[Línea {res.linea}] {res.texto}")
                        if traza is not None:
                            print(formatear_traza(traza))
                    except Exception as exc:
                        print(f"[Línea {res.linea}] No fue posible generar traza: {exc}")
                else:
                    print(f"\n[Línea {res.linea}] {res.texto}")
                    print(f"  => {res.error} (no genera AST)")
            print("=" * 78)

        return 0

    # 4. Ningún argumento provisto
    argparser.print_help(file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
