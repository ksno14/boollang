# Numeral 2: tres expresiones, derivaciones más a la izquierda y árboles

**Tarea 36 · Lenguaje `boollang` · Integrante 5**

Este documento toma tres expresiones booleanas medianamente complejas: dos **válidas** (E1, E2) y una **inválida** (E3). Para cada una se hace lo siguiente:

- se construye **paso a paso** su derivación más a la izquierda con las producciones P1 a P8 de la Figura 3,
- se dibuja su **árbol sintáctico**,
- y se argumenta **formalmente** por qué la gramática acepta E1 y E2 y en qué **token exacto** se bloquea E3 (`not or`).

Todo lo que aparece aquí se genera y se comprueba de forma automática, y se reutiliza el trabajo del resto del equipo sin modificarlo:

| Archivo | Contenido |
|---|---|
| [`derivaciones.py`](derivaciones.py) | Genera las derivaciones a partir del árbol de PLY, dibuja los árboles, localiza el bloqueo de E3 |
| [`salida_numeral2.txt`](salida_numeral2.txt) | Salida completa del script (fuente de las tablas de este documento) |
| [`../../tests/test_numeral2.py`](../../tests/test_numeral2.py) | 14 pruebas `pytest` sobre E1, E2 y E3 |

| Se reutiliza | De | Para |
|---|---|---|
| `boollang/lexer.py` | Integrante 1 | Tokenizar E1 a E3 y calcular la columna del error |
| `docs/numeral1/verificar_glc.py` | Integrante 2 | Producciones P1 a P8, parser LALR(1) sin `precedence`, conteo de árboles, PRIMEROS |
| `boollang/nodos.py`, `boollang/evaluador.py` | Integrante 4 | Construir el AST y evaluar E1 y E2 con el evaluador real del proyecto |

> Las tres expresiones son las líneas **L2, L3 y L4** del ejemplo `escenario3_recuperacion.bool` del documento de la Tarea 36. Así, el Numeral 2 coincide con la salida esperada del programa (`=> true`, `=> false`, `ERROR sintactico (col 29): token inesperado 'or'`). El Integrante 7 puede copiarlas tal cual en `ejemplos/expresiones_numeral2.bool`.

---

## 0. Gramática de referencia (Figura 3)

| # | Producción | | # | Producción |
|---|---|---|---|---|
| P1 | ExpB → ExpB **or** TermB | | P5 | FactB → **not** FactB |
| P2 | ExpB → TermB | | P6 | FactB → **(** ExpB **)** |
| P3 | TermB → TermB **and** FactB | | P7 | FactB → **true** |
| P4 | TermB → FactB | | P8 | FactB → **false** |

En cada paso de una **derivación más a la izquierda** ($\Rightarrow_{lm}$) se reemplaza el no terminal que está **más a la izquierda** en la forma sentencial. Como G no es ambigua (Numeral 1, §6), cada cadena de L(G) tiene **exactamente una** derivación más a la izquierda. La derivación que se muestra para cada expresión es, por tanto, **la** derivación, y no solo una de varias posibles.

---

## 1. E1 (válida)

```
E1 = not (true and false) or false and not false
```

**Tokens (11):** `not ( true and false ) or false and not false`. Todas son palabras reservadas en minúscula y no hay errores léxicos.

**Lectura esperada por precedencia** (not > and > or): `( not (true and false) ) or ( false and (not false) )`.

### 1.1 Derivación más a la izquierda (15 pasos)

| Paso | Prod. | Forma sentencial |
|---:|:---:|---|
| 0 | | ExpB |
| 1 | P1 | **ExpB** or TermB |
| 2 | P2 | **TermB** or TermB |
| 3 | P4 | **FactB** or TermB |
| 4 | P5 | not **FactB** or TermB |
| 5 | P6 | not ( **ExpB** ) or TermB |
| 6 | P2 | not ( **TermB** ) or TermB |
| 7 | P3 | not ( **TermB** and FactB ) or TermB |
| 8 | P4 | not ( **FactB** and FactB ) or TermB |
| 9 | P7 | not ( true and **FactB** ) or TermB |
| 10 | P8 | not ( true and false ) or **TermB** |
| 11 | P3 | not ( true and false ) or **TermB** and FactB |
| 12 | P4 | not ( true and false ) or **FactB** and FactB |
| 13 | P8 | not ( true and false ) or false and **FactB** |
| 14 | P5 | not ( true and false ) or false and not **FactB** |
| 15 | P8 | not ( true and false ) or false and not false |

