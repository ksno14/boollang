"""
Analizador sintáctico LALR(1) de boollang construido con ``ply.yacc`` (Integrante 3).

Inspirado en ``pycalcyacc.py`` (reglas ``p_`` de PLY cuyas acciones construyen
el resultado) y en ``calc461.y`` (lista de líneas ``input: /* vacío */ | input
line`` y recuperación por línea ``line: error '\\n' { yyerrok; }``).

Gramática
---------
Reglas 1 a 8: la Figura 3 transcrita tal cual, **sin tabla ``precedence``**.
La precedencia (``not`` > ``and`` > ``or``) y la asociatividad izquierda salen
de la estratificación ExpB > TermB > FactB, como se demuestra en
``docs/numeral1/verificacion_glc.md``::

    (1) ExpB  -> ExpB OR TermB          (5) FactB -> NOT FactB
    (2) ExpB  -> TermB                  (6) FactB -> LPAREN ExpB RPAREN
    (3) TermB -> TermB AND FactB        (7) FactB -> TRUE
    (4) TermB -> FactB                  (8) FactB -> FALSE

Reglas de programa (``gramatica.ebnf`` §2: ``programa = {sentencia}, [expb]``,
``sentencia = [expb], terminador``, ``terminador = ";" | salto_linea``)::

    Programa   -> Sentencias
                | Sentencias ExpB          última expresión sin terminador (EOF)
    Sentencias -> Sentencias Sentencia
                | <vacío>
    Sentencia  -> ExpB NEWLINE
                | ExpB PUNTOYCOMA
                | NEWLINE                  línea vacía o solo con comentarios
                | PUNTOYCOMA               sentencia vacía
                | error NEWLINE            recuperación de errores por línea
                | error PUNTOYCOMA         recuperación de errores por sentencia

Los terminadores no aparecen dentro de las reglas 1 a 8; solo amplían los
conjuntos SIGUIENTE de ExpB, TermB y FactB, así que la tabla sigue teniendo
0 conflictos (lo comprueba ``tests/test_parser.py``).

Recuperación de errores
-----------------------
Ante un token inesperado, ``p_error`` redacta el mensaje y PLY desapila hasta
el estado que puede desplazar ``error``. Luego descarta tokens hasta el
siguiente ``NEWLINE`` o ``;`` y reduce ``Sentencia -> error <terminador>``.
La acción de esa regla llama a ``errok()`` (el ``yyerrok`` de ``calc461.y``)
para que el error de la línea siguiente también se reporte. Dos detalles de
PLY 3.11 que se resuelven aquí, porque difieren de Bison:

* **Estado inicial.** PLY solo usa reducción por defecto cuando un estado
  tiene una única entrada en la tabla. Si el primer token del archivo es
  ``or``, ``and`` o ``)``, la regla ``Sentencias -> <vacío>`` no se reduce,
  el error ocurre con la pila en el estado 0 y PLY descarta el token sin
  desplazar ``error`` (``or true`` se aceptaría como ``true``). Como en Bison,
  el estado 0 recibe esa reducción por defecto (todas sus acciones son esa
  misma reducción) y el error se detecta en un estado que sí admite ``error``.
* **Fin de archivo.** PLY no recupera errores en ``$end``: si la última línea
  no tiene salto de línea y es errónea, ``parse()`` devuelve ``None``. Por eso
  las sentencias se acumulan en el contexto del análisis y el error pendiente
  se registra al terminar, sin perder las líneas anteriores.

Mensajes de error (coinciden con el documento de la Tarea 36)::

    ERROR sintactico (col 29): token inesperado 'or'
    ERROR sintactico: fin de linea inesperado
    ERROR sintactico: fin de linea inesperado, falta ')'

Los errores léxicos no se tratan aquí. ``boollang.archivo.procesar_texto`` les
da prioridad sobre los errores sintácticos en cascada de la misma línea.

Uso::

    from boollang.parser import parsear_programa
    programa = parsear_programa("true and false; not true\\n(true or")
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Union

import ply.yacc as yacc

# Nota: ``from . import lexer`` daría la instancia ``lexer`` que reexporta
# ``boollang/__init__.py``, no el módulo; por eso se importan los nombres.
from .lexer import t_COMMENT_MULTI, t_COMMENT_SINGLE
from .lexer import build_lexer, find_column
from .lexer import tokens as _TOKENS
from .nodos import (
    Conjuncion,
    Constante,
    Disyuncion,
    ExprBool,
    Negacion,
    Programa,
    Sentencia,
)

__all__ = ["ParserBoollang", "parsear_programa"]

_TERMINADORES = frozenset({"NEWLINE", "PUNTOYCOMA"})

# Mismos patrones de comentario que el lexer (PLY toma la regex del docstring).
_RE_COMENTARIO = re.compile(f"{t_COMMENT_MULTI.__doc__}|{t_COMMENT_SINGLE.__doc__}")


class _FlujoTokens:
    """Entrega a ``ply.yacc`` los tokens del lexer del Integrante 1.

    Anota en cada token los datos de la sentencia a la que pertenece, porque
    PLY puede haber leído el token siguiente cuando ejecuta una acción:

    * ``profundidad``: paréntesis abiertos en la sentencia antes del token.
    * ``inicio_sentencia`` y ``linea_sentencia`` (solo en terminadores):
      posición donde empieza el texto de la sentencia y línea de su primer token.

    Tras el último token, ``inicio``, ``linea`` y ``profundidad`` describen la
    sentencia final que no tiene terminador.
    """

    def __init__(self, texto: str):
        self._lexer = build_lexer()
        self._lexer.input(texto)
        self.inicio = 0
        self.linea: Optional[int] = None
        self.profundidad = 0

    @property
    def linea_actual(self) -> int:
        return self._lexer.lineno

    def token(self):
        tok = self._lexer.token()
        if tok is None:
            return None
        tok.profundidad = self.profundidad
        if tok.type in _TERMINADORES:
            tok.inicio_sentencia = self.inicio
            tok.linea_sentencia = self.linea if self.linea is not None else tok.lineno
            self.inicio = tok.lexpos + len(tok.value)
            self.linea = None
            self.profundidad = 0
        else:
            if self.linea is None:
                self.linea = tok.lineno
            if tok.type == "LPAREN":
                self.profundidad += 1
            elif tok.type == "RPAREN" and self.profundidad > 0:
                self.profundidad -= 1
        return tok


@dataclass
class _Contexto:
    """Estado de un análisis en curso (se crea uno por llamada a ``parsear``)."""

    texto: str
    flujo: _FlujoTokens
    sentencias: List[Sentencia] = field(default_factory=list)
    error_pendiente: Optional[str] = None


class _RegistroYacc:
    """``errorlog`` de ``ply.yacc`` que guarda los avisos en vez de imprimirlos."""

    def __init__(self):
        self.avisos: List[str] = []
        self.errores: List[str] = []

    def debug(self, msg, *args, **kwargs):
        pass

    info = debug

    def warning(self, msg, *args, **kwargs):
        self.avisos.append(msg % args)

    def error(self, msg, *args, **kwargs):
        self.errores.append(msg % args)

    critical = error


def _contar(patron: str, avisos: List[str]) -> int:
    return sum(int(n) for n in re.findall(patron, " ".join(avisos)))


class ParserBoollang:
    """Parser LALR(1) de programas boollang.

    Construye las tablas una vez y se puede reutilizar para muchos textos.
    No es reentrante: usar una instancia por hilo.

    Atributos tras la construcción: ``estados``, ``conflictos_sr``,
    ``conflictos_rr`` y ``avisos`` (mensajes de ``ply.yacc``).
    """

    tokens = _TOKENS
    start = "Programa"

    def __init__(self, archivo_tabla: Optional[Union[str, os.PathLike]] = None):
        """``archivo_tabla``: si se indica, escribe ahí la tabla LALR (``parser.out``)."""
        self._ctx: Optional[_Contexto] = None
        registro = _RegistroYacc()
        opciones = dict(
            module=self,
            method="LALR",
            debug=True,  # PLY solo cuenta los conflictos en modo debug
            write_tables=False,
            errorlog=registro,
        )
        if archivo_tabla is None:
            self._parser = yacc.yacc(debuglog=yacc.NullLogger(), **opciones)
        else:
            with open(archivo_tabla, "w", encoding="utf-8") as f:
                self._parser = yacc.yacc(debuglog=yacc.PlyLogger(f), **opciones)

        self.avisos = registro.avisos + registro.errores
        self.conflictos_sr = _contar(r"(\d+) shift/reduce conflicts?", self.avisos)
        self.conflictos_rr = _contar(r"(\d+) reduce/reduce conflicts?", self.avisos)
        self.estados = len(self._parser.action)
        self._reduccion_por_defecto_en_estado_inicial()

    def _reduccion_por_defecto_en_estado_inicial(self) -> None:
        """Hace que el estado 0 reduzca ``Sentencias -> <vacío>`` con cualquier token.

        Ver "Estado inicial" en el docstring del módulo.
        """
        acciones = set(self._parser.action[0].values())
        if len(acciones) != 1 or next(iter(acciones)) >= 0:
            raise RuntimeError(
                "El estado 0 debería tener como única acción reducir Sentencias -> <vacío>"
            )
        self._parser.defaulted_states[0] = acciones.pop()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def parsear(self, texto: str) -> Programa:
        """Analiza un programa completo y devuelve sus sentencias en orden.

        Cada ``Sentencia`` trae su AST o, si hubo error sintáctico, el mensaje;
        las sentencias vacías se omiten. ``texto`` es el código de la sentencia
        sin comentarios ni terminador.
        """
        if not isinstance(texto, str):
            raise TypeError(f"Se esperaba str, se recibió {type(texto).__name__}")
        flujo = _FlujoTokens(texto)
        self._ctx = ctx = _Contexto(texto=texto, flujo=flujo)
        try:
            programa = self._parser.parse(lexer=flujo)
            if ctx.error_pendiente is not None:
                # PLY abandonó en $end: el error es de la última sentencia.
                ctx.sentencias.append(
                    self._sentencia_final(error=ctx.error_pendiente)
                )
                ctx.error_pendiente = None
            return programa if programa is not None else Programa(ctx.sentencias)
        finally:
            self._ctx = None

    # ------------------------------------------------------------------
    # Figura 3: reglas 1 a 8, transcritas tal cual (en este orden, para que
    # PLY las numere igual que la figura y que docs/numeral1/parser.out).
    # ------------------------------------------------------------------

    def p_ExpB_or(self, p):
        'ExpB : ExpB OR TermB'
        p[0] = Disyuncion(p[1], p[3])

    def p_ExpB_TermB(self, p):
        'ExpB : TermB'
        p[0] = p[1]

    def p_TermB_and(self, p):
        'TermB : TermB AND FactB'
        p[0] = Conjuncion(p[1], p[3])

    def p_TermB_FactB(self, p):
        'TermB : FactB'
        p[0] = p[1]

    def p_FactB_not(self, p):
        'FactB : NOT FactB'
        p[0] = Negacion(p[2])

    def p_FactB_paren(self, p):
        'FactB : LPAREN ExpB RPAREN'
        p[0] = p[2]

    def p_FactB_true(self, p):
        'FactB : TRUE'
        p[0] = Constante(True)

    def p_FactB_false(self, p):
        'FactB : FALSE'
        p[0] = Constante(False)

    # ------------------------------------------------------------------
    # Programa y Sentencia
    # ------------------------------------------------------------------

    def p_Programa(self, p):
        'Programa : Sentencias'
        p[0] = Programa(p[1])

    def p_Programa_ultima_sin_terminador(self, p):
        'Programa : Sentencias ExpB'
        p[1].append(self._sentencia_final(arbol=p[2]))
        p[0] = Programa(p[1])

    def p_Sentencias_lista(self, p):
        'Sentencias : Sentencias Sentencia'
        if p[2] is not None:
            p[1].append(p[2])
        p[0] = p[1]

    def p_Sentencias_vacia(self, p):
        'Sentencias :'
        # La lista vive en el contexto para sobrevivir si PLY abandona en $end.
        p[0] = self._ctx.sentencias

    def p_Sentencia_expresion(self, p):
        '''Sentencia : ExpB NEWLINE
                     | ExpB PUNTOYCOMA'''
        p[0] = self._sentencia(p.slice[2], arbol=p[1])

    def p_Sentencia_vacia(self, p):
        '''Sentencia : NEWLINE
                     | PUNTOYCOMA'''
        p[0] = None

    def p_Sentencia_error(self, p):
        '''Sentencia : error NEWLINE
                     | error PUNTOYCOMA'''
        mensaje = self._ctx.error_pendiente or "ERROR sintactico"
        self._ctx.error_pendiente = None
        p.parser.errok()  # yyerrok: la siguiente línea errónea también se reporta
        p[0] = self._sentencia(p.slice[2], error=mensaje)

    def p_error(self, tok):
        self._ctx.error_pendiente = self._mensaje_error(tok)

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------

    def _mensaje_error(self, tok) -> str:
        """Mensaje del primer error de una sentencia (``tok`` es None en EOF)."""
        if tok is None or tok.type == "NEWLINE":
            mensaje = "ERROR sintactico: fin de linea inesperado"
        else:
            col = find_column(self._ctx.texto, tok)
            mensaje = f"ERROR sintactico (col {col}): token inesperado '{tok.value}'"

        if tok is None:
            abiertos = self._ctx.flujo.profundidad
        elif tok.type in _TERMINADORES:
            abiertos = tok.profundidad
        else:
            abiertos = 0  # el problema es el token, no un paréntesis sin cerrar
        if abiertos > 0:
            mensaje += ", falta ')'"
        return mensaje

    def _texto(self, inicio: int, fin: int) -> str:
        return _RE_COMENTARIO.sub("", self._ctx.texto[inicio:fin]).strip()

    def _sentencia(self, terminador, arbol: Optional[ExprBool] = None,
                   error: Optional[str] = None) -> Sentencia:
        """Sentencia que termina en el token ``terminador`` (NEWLINE o ``;``)."""
        return Sentencia(
            linea=terminador.linea_sentencia,
            texto=self._texto(terminador.inicio_sentencia, terminador.lexpos),
            arbol=arbol,
            error=error,
        )

    def _sentencia_final(self, arbol: Optional[ExprBool] = None,
                         error: Optional[str] = None) -> Sentencia:
        """Sentencia que termina en el fin de archivo, sin terminador."""
        flujo = self._ctx.flujo
        return Sentencia(
            linea=flujo.linea if flujo.linea is not None else flujo.linea_actual,
            texto=self._texto(flujo.inicio, len(self._ctx.texto)),
            arbol=arbol,
            error=error,
        )


_parser_por_defecto: Optional[ParserBoollang] = None


def parsear_programa(texto: str) -> Programa:
    """Analiza ``texto`` con un parser compartido (punto de entrada de ``boollang.archivo``)."""
    global _parser_por_defecto
    if _parser_por_defecto is None:
        _parser_por_defecto = ParserBoollang()
    return _parser_por_defecto.parsear(texto)
