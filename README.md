# boollang — Lenguaje para Expresiones Booleanas (Tarea 36)

Implementación del analizador léxico, gramática formal, evaluador semántico, estructura del Árbol de Sintaxis Abstracta (AST), traza de evaluación por precedencia y suite de pruebas para el lenguaje de expresiones booleanas `boollang`, construido utilizando **Python** y **PLY (Python Lex-Yacc)**.

---

## Características y Funcionalidades

El procesador de expresiones booleanas procesa cadenas de texto y archivos con expresiones booleanas, identificando tokens válidos, manejando comentarios, controlando la posición en línea/columna, construyendo el AST, evaluando semánticamente y reportando errores léxicos o sintácticos con recuperación por línea.

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
│   ├── __main__.py        # CLI: python -m boollang fuente.bool -o destino.out [--traza] [--ascii]
│   ├── archivo.py         # Lectura .bool, conciliación de errores y escritura .out
│   ├── evaluador.py       # Evaluador semántico booleano y resumen
│   ├── lexer.py           # Reglas léxicas, tokens, errores y utilidades (Integrante 1)
│   ├── nodos.py           # Nodos del Árbol de Sintaxis Abstracta (AST) (Integrante 6)
│   └── traza.py           # Formateador de árbol y traza por precedencia (Integrante 6)
├── docs/
│   ├── numeral1/          # Verificación formal GLC, E-BNF y parser.out (Integrante 2)
│   └── numeral2/          # Derivaciones, árboles y bloqueo de E3 (Integrante 5)
├── tests/
│   ├── __init__.py
│   ├── test_evaluador.py  # Pruebas del evaluador, CLI y archivo (Integrante 4)
│   ├── test_gramatica.py  # Pruebas de verificación de la GLC (Integrante 2)
│   ├── test_lexer.py      # Pruebas unitarias del lexer (Integrante 1)
│   ├── test_numeral2.py   # Pruebas de derivaciones del Numeral 2 (Integrante 5)
│   └── test_traza.py      # Pruebas de AST, traza de evaluación y CLI (Integrante 6)
├── .gitignore             # Archivos y carpetas ignorados por git
├── gramatica.ebnf         # Gramática oficial en notación E-BNF (Figura 2)
├── README.md              # Documentación técnica integral
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

## Ejecución de la Suite Completa de Pruebas

La suite de pruebas contiene **100 pruebas unitarias automatizadas** que cubren el lexer, gramática formal, derivaciones del Numeral 2, evaluador, AST, traza y CLI:

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

## Numeral 2: Tres Expresiones, Derivaciones y Árboles

- `docs/numeral2/derivaciones.md`: dos expresiones válidas (E1 → `true`, E2 → `false`) y una inválida (E3, se bloquea en `not or`, columna 29). Incluye la derivación más a la izquierda paso a paso, el árbol sintáctico, el AST evaluado y la argumentación formal de por qué se aceptan o se rechazan.
- `docs/numeral2/derivaciones.py`: genera y comprueba todo lo anterior reutilizando el lexer, la verificación del Numeral 1 y el evaluador del proyecto.

```bash
python docs/numeral2/derivaciones.py
python -m pytest tests/test_numeral2.py -v
```

---

## Integrante 6: Estructura del Árbol (AST) y Traza de Evaluación

El módulo desarrollado por el **Integrante 6** comprende:
1. **Definición de nodos del AST (`boollang/nodos.py`):**
   - `Constante(valor: bool)`: nodo hoja literal (`true` o `false`).
   - `Negacion(op: ExprBool)`: nodo unario para operador lógico `not`.
   - `Conjuncion(izq: ExprBool, der: ExprBool)`: nodo binario para operador lógico `and`.
   - `Disyuncion(izq: ExprBool, der: ExprBool)`: nodo binario para operador lógico `or`.
   - `Sentencia(linea, texto, arbol=None, error=None)` y `Programa(sentencias)`.
   - Propiedades de introspección: `hijos()`, `nombre_op`, `prioridad` formal (`not`: 3 > `and`: 2 > `or`: 1 > `const`: 4) y `a_texto()` (reconstrucción textual con uso mínimo de paréntesis según asociatividad a la izquierda).