En **negrita**, el no terminal más a la izquierda, que es el que se reemplaza en el paso siguiente.
Producciones usadas: P1×1, P2×2, P3×2, P4×3, P5×2, P6×1, P7×1, P8×3, es decir, **las 8 producciones**.

### 1.2 Árbol sintáctico (derivación concreta) anotado con valores

```
ExpB = true
├── ExpB = true
│   └── TermB = true
│       └── FactB = true
│           ├── not
│           └── FactB = false
│               ├── (
│               ├── ExpB = false
│               │   └── TermB = false
│               │       ├── TermB = true
│               │       │   └── FactB = true
│               │       │       └── true
│               │       ├── and
│               │       └── FactB = false
│               │           └── false
│               └── )
├── or
└── TermB = false
    ├── TermB = false
    │   └── FactB = false
    │       └── false
    ├── and
    └── FactB = true
        ├── not
        └── FactB = false
            └── false
```

### 1.3 AST (`boollang.nodos`) y valor

```
or   [true]                      Disyuncion(
├── not   [true]                   Negacion(Conjuncion(Constante(True), Constante(False))),
│   └── and   [false]              Conjuncion(Constante(False), Negacion(Constante(False))))
│       ├── true   [true]
│       └── false   [false]
└── and   [false]
    ├── false   [false]
    └── not   [true]
        └── false   [false]
```

**Valor: `true`**: `not (true and false)` = `not false` = true, y `true or …` = true. `boollang.evaluador.evaluar` (Integrante 4) da el mismo resultado.

---

## 2. E2 (válida)

```
E2 = not not (false or true and not false) and (true or false) and not (true and true)
```

**Tokens (23):** `not not ( false or true and not false ) and ( true or false ) and not ( true and true )`. No hay errores léxicos.

**Lectura esperada:** `( ( not not (false or (true and not false)) ) and (true or false) ) and ( not (true and true) )`. El `and` es **asociativo por la izquierda**, la doble negación se anida hacia la derecha y dentro del primer paréntesis el `and` va antes que el `or`.

### 2.1 Derivación más a la izquierda (30 pasos)

| Paso | Prod. | Forma sentencial |
|---:|:---:|---|
| 0 | | ExpB |
| 1 | P2 | **TermB** |
| 2 | P3 | **TermB** and FactB |
| 3 | P3 | **TermB** and FactB and FactB |
| 4 | P4 | **FactB** and FactB and FactB |
| 5 | P5 | not **FactB** and FactB and FactB |
| 6 | P5 | not not **FactB** and FactB and FactB |
| 7 | P6 | not not ( **ExpB** ) and FactB and FactB |
| 8 | P1 | not not ( **ExpB** or TermB ) and FactB and FactB |
| 9 | P2 | not not ( **TermB** or TermB ) and FactB and FactB |
| 10 | P4 | not not ( **FactB** or TermB ) and FactB and FactB |
| 11 | P8 | not not ( false or **TermB** ) and FactB and FactB |
| 12 | P3 | not not ( false or **TermB** and FactB ) and FactB and FactB |
| 13 | P4 | not not ( false or **FactB** and FactB ) and FactB and FactB |
| 14 | P7 | not not ( false or true and **FactB** ) and FactB and FactB |
| 15 | P5 | not not ( false or true and not **FactB** ) and FactB and FactB |
| 16 | P8 | not not ( false or true and not false ) and **FactB** and FactB |
| 17 | P6 | not not ( false or true and not false ) and ( **ExpB** ) and FactB |
| 18 | P1 | not not ( false or true and not false ) and ( **ExpB** or TermB ) and FactB |
| 19 | P2 | not not ( false or true and not false ) and ( **TermB** or TermB ) and FactB |
| 20 | P4 | not not ( false or true and not false ) and ( **FactB** or TermB ) and FactB |
| 21 | P7 | not not ( false or true and not false ) and ( true or **TermB** ) and FactB |
| 22 | P4 | not not ( false or true and not false ) and ( true or **FactB** ) and FactB |
| 23 | P8 | not not ( false or true and not false ) and ( true or false ) and **FactB** |
| 24 | P5 | not not ( false or true and not false ) and ( true or false ) and not **FactB** |
| 25 | P6 | not not ( false or true and not false ) and ( true or false ) and not ( **ExpB** ) |
| 26 | P2 | not not ( false or true and not false ) and ( true or false ) and not ( **TermB** ) |
| 27 | P3 | not not ( false or true and not false ) and ( true or false ) and not ( **TermB** and FactB ) |
| 28 | P4 | not not ( false or true and not false ) and ( true or false ) and not ( **FactB** and FactB ) |
| 29 | P7 | not not ( false or true and not false ) and ( true or false ) and not ( true and **FactB** ) |
| 30 | P7 | not not ( false or true and not false ) and ( true or false ) and not ( true and true ) |

