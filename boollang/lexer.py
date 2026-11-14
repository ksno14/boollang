"""
Analizador léxico para expresiones booleanas y proposicionales relacionales (boollang / rellang).
Implementado con PLY (ply.lex) siguiendo las especificaciones de las Tareas 36 y 37.
"""

import ply.lex as lex


class LexicalError:
    """Representa un error léxico detectado durante el análisis."""

    def __init__(self, line: int, column: int, message: str, value: str):
        self.line = line
        self.column = column
        self.message = message
        self.value = value

    def __repr__(self):
        return f"LexicalError(line={self.line}, column={self.column}, message={self.message!r}, value={self.value!r})"

    def __str__(self):
        return self.message

    def __eq__(self, other):
        if isinstance(other, LexicalError):
            return (self.line, self.column, self.message, self.value) == (
                other.line,
                other.column,
                other.message,
                other.value,
            )
        return False


# Lista oficial de tokens para el lenguaje (Tarea 36 booleana + Tarea 37 relacional/aritmética)
tokens = (
    # Palabras reservadas booleanas (Tarea 36)
    'TRUE',
    'FALSE',
    'AND',
    'OR',
    'NOT',
    # Delimitadores y separadores
    'LPAREN',
    'RPAREN',
    'PUNTOYCOMA',
    'NEWLINE',
    # Operadores aritméticos (Tarea 37 - Calculadora LP02)
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',
    # Operadores relacionales (Tarea 37)
    'LE',
    'GE',
    'EQ',
    'NE',
    'LT',
    'GT',
    # Asignación, literales numéricos e identificadores de variables (Tarea 37)
    'ASSIGN',
    'NUMBER',
    'ID',
)

# Diccionario de palabras reservadas (solo en minúscula)
reserved = {
    'true': 'TRUE',
    'false': 'FALSE',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
}

# Palabras explícitamente inválidas (variantes en mayúsculas de reservadas u operadores no soportados)
invalid_words = {
    'TRUE',
    'FALSE',
    'AND',
    'OR',
    'NOT',
    'True',
    'False',
    'And',
    'Or',
    'Not',
    'xor',
    'XOR',
    'nand',
    'NAND',
    'nor',
    'NOR',
    'BADWORD',
    'invalida',
}

# Expresiones regulares para operadores relacionales de dos caracteres (prioridad por longitud)
t_LE = r'<='
t_GE = r'>='
t_EQ = r'=='
t_NE = r'!='

# Expresiones regulares para operadores relacionales, asignación y aritméticos de un carácter
t_LT = r'<'
t_GT = r'>'
t_ASSIGN = r'='
t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'

# Expresiones regulares para delimitadores simples
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_PUNTOYCOMA = r';'

# Caracteres ignorados (espacios y tabulaciones, retorno de carro)
t_ignore = ' \t\r'


def find_column(input_text: str, token) -> int:
    """
    Calcula la columna (base 1) de un token o índice lexpos dado en el texto de entrada.
    """
    if hasattr(token, 'lexpos'):
        pos = token.lexpos
    else:
        pos = int(token)
    line_start = input_text.rfind('\n', 0, pos) + 1
    return (pos - line_start) + 1


# Regla para ignorar comentarios multilínea (/* ... */)
def t_COMMENT_MULTI(t):
    r'/\*[\s\S]*?\*/'
    t.lexer.lineno += t.value.count('\n')
    # No retorna token: se ignora


# Regla para ignorar comentarios de una sola línea (// ...)
def t_COMMENT_SINGLE(t):
    r'//[^\n]*'
    # No retorna token: se ignora. No consume el '\n' para que t_NEWLINE maneje el salto de línea.
    pass


# Regla para constantes numéricas enteras y de punto flotante (Tarea 37)
def t_NUMBER(t):
    r'\d+(?:\.\d+)?'
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t


# Regla para saltos de línea y conteo de líneas
def t_NEWLINE(t):
    r'\n'
    t.lexer.lineno += 1
    return t


# Regla para palabras reservadas, identificadores de variables (ID) y palabras no válidas
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    if t.value in reserved:
        t.type = reserved[t.value]
        return t
    if t.value in invalid_words or t.value.lower() in reserved:
        col = find_column(t.lexer.lexdata, t)
        msg = f"ERROR lexico (col {col}): palabra no valida '{t.value}'"
        error = LexicalError(
            line=t.lexer.lineno,
            column=col,
            message=msg,
            value=t.value,
        )
        if hasattr(t.lexer, 'errors'):
            t.lexer.errors.append(error)
        # Se omite el token (skip) sin detener el análisis
        return None
    t.type = 'ID'
    return t


# Manejo de caracteres ilegales
def t_error(t):
    col = find_column(t.lexer.lexdata, t)
    msg = f"ERROR lexico (col {col}): caracter ilegal '{t.value[0]}'"
    error = LexicalError(
        line=t.lexer.lineno,
        column=col,
        message=msg,
        value=t.value[0],
    )
    if hasattr(t.lexer, 'errors'):
        t.lexer.errors.append(error)
    t.lexer.skip(1)


def build_lexer(**kwargs):
    """
    Construye y retorna una nueva instancia del analizador léxico.
    Inicializa la lista de errores para facilitar su consulta.
    """
    new_lexer = lex.lex(**kwargs)
    new_lexer.errors = []
    return new_lexer


# Instancia por defecto a nivel de módulo
lexer = build_lexer()


def tokenize(data: str, lexer_instance=None):
    """
    Tokeniza un texto de entrada completo.
    Retorna una tupla (lista_tokens, lista_errores).
    """
    lx = lexer_instance if lexer_instance is not None else build_lexer()
    lx.errors = []
    lx.lineno = 1
    lx.input(data)
    tokens_list = []
    while True:
        tok = lx.token()
        if not tok:
            break
        tokens_list.append(tok)
    return tokens_list, list(lx.errors)
