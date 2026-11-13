"""
Punto de entrada CLI para ejecutar `python -m boollang <fuente.bool> -o <destino.out>`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .archivo import ParserNoDisponibleError, procesar_archivo


def construir_argparser() -> argparse.ArgumentParser:
    """Construye el analizador de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="python -m boollang",
        description="Evalúa un archivo fuente de expresiones booleanas (.bool) y genera un archivo .out.",
    )
    parser.add_argument(
        "fuente",
        help="Ruta al archivo fuente (.bool) con las expresiones booleanas.",
    )
    parser.add_argument(
        "-o",
        "--salida",
        dest="salida",
        default=None,
        help="Ruta al archivo destino (.out). Si se omite, usa <fuente>.out.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Ejecuta la interfaz CLI de boollang y retorna el código de salida."""
    argparser = construir_argparser()
    args = argparser.parse_args(argv)

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