Producciones usadas: P1×2, P2×4, P3×4, P4×6, P5×4, P6×3, P7×4, P8×3, es decir, **las 8 producciones**.

### 2.2 Árbol sintáctico anotado con valores

```
ExpB = false
└── TermB = false
    ├── TermB = true
    │   ├── TermB = true
    │   │   └── FactB = true
    │   │       ├── not
    │   │       └── FactB = false
    │   │           ├── not
    │   │           └── FactB = true
    │   │               ├── (
    │   │               ├── ExpB = true
    │   │               │   ├── ExpB = false
    │   │               │   │   └── TermB = false
    │   │               │   │       └── FactB = false
    │   │               │   │           └── false
    │   │               │   ├── or
    │   │               │   └── TermB = true
    │   │               │       ├── TermB = true
    │   │               │       │   └── FactB = true
    │   │               │       │       └── true
    │   │               │       ├── and
    │   │               │       └── FactB = true
    │   │               │           ├── not
    │   │               │           └── FactB = false
    │   │               │               └── false
    │   │               └── )
    │   ├── and
    │   └── FactB = true
    │       ├── (
    │       ├── ExpB = true
    │       │   ├── ExpB = true
    │       │   │   └── TermB = true
    │       │   │       └── FactB = true
    │       │   │           └── true
    │       │   ├── or
    │       │   └── TermB = false
    │       │       └── FactB = false
    │       │           └── false
    │       └── )
    ├── and
    └── FactB = false
        ├── not
        └── FactB = true
            ├── (
            ├── ExpB = true
            │   └── TermB = true
            │       ├── TermB = true
            │       │   └── FactB = true
            │       │       └── true
            │       ├── and
            │       └── FactB = true
            │           └── true
            └── )
```

### 2.3 AST (`boollang.nodos`) y valor

```
and   [false]
├── and   [true]
│   ├── not   [true]
│   │   └── not   [false]
│   │       └── or   [true]
│   │           ├── false   [false]
│   │           └── and   [true]
│   │               ├── true   [true]
│   │               └── not   [true]
│   │                   └── false   [false]
│   └── or   [true]
│       ├── true   [true]
│       └── false   [false]
└── not   [false]
    └── and   [true]
        ├── true   [true]
        └── true   [true]
```

**Valor: `false`**: el último factor es `not (true and true)` = false, y `… and false` = false. El evaluador del proyecto da el mismo resultado.

---

## 3. Por qué la gramática acepta E1 y E2 (argumento formal)

**Proposición.** $E1, E2 \in L(G)$ y cada una tiene un único árbol de derivación.

*Prueba.*

1. **Pertenencia.** Las tablas 1.1 y 2.1 son derivaciones $\text{ExpB} \Rightarrow_{lm}^{15} E1$ y $\text{ExpB} \Rightarrow_{lm}^{30} E2$. En cada paso, (a) el símbolo reemplazado es un no terminal de la forma sentencial, (b) es el **más a la izquierda** y (c) se sustituye por el lado derecho de una producción $P_k \in P$ cuyo lado izquierdo es ese no terminal. La última forma sentencial está formada solo por terminales y es exactamente la cadena de tokens. Por definición de $L(G) = \{w \in \Sigma^* \mid \text{ExpB} \Rightarrow^* w\}$, ambas pertenecen al lenguaje. `test_derivaciones_son_mas_a_la_izquierda_y_producen_la_cadena` comprueba (a), (b) y (c) paso a paso, y aplica cada producción de forma independiente al árbol de PLY.

2. **Unicidad.** Se sigue del Teorema de §6.2 del Numeral 1: en cada nodo, la producción y la partición quedan determinadas por la cadena. Por ejemplo, en E1:
   - **Raíz ExpB.** Hay un único `or` en profundidad 0 (el 7.º token), así que la producción es P1 y la partición es `not ( true and false )` | `or` | `false and not false`. El `or` interior a los paréntesis no cuenta (profundidad 1).
   - **TermB derecho** (`false and not false`). Hay un `and` en profundidad 0, así que la producción es P3 y se parte en el **último** `and`.
   - **FactB** (`not …`). El primer token `not` fija la producción P5. Con `(`, se aplica P6.

   En E2, la raíz no tiene `or` en profundidad 0 (los dos `or` están dentro de paréntesis), así que se aplica P2. Después, TermB tiene dos `and` en profundidad 0, se aplica P3 y se parte en el **último** de ellos. Eso da `(A and B) and C`, es decir, la asociatividad izquierda del paso 3 de la tabla 2.1. `glc.contar_arboles` confirma **1 árbol** para cada una.

