# boollang — Analizador Léxico para Expresiones Booleanas

Implementación del analizador léxico para el lenguaje de expresiones booleanas `boollang`, construido utilizando **PLY (Python Lex-Yacc)** (`ply.lex`).

---

## Características y Funcionalidades

El analizador léxico procesa cadenas de texto y archivos con expresiones booleanas, identificando tokens válidos, manejando comentarios, controlando la posición en línea/columna y recuperándose de errores léxicos sin detener el análisis.

### 1. Tokens Soportados
El analizador reconoce los siguientes tipos de tokens:

| Token | Lexema / Patrón | Descripción |
|---|---|---|
| `TRUE` | `true` | Literal booleano verdadero (únicamente en minúsculas) |
| `FALSE` | `false` | Literal booleano falso (únicamente en minúsculas) |
| `AND` | `and` | Operador lógico de conjunción |
| `OR` | `or` | Operador lógico de disyunción |
| `NOT` | `not` | Operador lógico de negación |
| `LPAREN` | `(` | Paréntesis de apertura para agrupación |
| `RPAREN` | `)` | Paréntesis de cierre para agrupación |
| `PUNTOYCOMA` | `;` | Separador/terminador de sentencia |
| `NEWLINE` | `\n` | Salto de línea / terminador de sentencia |

### 2. Palabras Reservadas y Validación de Identificadores
- Las palabras reservadas son estrictamente en minúsculas: `true`, `false`, `and`, `or`, `not`.
- Cualquier otra palabra o identificador no reservado, así como palabras en mayúsculas o mixtas (como `TRUE`, `False`, `xor`, `ident`), se captura y se reporta como un **error léxico**:

  ```text
  ERROR lexico (col <columna>): palabra no valida '<palabra>'
  ```
- El analizador registra el error y continúa con el análisis de los tokens subsecuentes sin interrumpir el flujo.

### 3. Comentarios y Espacios en Blanco
- **Espacios en blanco:** Los espacios (` `), tabulaciones (`\t`) y retornos de carro (`\r`) son ignorados automáticamente.
- **Comentarios de una línea:** Patrón `//[^\n]*`. Se descartan sin consumir el salto de línea para preservar el conteo exacto de las líneas de código.
- **Comentarios multilínea:** Patrón `/* ... */`. Se descartan y se actualiza el contador de líneas sumando los saltos de línea contenidos en el bloque.

### 4. Conteo de Línea, Columna y Manejo de Errores
- Cada salto de línea incrementa el contador `lineno` del analizador.
- La función auxiliar `find_column(input_text, token)` calcula de forma exacta la columna (base 1) donde inicia cada lexema o error.
- Los caracteres ilegales no reconocidos por ninguna regla son capturados por `t_error`:
  ```text
  ERROR lexico (col <columna>): caracter ilegal '<caracter>'
  ```
  Se avanzan con `skip(1)` para permitir la recuperación inmediata.
- Todos los errores léxicos se registran como instancias de `LexicalError(line, column, message, value)` dentro de la lista `lexer.errors`.

---

## Estructura del Proyecto

```text
boollang/
├── boollang/
│   ├── __init__.py        # Exporta componentes principales del paquete
│   └── lexer.py           # Reglas léxicas, tokens, errores y utilidades
├── tests/
│   ├── __init__.py
│   └── test_lexer.py      # Suite de pruebas unitarias con pytest
├── .gitignore             # Archivos y carpetas ignorados por git
├── README.md              # Documentación técnica del módulo
└── requirements.txt       # Dependencias necesarias (ply, pytest)
```

---

## Requisitos e Instalación

Se requiere Python 3.8 o superior.

Para instalar las dependencias del proyecto:

```bash
pip install -r requirements.txt
```

---

## Ejecución de Pruebas Unitarias

La suite de pruebas cubre reconocimiento de tokens, cálculo de líneas y columnas, comentarios de una y varias líneas, recuperación ante errores léxicos y el caso del escenario de recuperación oficial:

```bash
python -m pytest -v
```

---

## Numeral 1: Verificación de la Gramática (GLC) y E-BNF

- `gramatica.ebnf`: gramática oficial en notación E-BNF (ISO/IEC 14977): Figura 3, nivel de programa y nivel léxico.
- `docs/numeral1/verificacion_glc.md`: demostración de que la Figura 3 es una GLC bien formada (símbolos productivos y alcanzables, sin producciones ε ni ciclos), no ambigua y funcionalmente completa.
- `docs/numeral1/parser.out`: tabla LALR(1) generada por `ply.yacc` con las 8 reglas y sin tabla `precedence`: **15 estados, 0 conflictos**.
- `docs/numeral1/verificar_glc.py`: comprueba automáticamente todas las propiedades y regenera `parser.out`.

```bash
python docs/numeral1/verificar_glc.py
python -m pytest tests/test_gramatica.py -v
```

---

## Ejemplo de Uso en Código

```python
from boollang.lexer import tokenize, build_lexer, find_column

codigo = """// Prueba de expresiones booleanas
true and false;
true and TRUE
"""

tokens, errores = tokenize(codigo)

# Visualizar tokens obtenidos
for tok in tokens:
    print(f"Línea {tok.lineno} -> {tok.type} ({tok.value})")

# Visualizar errores léxicos detectados
for err in errores:
    print(f"Línea {err.line} -> {err.message}")
```

Salida esperada:
```text
Línea 2 -> TRUE (true)
Línea 2 -> AND (and)
Línea 2 -> FALSE (false)
Línea 2 -> PUNTOYCOMA (;)
Línea 2 -> NEWLINE (
)
Línea 3 -> TRUE (true)
Línea 3 -> AND (and)
Línea 3 -> NEWLINE (
)
Línea 3 -> ERROR lexico (col 10): palabra no valida 'TRUE'
```