2. **Formateador visual en texto (`formatear_arbol` en `boollang/traza.py`):**
   - Muestra el árbol jerárquico usando caracteres de caja Unicode (`├──`, `└──`, `│   `) o ASCII (`|--`, `\--`).
   - Anota opcionalmente el valor booleano evaluado `[true]` o `[false]` de cada subárbol.
   - Ejemplo para E1 (`not (true and false) or false and not false`):
     ```text
     or   [true]
     ├── not   [true]
     │   └── and   [false]
     │       ├── true   [true]
     │       └── false   [false]
     └── and   [false]
         ├── false   [false]
         └── not   [true]
             └── false   [false]
     ```

3. **Motor de traza paso a paso (`trazar_evaluacion` y `formatear_traza`):**
   - Modela la evaluación reducible paso a paso respetando estrictamente:
     * Los subárboles entre paréntesis primero (FactB).
     * Precedencia de operadores dentro de cada nivel: `not` > `and` > `or`.
     * Asociatividad a la izquierda para operadores de igual precedencia.
   - Cada paso registra: número de paso, operador aplicado, subexpresión evaluada, valor booleano resultante y estado simplificado de la expresión completa.

4. **Verificación automatizada del Numeral 2 (`verificar_numeral2`):**
   - Comprueba automáticamente las 3 expresiones del Numeral 2 (E1, E2 y E3):
     * **E1:** Válida, evalúa a `true` en 5 pasos de reducción.
     * **E2:** Válida, evalúa a `false` en 10 pasos de reducción.
     * **E3:** Inválida, detecta formalmente el error de sintaxis en el token `'or'` en la columna 29.

5. **Opciones avanzadas en la Interfaz CLI (`boollang/__main__.py`):**
   - **Opción `--traza` (`-t`):** Imprime el AST visual y el desglose de pasos al procesar un archivo o expresión. Reutiliza el AST ya construido durante el análisis del archivo (sin reparsear cada línea); si no está disponible, recurre a un reparseo como respaldo.
   - **Opción `--ascii`:** Fuerza la salida del árbol en ASCII puro (`|--`, `\--`, `|`). Si no se indica, la CLI elige automáticamente entre `unicode` y `ascii` según la codificación de la consola (p. ej. `cp1252` en Windows cae a ASCII para evitar `UnicodeEncodeError`).
   - **Opción `-e` / `--expresion`:** Evalúa directamente una expresión desde la terminal.
   - **Opción `--numeral2`:** Ejecuta la verificación completa del Numeral 2 con sus árboles y trazas.

### Ejemplos de uso del CLI con `--traza` y `--numeral2`:

```bash
# 1. Evaluar expresión directa con traza completa y árbol:
python -m boollang -e "not (true and false) or false and not false" --traza

# 2. Verificar automáticamente las 3 expresiones del Numeral 2:
python -m boollang --numeral2

# 3. Procesar archivo .bool con generación de .out y traza detallada en consola:
python -m boollang archivo.bool -o resultado.out --traza
```

Salida generada por `--traza`:
```text
==============================================================================
Traza de Evaluacion (Precedencia: not > and > or)
==============================================================================
Expresion original: not (true and false) or false and not false
Resultado final:    true

Arbol Sintactico (AST) con valores por subexpresion:
or   [true]
├── not   [true]
│   └── and   [false]
│       ├── true   [true]
│       └── false   [false]
└── and   [false]
    ├── false   [false]
    └── not   [true]
        └── false   [false]

Pasos de reduccion (5 pasos):
  1. [AND] true and false => false
     Estado: not false or false and not false
  2. [NOT] not false => true
     Estado: true or false and not false
  3. [NOT] not false => true
     Estado: true or false and true
  4. [AND] false and true => false
     Estado: true or false
  5. [OR ] true or false => true
     Estado: true
==============================================================================
```

### Pruebas unitarias del Integrante 6:
```bash
python -m pytest tests/test_traza.py -v
```

---

## Ejemplo de Uso en Código Python

```python
from boollang import parsear_expresion, formatear_arbol, trazar_evaluacion, formatear_traza

# 1. Analizar expresión y construir AST
expresion = "not (true and false) or false and not false"
arbol = parsear_expresion(expresion)

# 2. Formatear visualmente el AST con sus valores
print(formatear_arbol(arbol, con_valores=True))

# 3. Generar la traza de evaluación paso a paso
traza = trazar_evaluacion(arbol)
print(formatear_traza(traza))
```