3. **Coherencia con el analizador.** El parser LALR(1) de la Figura 3 (sin tabla `precedence`) acepta ambas cadenas y construye exactamente los árboles 1.2 y 2.2. Una derivación más a la izquierda recorre el árbol en **preorden**, mientras que un parser ascendente lo construye en **postorden** (derivación más a la derecha en reversa). El árbol es el mismo. ∎

**Lo que muestran E1 y E2 sobre la gramática:**

| Fenómeno | Dónde se ve | Producción responsable |
|---|---|---|
| `and` antes que `or` | E1: `… or false and not false` se agrupa como `or (false and not false)` | P1 tiene a TermB a la derecha |
| `not` solo afecta a su FactB | E1: `not (true and false)` niega el paréntesis, no el `or` | P5: FactB → not FactB |
| `and` asociativo por la izquierda | E2: la raíz es `(A and B) and C` (pasos 2 y 3: P3, P3) | P3 es recursiva por la izquierda |
| Doble negación anidada | E2: `not not (…)` (pasos 5 y 6: P5, P5) | P5 es recursiva por la derecha |
| Paréntesis que reinician el nivel | E2: dentro de `( … )` vuelve a aparecer ExpB con su propio `or` | P6: FactB → ( ExpB ) |

---

## 4. E3 (inválida): dónde y por qué se bloquea

```
E3 = (true or not false) and not or false
                                 ^
                                 columna 29: token 'or'
```

**Tokens (10):** `( true or not false ) and not or false`.

**Nivel léxico: correcta.** Las 10 son palabras reservadas o paréntesis válidos y el lexer del Integrante 1 reporta **0 errores**. El error es **puramente sintáctico**: cada palabra es válida, pero el **orden** `not or` no lo es.

### 4.1 Derivación más a la izquierda del prefijo viable (12 pasos)

Se puede derivar todo el prefijo `( true or not false ) and not` hasta dejar pendiente un único FactB:

| Paso | Prod. | Forma sentencial |
|---:|:---:|---|
| 0 | | ExpB |
| 1 | P2 | **TermB** |
| 2 | P3 | **TermB** and FactB |
| 3 | P4 | **FactB** and FactB |
| 4 | P6 | ( **ExpB** ) and FactB |
| 5 | P1 | ( **ExpB** or TermB ) and FactB |
| 6 | P2 | ( **TermB** or TermB ) and FactB |
| 7 | P4 | ( **FactB** or TermB ) and FactB |
| 8 | P7 | ( true or **TermB** ) and FactB |
| 9 | P4 | ( true or **FactB** ) and FactB |
| 10 | P5 | ( true or not **FactB** ) and FactB |
| 11 | P8 | ( true or not false ) and **FactB** |
| 12 | P5 | ( true or not false ) and not **FactB** |

En el paso 12 los 8 primeros tokens ya están generados y el no terminal más a la izquierda es **FactB**, que viene de P5 (FactB → not **FactB**). El siguiente terminal de la cadena tiene que salir de ese FactB. Las únicas opciones son P5 a P8, y **todas** empiezan por `not`, `(`, `true` o `false`. El token que sigue es `or`, así que **ninguna producción es aplicable** y la derivación se detiene en este punto.

Árbol parcial en el momento del bloqueo:

```
ExpB
└── TermB
    ├── TermB
    │   └── FactB
    │       ├── (
    │       ├── ExpB  ⇒*  true or not false
    │       └── )
    ├── and
    └── FactB
        ├── not
        └── FactB   ← debe empezar por {not, (, true, false}, pero llega 'or'  ✗
```

### 4.2 Argumento formal

**Proposición.** $E3 \notin L(G)$, y el primer token que impide cualquier derivación es el `or` de la posición 9 (columna 29), que sigue inmediatamente a `not`.

*Prueba.* Sean $w = E3 = w_1 \dots w_{10}$, con $w_8 = \texttt{not}$ y $w_9 = \texttt{or}$.

**Lema 1 (PRIMEROS).** $\text{PRIMEROS}(\text{FactB}) = \{\texttt{not}, \texttt{(}, \texttt{true}, \texttt{false}\}$. Cada una de P5 a P8 empieza con un terminal distinto y no hay producciones ε (Numeral 1, §4).

**Lema 2 (ÚLTIMOS).** Sea $\text{ÚLTIMOS}(X)$ el conjunto de terminales con los que puede **terminar** una cadena de $L(X)$. Por punto fijo sobre el último símbolo de cada lado derecho, $\text{ÚLTIMOS}(\text{ExpB}) = \text{ÚLTIMOS}(\text{TermB}) = \text{ÚLTIMOS}(\text{FactB}) = \{\texttt{)}, \texttt{true}, \texttt{false}\}$. En particular, **ninguna cadena de L(ExpB), L(TermB) o L(FactB) termina en `not`**. El caso clave es P5 = not FactB, que termina en FactB y no en `not`.

