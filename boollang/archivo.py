"""
Lectura de archivos fuente `.bool`, orquestación del análisis/evaluación
y generación de archivos destino `.out`.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Union

from .evaluador import ResumenEvaluacion, evaluar_programa
from .lexer import LexicalError, tokenize
from .nodos import Programa, Sentencia


class ParserNoDisponibleError(NotImplementedError):
    """Se lanza cuando `boollang.parser` aún no está disponible y no se inyectó `parser_fn`."""


def _cargar_parser_por_defecto() -> Callable[[str], Any]:
    """Localiza dinámicamente el punto de entrada de `boollang.parser`."""
    try:
        modulo_parser = importlib.import_module("boollang.parser")
    except ModuleNotFoundError as exc:
        if exc.name == "boollang.parser":
            raise ParserNoDisponibleError(
                "El módulo `boollang.parser` (Integrante 3) aún no está disponible. "
                "Asegúrate de integrarlo o inyectar `parser_fn`."
            ) from exc
        raise

    for nombre in ("parsear_programa", "parse_programa", "parsear", "parse"):
        fn = getattr(modulo_parser, nombre, None)
        if callable(fn):
            return fn

    raise ParserNoDisponibleError(
        "El módulo `boollang.parser` no expone una función compatible "
        "(`parsear_programa`, `parse_programa`, `parsear` o `parse`)."
    )


def _limpiar_comentarios_preservando_lineas(contenido: str) -> str:
    """Reemplaza comentarios `//...` y `/*...*/` por espacios conservando saltos de línea."""
    salida: list[str] = []
    i = 0
    n = len(contenido)

    while i < n:
        if contenido[i : i + 2] == "//":
            i += 2
            while i < n and contenido[i] != "\n":
                i += 1
            continue

        if contenido[i : i + 2] == "/*":
            i += 2
            while i < n and contenido[i : i + 2] != "*/":
                if contenido[i] == "\n":
                    salida.append("\n")
                i += 1
            if i < n:
                i += 2
            continue

        salida.append(contenido[i])
        i += 1

    return "".join(salida)


def _agrupar_errores_lexicos(errores_lexicos: Iterable[LexicalError]) -> dict[int, LexicalError]:
    """Retorna el primer `LexicalError` registrado por número de línea."""
    por_linea: dict[int, LexicalError] = {}
    for err in errores_lexicos:
        if err.line not in por_linea:
            por_linea[err.line] = err
    return por_linea


def _normalizar_salida_parser(resultado_parser: Any) -> list[Sentencia]:
    """Convierte el retorno del parser a `list[Sentencia]`."""
    if isinstance(resultado_parser, Programa):
        return list(resultado_parser.sentencias)

    if isinstance(resultado_parser, tuple) and len(resultado_parser) == 2:
        primero, _ = resultado_parser
        if isinstance(primero, Programa):
            return list(primero.sentencias)
        if isinstance(primero, (list, tuple)) and all(isinstance(s, Sentencia) for s in primero):
            return list(primero)

    if isinstance(resultado_parser, (list, tuple)) and all(
        isinstance(s, Sentencia) for s in resultado_parser
    ):
        return list(resultado_parser)

    raise TypeError(
        "El parser debe retornar un `Programa` o una secuencia de `Sentencia`; "
        f"se recibió {type(resultado_parser).__name__}."
    )


def _reconciliar_sentencias(
    contenido: str,
    sentencias_crudas: list[Sentencia],
    errores_lexicos: list[LexicalError],
) -> list[Sentencia]:
    """
    Aplica prioridad de errores léxicos sobre errores sintácticos en cascada
    y completa el texto de cada sentencia si el parser lo dejó vacío.
    """
    errores_por_linea = _agrupar_errores_lexicos(errores_lexicos)
    lineas_sin_comentarios = _limpiar_comentarios_preservando_lineas(contenido).splitlines()

    def texto_linea(num_linea: int) -> str:
        if 1 <= num_linea <= len(lineas_sin_comentarios):
            return lineas_sin_comentarios[num_linea - 1].strip()
        return ""

    reconciliadas: list[Sentencia] = []
    lineas_presentes: set[int] = set()

    for sent in sentencias_crudas:
        lineas_presentes.add(sent.linea)
        texto = sent.texto.strip() if sent.texto else texto_linea(sent.linea)
        err_lex = errores_por_linea.get(sent.linea)

        if err_lex is not None:
            reconciliadas.append(
                Sentencia(
                    linea=sent.linea,
                    texto=texto,
                    arbol=None,
                    error=err_lex.message,
                )
            )
        else:
            reconciliadas.append(
                Sentencia(
                    linea=sent.linea,
                    texto=texto,
                    arbol=sent.arbol,
                    error=sent.error,
                )
            )

    for linea, err_lex in errores_por_linea.items():
        if linea not in lineas_presentes:
            reconciliadas.append(
                Sentencia(
                    linea=linea,
                    texto=texto_linea(linea),
                    arbol=None,
                    error=err_lex.message,
                )
            )

    indexed = list(enumerate(reconciliadas))
    indexed.sort(key=lambda item: (item[1].linea, item[0]))
    return [sent for _, sent in indexed]


def formatear_salida(ruta_fuente: str, resumen: ResumenEvaluacion) -> str:
    """Genera el texto completo del archivo `.out` con encabezado, líneas y resumen."""
    lineas = [f"# Evaluaciones de: {ruta_fuente}"]
    for res in resumen.resultados:
        lineas.append(res.formatear_linea())
    lineas.append(
        f"# Resumen: {resumen.procesadas} expresiones procesadas | "
        f"{resumen.evaluadas} evaluadas | {resumen.con_error} con error"
    )
    return "\n".join(lineas) + "\n"


def procesar_texto(
    contenido: str,
    nombre_fuente: str = "<entrada>",
    parser_fn: Optional[Callable[[str], Any]] = None,
) -> tuple[str, ResumenEvaluacion]:
    """Tokeniza, parsea, evalúa y formatea un programa completo en memoria."""
    _, errores_lexicos = tokenize(contenido)
    parser = parser_fn if parser_fn is not None else _cargar_parser_por_defecto()
    sentencias_crudas = _normalizar_salida_parser(parser(contenido))
    sentencias = _reconciliar_sentencias(contenido, sentencias_crudas, errores_lexicos)
    resumen = evaluar_programa(sentencias)
    salida = formatear_salida(nombre_fuente, resumen)
    return salida, resumen


def procesar_archivo(
    ruta_entrada: Union[str, Path],
    ruta_salida: Union[str, Path],
    parser_fn: Optional[Callable[[str], Any]] = None,
    nombre_fuente: Optional[str] = None,
) -> ResumenEvaluacion:
    """Lee un archivo `.bool`, evalúa sus expresiones y escribe el resultado `.out`."""
    entrada = Path(ruta_entrada)
    salida = Path(ruta_salida)
    contenido = entrada.read_text(encoding="utf-8")

    etiqueta_fuente = (
        nombre_fuente
        if nombre_fuente is not None
        else (ruta_entrada if isinstance(ruta_entrada, str) else str(entrada))
    )
    texto_salida, resumen = procesar_texto(
        contenido,
        nombre_fuente=etiqueta_fuente,
        parser_fn=parser_fn,
    )

    if salida.parent and not salida.parent.exists():
        salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(texto_salida, encoding="utf-8")
    return resumen
