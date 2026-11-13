"""
Punto de entrada CLI para ejecutar `python -m boollang <fuente.bool> -o <destino.out>`.

Soporta opciones avanzadas implementadas por el Integrante 6:
- `--traza` (`-t`): Muestra el AST formateado en texto y la traza de evaluación paso a paso.
- `--expresion` (`-e`): Evalúa una expresión booleana directamente desde la línea de comandos.
- `--numeral2`: Verifica de forma automática las 3 expresiones del Numeral 2 con árbol y traza.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .archivo import ParserNoDisponibleError, procesar_archivo
from .evaluador import formatear_booleano
from .traza import (
    formatear_traza,
    parsear_expresion,
    trazar_evaluacion,
    verificar_numeral2,
)


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
        help="Ejecuta la verificación automatizada de las 3 expresiones del Numeral 2 con árbol y traza.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Ejecuta la interfaz CLI de boollang y retorna el código de salida."""
    argparser = construir_argparser()
    args = argparser.parse_args(argv)

    # 1. Modo Verificación Numeral 2
    if args.numeral2:
        resultados = verificar_numeral2(con_traza=True)
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
            if args.traza:
                traza = trazar_evaluacion(args.expresion)
                print(formatear_traza(traza))
            else:
                arbol = parsear_expresion(args.expresion)
                from .evaluador import evaluar
                valor = evaluar(arbol)
                print(formatear_booleano(valor))
            return 0
        except SyntaxError as exc:
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
            for res in resumen.resultados:
                if not res.es_error:
                    try:
                        traza = trazar_evaluacion(res.texto)
                        print(f"\n[Línea {res.linea}] {res.texto}")
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