**Paso 1: el token `not` de la posición 8 tiene que venir de P5.** Es la única producción que genera `not`. Por lo tanto, en cualquier árbol para $w$ existe un nodo FactB → `not` FactB cuyo hijo FactB genera una subcadena **no vacía** que empieza en $w_9$.

**Paso 2: esa subcadena debería empezar por un elemento de PRIMEROS(FactB).** Pero $w_9 = \texttt{or} \notin \text{PRIMEROS}(\text{FactB})$ (Lema 1). Contradicción.

**Paso 3: no hay otra forma de colocar el `or`.** La única producción que genera `or` es P1, ExpB → ExpB **or** TermB. El `or` de la posición 9 está en profundidad 0 (el paréntesis se cerró en $w_6$). Para usarlo como operador de P1, la parte izquierda $w_1 \dots w_8 = \texttt{( true or not false ) and not}$ tendría que pertenecer a $L(\text{ExpB})$, lo cual es imposible porque termina en `not` (Lema 2). Tampoco puede pertenecer a un ExpB entre paréntesis, porque a la derecha de $w_9$ no hay ningún `)`.

Por los pasos 1 a 3, ningún árbol de derivación genera $w$, así que $E3 \notin L(G)$. Además, el prefijo $w_1 \dots w_8$ **sí** es prefijo de una cadena de L(G): por ejemplo, la tabla 4.1 completada con FactB ⇒ true. Por eso el primer punto de bloqueo es exactamente $w_9$. ∎

**Corolario (lectura de "not or").** `not` es un operador **unario prefijo** y exige un operando FactB a su derecha. `or` es **binario infijo** y exige un ExpB completo a su izquierda. En `not or`, el `not` queda sin operando y el `or` queda sin operando izquierdo completo. La gramática rechaza las dos lecturas.

### 4.3 Evidencia del parser LALR(1)

Con la tabla de `docs/numeral1/parser.out` (Integrante 2), el parser desplaza los 8 primeros tokens sin errores. Después de desplazar `not` llega al **estado 4**:

```
state 4

    (5) FactB -> NOT . FactB
    (5) FactB -> . NOT FactB
    (6) FactB -> . LPAREN ExpB RPAREN
    (7) FactB -> . TRUE
    (8) FactB -> . FALSE

    NOT             shift and go to state 4
    LPAREN          shift and go to state 5
    TRUE            shift and go to state 6
    FALSE           shift and go to state 7
```

El estado 4 solo tiene acciones para `NOT`, `LPAREN`, `TRUE` y `FALSE`, que son exactamente PRIMEROS(FactB). **No tiene acción para `OR`**, así que el parser invoca `p_error` en ese token:

```
SyntaxError: token inesperado 'or' (col 29)
```

Este resultado coincide con la línea esperada del documento de la Tarea 36:

```
[L4] (true or not false) and not or false   => ERROR sintactico (col 29): token inesperado 'or'
```

`glc.contar_arboles` da **0 árboles** para E3.

> **Para el Integrante 3 (`parser.py`).** El error se detecta en `p_error` con el token `OR` (`lexpos` = 28, columna 29). La recuperación `error NEWLINE` descarta el resto de la línea (`or false`) y el análisis sigue en la línea siguiente. `tests/test_numeral2.py::test_e3_se_bloquea_en_not_or` sirve como referencia del mensaje y la columna esperados.

---

## 5. Resumen

| | Expresión | ¿En L(G)? | Pasos ⇒ₗₘ | Árboles | Valor / error |
|---|---|:---:|:---:|:---:|---|
| E1 | `not (true and false) or false and not false` | ✔ | 15 | 1 | `true` |
| E2 | `not not (false or true and not false) and (true or false) and not (true and true)` | ✔ | 30 | 1 | `false` |
| E3 | `(true or not false) and not or false` | ✘ | 12 (prefijo) | 0 | ERROR sintáctico, col 29, token `or` |

## 6. Cómo reproducir

```bash
pip install -r requirements.txt
python docs/numeral2/derivaciones.py          # informe + regenera salida_numeral2.txt
python -m pytest tests/test_numeral2.py -v    # 14 pruebas del Numeral 2
```
