# boollang / rellang — Lenguajes para Expresiones Booleanas y Proposicionales Relacionales (Tareas 36 y 37)

Implementación integral de analizador léxico (`ply.lex`), gramáticas formales E-BNF, analizador sintáctico LALR(1) (`ply.yacc` sin tabla `precedence`), Árbol de Sintaxis Abstracta (AST), evaluador semántico con entorno de variables, trazador paso a paso y suite automatizada para:

- **Tarea 36 (`boollang`):** Lenguaje de expresiones booleanas de la Figura 3 (`true`, `false`, `not`, `and`, `or`, paréntesis, comentarios y recuperación de errores por línea).
- **Tarea 37 (`rellang` / extensión relacional):** Extensión combinando la Figura 3 con la calculadora aritmética **LP02 (`CalculadoraEnFLEX_BISON_y_EnPLY`)** para reconocer y evaluar **expresiones proposicionales relacionales** como `(3X+5Y) <= X/(3-Z)`, asignaciones (`X = 2; Y = 1; Z = 2;`), multiplicación implícita (`3X`, `2(X+1)`, `-2X`, `6/2X`), operadores relacionales (`<=`, `>=`, `==`, `!=`, `<`, `>`) y detección de errores semánticos (división por cero y variable no definida).

---

## Jerarquía de Precedencia (7 Niveles, sin tabla `%precedence`)

| Nivel | Categoría | Operadores / Formas | Asociatividad | No terminal |
| :---: |---|---| :---: |---|
| **1** | Disyunción lógica | `or` | Izquierda | `ExpB` |
| **2** | Conjunción lógica | `and` | Izquierda | `TermB` |
| **3** | Negación lógica | `not` | Derecha (prefijo) | `FactB` |
| **4** | Comparación relacional | `<=`, `>=`, `==`, `!=`, `<`, `>` | No asociativo | `ExpRel` |
| **5** | Aditivo aritmético | `+`, `-` | Izquierda | `ExpA` |
| **6** | Multiplicativo aritmético | `*`, `/` | Izquierda | `TermA` |
| **7** | Unario, implícito y átomos | `-` unario, `NUMBER ID`, `NUMBER (ExpA)`, `(ExpA)`, `NUMBER`, `ID` | Derecha (prefijo) | `FactA` |

---

## Estructura del Proyecto

```text
boollang/
├── boollang/                   # Paquete núcleo (retrocompatible Tarea 36 + Tarea 37)
│   ├── __init__.py             # Exporta API unificada (ParserBoollang, ParserRellang, evaluar, ...)
│   ├── __main__.py             # CLI (-m boollang)
│   ├── lexer.py                # Scanner PLY: 22 tokens + comentarios + LexicalError
│   ├── nodos.py                # 10 clases AST (@dataclass): booleanos, aritméticos, relacionales y asignación
│   ├── parser.py               # Parser LALR(1): 42 reglas, 63 estados, 0 conflictos, recuperación errok()
│   ├── evaluador.py            # Evaluador semántico, entorno de variables y ErrorSemantico
│   ├── archivo.py              # Lectura .bool / .rel, conciliación léxico>sintáctico y escritura .out
│   └── traza.py                # Árbol AST con valores intermedios y traza paso a paso
├── rellang/                    # Paquete dedicado para Tarea 37 (-m rellang)
│   ├── __init__.py             # Reexporta la API completa para expresiones relacionales
│   └── ...                     # Módulos espejo (__main__, lexer, nodos, parser, evaluador, archivo, traza)
├── docs/
│   ├── numeral1/               # Verificación GLC Figura 3 y extendida G_rel (47 estados, 0 conflictos)
│   └── numeral2/               # Derivaciones =>lm (E1-E3 y R1-R3), árboles y bloqueos sintácticos
├── ejemplos/                   # Escenarios de prueba .bool (Tarea 36) y .rel (Tarea 37) con sus .out
├── tests/                      # 209 pruebas automatizadas en 7 módulos pytest
├── gramatica.ebnf              # Gramática oficial Tarea 36 (W3C Figura 2 + ISO/IEC 14977)
├── gramatica_relacional.ebnf   # Gramática extendida Tarea 37 (7 niveles)
└── requirements.txt            # ply>=3.11, pytest
```

---

## Instalación y Uso

```bash
pip install -r requirements.txt

# Tarea 37: evaluar archivo .rel y generar .out
python -m rellang ejemplos/escenario1_enunciado.rel -o ejemplos/escenario1_enunciado.out

# Mostrar AST con valores numéricos/booleanos intermedios y traza de reducción
python -m rellang ejemplos/escenario1_enunciado.rel --traza
python -m rellang -e "X = 2; Y = 1; Z = 2; (3X+5Y) <= X/(3-Z)" --traza

# Verificaciones formales Numeral 1 y Numeral 2 (relacional)
python docs/numeral1/verificar_glc_relacional.py
python docs/numeral2/derivaciones_relacionales.py
python -m rellang --numeral2-rel

# Retrocompatibilidad Tarea 36 (.bool)
python -m boollang ejemplos/01_basicas_y_precedencia.bool -o ejemplos/01_basicas_y_precedencia.out

# Ejecutar la suite completa de pruebas
python -m pytest tests -v
```
