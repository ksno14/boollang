"""
boollang - Lenguaje para expresiones booleanas.
"""

from .lexer import build_lexer, lexer, tokens, reserved, find_column, LexicalError, tokenize
from .nodos import Constante, Negacion, Conjuncion, Disyuncion, ExprBool, Sentencia, Programa
from .evaluador import (
    ResultadoSentencia,
    ResumenEvaluacion,
    evaluar,
    evaluar_programa,
    evaluar_sentencia,
    formatear_booleano,
)
from .archivo import (
    ParserNoDisponibleError,
    formatear_salida,
    procesar_archivo,
    procesar_texto,
)

__all__ = [
    'build_lexer',
    'lexer',
    'tokens',
    'reserved',
    'find_column',
    'LexicalError',
    'tokenize',
    'Constante',
    'Negacion',
    'Conjuncion',
    'Disyuncion',
    'ExprBool',
    'Sentencia',
    'Programa',
    'ResultadoSentencia',
    'ResumenEvaluacion',
    'evaluar',
    'evaluar_programa',
    'evaluar_sentencia',
    'formatear_booleano',
    'ParserNoDisponibleError',
    'formatear_salida',
    'procesar_archivo',
    'procesar_texto',
]
