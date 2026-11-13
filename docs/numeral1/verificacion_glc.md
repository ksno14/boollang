# Numeral 1: verificación formal de la gramática (Figura 3)

**Tarea 36 · Lenguaje `boollang` · Integrante 2**

Este documento demuestra que la gramática de la Figura 3 es una **gramática libre de contexto (GLC) bien formada**. En concreto, que sus símbolos son **productivos** y **alcanzables**, que **no tiene producciones ε ni ciclos**, que es **no ambigua** y que es **funcionalmente completa**. También incluye la evidencia de que PLY construye su tabla **LALR(1) sin conflictos**.

Cada afirmación se comprueba de forma automática con:

| Archivo | Contenido |
|---|---|
| [`verificar_glc.py`](verificar_glc.py) | Algoritmos de punto fijo, conteo de árboles, construcción LALR(1) con `ply.yacc` y completitud funcional |
| [`parser.out`](parser.out) | Tabla LALR(1) generada por PLY 3.11 (evidencia de 0 conflictos) |
| [`salida_verificacion.txt`](salida_verificacion.txt) | Salida completa del script |
| [`../../tests/test_gramatica.py`](../../tests/test_gramatica.py) | 21 pruebas `pytest` con estas propiedades |
| [`../../gramatica.ebnf`](../../gramatica.ebnf) | Gramática oficial en notación E-BNF (Figura 2) |

---

## 0. La gramática G

$G = (V, \Sigma, P, S)$ con

- $V = \{\text{ExpB}, \text{TermB}, \text{FactB}\}$ (no terminales)
- $\Sigma = \{\texttt{or}, \texttt{and}, \texttt{not}, \texttt{(}, \texttt{)}, \texttt{true}, \texttt{false}\}$ (terminales)
- $S = \text{ExpB}$ (símbolo inicial)
- $P$: las 8 producciones de la Figura 3

| # | Producción | Nivel |
|---|---|---|
| P1 | ExpB → ExpB **or** TermB | disyunción (menor precedencia) |
| P2 | ExpB → TermB | |
| P3 | TermB → TermB **and** FactB | conjunción |
| P4 | TermB → FactB | |
| P5 | FactB → **not** FactB | negación (mayor precedencia) |
| P6 | FactB → **(** ExpB **)** | agrupación |
| P7 | FactB → **true** | literal |
| P8 | FactB → **false** | literal |

Cada terminal corresponde a un token del analizador léxico (`boollang/lexer.py`): `or`→`OR`, `and`→`AND`, `not`→`NOT`, `(`→`LPAREN`, `)`→`RPAREN`, `true`→`TRUE`, `false`→`FALSE`.

---

## 1. G es una GLC bien formada

Una gramática es **libre de contexto** si toda producción tiene la forma $A \to \alpha$ con $A \in V$ y $\alpha \in (V \cup \Sigma)^*$. Además está **bien formada** (es *limpia* o *reducida*) si no tiene símbolos inútiles, es decir, todo símbolo es productivo y alcanzable.

- $V \cap \Sigma = \varnothing$ y $S \in V$.
- El lado izquierdo de P1 a P8 es siempre **un único no terminal**: ExpB, TermB o FactB. Ninguna regla depende del contexto en que aparece el no terminal.
- Todo lado derecho pertenece a $(V \cup \Sigma)^+$ (es no vacío; ver §4).
- Todo no terminal tiene al menos una producción.

Por tanto, G es una GLC. Las secciones 2 y 3 prueban que no tiene símbolos inútiles.

---

## 2. Todos los símbolos son productivos

Un símbolo $X$ es **productivo** si $X \Rightarrow^* w$ para alguna $w \in \Sigma^*$. Los terminales lo son trivialmente. Para los no terminales se usa el algoritmo de punto fijo:

$$\text{Prod}_0 = \varnothing, \qquad \text{Prod}_{i+1} = \text{Prod}_i \cup \{A \mid A \to \alpha \in P,\ \alpha \in (\Sigma \cup \text{Prod}_i)^*\}$$

| Iteración | Conjunto | Justificación |
|---|---|---|
| Prod₁ | {FactB} | P7: FactB → true (solo terminales) |
| Prod₂ | {FactB, TermB} | P4: TermB → FactB, con FactB ∈ Prod₁ |
| Prod₃ | {FactB, TermB, ExpB} | P2: ExpB → TermB, con TermB ∈ Prod₂ |
| Prod₄ | = Prod₃ | punto fijo |

$\text{Prod}_3 = V$, así que **todo no terminal es productivo**. Derivaciones testigo:

- FactB ⇒ true
- TermB ⇒ FactB ⇒ true
- ExpB ⇒ TermB ⇒ FactB ⇒ true

## 3. Todos los símbolos son alcanzables

Un símbolo $X$ es **alcanzable** si $S \Rightarrow^* \alpha X \beta$:

$$\text{Alc}_0 = \{S\}, \qquad \text{Alc}_{i+1} = \text{Alc}_i \cup \{X \mid A \to \alpha X \beta \in P,\ A \in \text{Alc}_i\}$$

| Iteración | Conjunto | Producciones usadas |
|---|---|---|
| Alc₀ | {ExpB} | símbolo inicial |
| Alc₁ | {ExpB, TermB, or} | P1, P2 |
| Alc₂ | {ExpB, TermB, FactB, or, and} | P3, P4 |
| Alc₃ | {ExpB, TermB, FactB, or, and, not, (, ), true, false} | P5 a P8 |
| Alc₄ | = Alc₃ | punto fijo |

$\text{Alc}_3 = V \cup \Sigma$, así que **todo símbolo es alcanzable** y no hay que eliminar ninguno.

## 4. Sin producciones ε

Ninguna de las 8 producciones tiene el lado derecho vacío: la longitud mínima es 1 (P2, P4, P7 y P8). Además, el conjunto de **anulables** es vacío. Con $\text{Nul}_0 = \varnothing$, ninguna producción tiene un lado derecho formado solo por anulables, así que $\text{Nul}_1 = \varnothing$ es el punto fijo.

Consecuencia: $\varepsilon \notin L(G)$, y en toda derivación cada símbolo genera **al menos un terminal**. Por eso un paso de derivación nunca acorta la forma sentencial.

## 5. Sin ciclos

Una gramática tiene un **ciclo** si existe $A \in V$ con $A \Rightarrow^+ A$. Sin producciones ε (§4), un ciclo solo puede formarse con **producciones unitarias** $A \to B$, porque cualquier otra producción agrega al menos un terminal y la forma sentencial no vuelve a ser $A$.

Las producciones unitarias son P2 (ExpB → TermB) y P4 (TermB → FactB). Su cierre transitivo es:

$$U^+ = \{(\text{ExpB},\text{TermB}),\ (\text{TermB},\text{FactB}),\ (\text{ExpB},\text{FactB})\}$$

El grafo unitario es una cadena estrictamente descendente:

```
ExpB ──► TermB ──► FactB        (FactB no tiene producciones unitarias)
```

Ningún par $(A, A)$ pertenece a $U^+$, así que **G no tiene ciclos**. Junto con §2 a §4, G es una **gramática propia**.

> **Observación.** FactB → ( ExpB ) **no** forma un ciclo: ExpB ⇒⁺ ( ExpB ) siempre agrega dos terminales, así que nunca vuelve a la forma sentencial "ExpB". Es la recursión que permite el anidamiento.
>
> **Recursión izquierda.** P1 y P3 son recursivas por la izquierda. Esto **no** es un defecto para un analizador ascendente LALR(1) como `ply.yacc`, que las procesa en pila constante. Además, es justo lo que da la asociatividad izquierda (§6.3). Solo un analizador descendente LL(1) requeriría transformarlas.

---

## 6. G no es ambigua

Una GLC es **ambigua** si alguna cadena de $L(G)$ tiene dos árboles de derivación distintos o, lo que es equivalente, dos derivaciones más a la izquierda distintas.

### 6.1 Por qué hace falta la estratificación: contraejemplo

La gramática "ingenua" con el mismo lenguaje:

```
E → E or E | E and E | not E | ( E ) | true | false
```

**es ambigua**. La cadena `true or false and false` tiene dos árboles:

```
      E (or)                     E (and)
     /  |  \                    /   |   \
 true  or   E (and)          E (or) and  false
           / | \             / | \
      false and false    true or false
   valor: true             valor: false
```

Los dos árboles dan **valores distintos**, así que la ambigüedad sí cambia el resultado. La Figura 3 la elimina **estratificando** la gramática en tres niveles, uno por precedencia: ExpB > TermB > FactB.

### 6.2 Demostración (inducción estructural)

Sea $\text{prof}(w, i)$ el número de `(` menos el número de `)` en $w_1 \dots w_{i-1}$. Decimos que un operador en la posición $i$ está **en profundidad 0** si $\text{prof}(w, i) = 0$.

**Lema A (balanceo).** Toda $w \in L(X)$, con $X \in V$, tiene paréntesis balanceados. *Prueba:* inducción sobre la derivación. Solo P6 introduce paréntesis, y lo hace en pareja `(` … `)` alrededor de una subcadena que, por hipótesis de inducción, está balanceada. ∎

**Lema B.** Si $w \in L(\text{FactB})$, entonces $w$ no tiene `and` ni `or` en profundidad 0.
*Prueba:* con P7 y P8 no hay operadores. Con P5, $w = \texttt{not}\,w'$ y $w' \in L(\text{FactB})$ cumple el lema por hipótesis de inducción. Con P6 todos los símbolos de $w$, salvo los extremos, están en profundidad ≥ 1. ∎

**Lema C.** Si $w \in L(\text{TermB})$, entonces $w$ no tiene `or` en profundidad 0.
*Prueba:* con P4 se aplica el Lema B. Con P3, $w = u\ \texttt{and}\ v$, donde $u$ cumple el lema por hipótesis de inducción y $v$ cumple el Lema B. Como $u$ está balanceada (Lema A), la profundidad al empezar $v$ vuelve a ser 0. ∎

**Teorema.** Para todo $X \in V$ y toda $w \in L(X)$, existe **exactamente un** árbol de derivación con raíz $X$ y frontera $w$.

*Prueba.* Inducción fuerte sobre el par $(|w|, \text{nivel}(X))$ en orden lexicográfico, con $\text{nivel}(\text{FactB}) < \text{nivel}(\text{TermB}) < \text{nivel}(\text{ExpB})$. Basta probar que la **primera producción** aplicada y la **partición** de $w$ entre los hijos están determinadas por $w$. Después, la hipótesis de inducción da la unicidad de cada subárbol, porque cada hijo es una cadena más corta o un no terminal de nivel menor con la misma cadena.

- **X = FactB.** Las producciones P5 a P8 empiezan con terminales distintos (`not`, `(`, `true`, `false`), así que el **primer token** de $w$ decide la producción. En P5, $w' = w_2\dots w_n$. En P6, $u = w_2 \dots w_{n-1}$. Ambas particiones son únicas.
- **X = TermB.**
  - Si $w$ tiene algún `and` en profundidad 0, P4 es imposible (Lema B), así que la producción es P3: $w = u\ \texttt{and}\ v$. Ese `and` está en profundidad 0 (Lema A sobre $u$), y $v \in L(\text{FactB})$ no tiene `and` en profundidad 0 (Lema B). Por tanto, el `and` de P3 es **el último `and` en profundidad 0** de $w$, y la partición es única.
  - Si no tiene ninguno, P3 es imposible, así que la producción es P4 (TermB → FactB): misma cadena, nivel menor.
- **X = ExpB.** Mismo razonamiento con `or` y el Lema C. La producción es P1 si y solo si hay un `or` en profundidad 0, y la partición se hace en **el último** de ellos. En otro caso, la producción es P2.

Como la producción y la partición son únicas en cada nodo, el árbol es único. ∎

**Corolario.** Con $X = \text{ExpB}$, toda cadena de $L(G)$ tiene un único árbol de derivación y, por tanto, una única derivación más a la izquierda: **G no es ambigua**.

### 6.3 Precedencia y asociatividad que se deducen de la prueba

La prueba anterior describe la forma del árbol único:

| Propiedad | Motivo en la gramática | Ejemplo | Agrupación |
|---|---|---|---|
| `not` > `and` > `or` | La raíz parte primero por `or` (nivel ExpB), luego por `and` (TermB); `not` está en FactB, el nivel más profundo | `true or false and false` | `true or (false and false)` = **true** |
| `and` asociativo por la izquierda | P3 es recursiva por la izquierda y se parte en el **último** `and` | `true and false and true` | `(true and false) and true` |
| `or` asociativo por la izquierda | P1 es recursiva por la izquierda y se parte en el **último** `or` | `a or b or c` | `(a or b) or c` |
| `not` prefijo, asociativo por la derecha | P5: FactB → not FactB | `not not true` | `not (not true)` |
| `not` solo afecta a su FactB | El operando de `not` es FactB, no TermB | `not true and false` | `(not true) and false` = **false** |

Árboles únicos que genera `ply.yacc` con las 8 reglas y **sin tabla `precedence`** (tomados de `salida_verificacion.txt`):

```
true or false and false   =>  true        true and false and true   =>  false
ExpB                                      ExpB
├── ExpB                                  └── TermB
│   └── TermB                                 ├── TermB
│       └── FactB                             │   ├── TermB
│           └── true                          │   │   └── FactB
├── or                                        │   │       └── true
└── TermB                                     │   ├── and
    ├── TermB                                 │   └── FactB
    │   └── FactB                             │       └── false
    │       └── false                         ├── and
    ├── and                                   └── FactB
    └── FactB                                     └── true
        └── false
```

### 6.4 Evidencia LALR(1): `parser.out` con 0 conflictos

Knuth (1965) demostró que **toda gramática LR(k) es no ambigua**. Como LALR(1) ⊂ LR(1), basta con que la tabla LALR(1) no tenga conflictos shift/reduce ni reduce/reduce para obtener una segunda prueba, independiente de la §6.2.

Se transcribieron las 8 reglas tal cual en `ply.yacc` (clase `ReglasFigura3` de `verificar_glc.py`), **sin declaración `precedence`**, para que PLY no pudiera resolver ningún conflicto por su cuenta. El resultado ([`parser.out`](parser.out)):

```
Created by PLY version 3.11 (http://www.dabeaz.com/ply)

Grammar

Rule 0     S' -> ExpB
Rule 1     ExpB -> ExpB OR TermB
Rule 2     ExpB -> TermB
Rule 3     TermB -> TermB AND FactB
Rule 4     TermB -> FactB
Rule 5     FactB -> NOT FactB
Rule 6     FactB -> LPAREN ExpB RPAREN
Rule 7     FactB -> TRUE
Rule 8     FactB -> FALSE
...
Parsing method: LALR
```

| Medida | Valor |
|---|---|
| Método | LALR |
| Estados | 15 (`state 0` … `state 14`) |
| Conflictos shift/reduce | **0** |
| Conflictos reduce/reduce | **0** |
| Apariciones de la palabra `conflict` en `parser.out` | **0** |

Cuando hay conflictos, PLY marca cada uno dentro del estado con `! shift/reduce conflict for … resolved as shift` y agrega al final una sección `WARNING: Conflicts:`. Ninguna de las dos aparece en el archivo.

Los estados "críticos", donde la gramática ingenua sí tiene conflicto, se resuelven sin ambigüedad gracias a los conjuntos SIGUIENTE:

```
state 2                                     state 12
    (2) ExpB -> TermB .                         (1) ExpB -> ExpB OR TermB .
    (3) TermB -> TermB . AND FactB              (3) TermB -> TermB . AND FactB

    OR      reduce using rule 2                 OR      reduce using rule 1
    $end    reduce using rule 2                 $end    reduce using rule 1
    RPAREN  reduce using rule 2                 RPAREN  reduce using rule 1
    AND     shift and go to state 9             AND     shift and go to state 9
```

- En el estado 12, con `AND` el parser **desplaza**: el `and` se agrupa antes que el `or` (precedencia).
- Con `OR` **reduce**: el `or` ya leído se cierra antes de empezar el siguiente (asociatividad izquierda).

Cada token tiene una única acción porque SIGUIENTE(ExpB) = {`or`, `)`, `$`} no contiene `and`.

| No terminal | PRIMERO | SIGUIENTE |
|---|---|---|
| ExpB | `not` `(` `true` `false` | `or` `)` `$` |
| TermB | `not` `(` `true` `false` | `or` `and` `)` `$` |
| FactB | `not` `(` `true` `false` | `or` `and` `)` `$` |

Como control, `tests/test_gramatica.py` construye con la misma función la gramática ingenua de §6.1. En ese caso PLY sí reporta conflictos shift/reduce, lo que confirma que el detector funciona y que el 0 de la Figura 3 no es un falso negativo.

### 6.5 Verificación exhaustiva acotada

Como tercera evidencia, `verificar_glc.py` **cuenta los árboles de derivación** (programación dinámica sobre tramos $[i, j)$) de **todas** las cadenas de $\Sigma^n$ con $1 \le n \le 7$: $\sum_{n=1}^{7} 7^n = 960\,799$ cadenas.

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| Cadenas de L(G) | 2 | 2 | 12 | 22 | 90 | 216 | 770 |
| Con ≥ 2 árboles | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Con la gramática ingenua, el mismo contador da **2** árboles para `true or false and false`; con la Figura 3 da **1**.

---

## 7. G es funcionalmente completa

Un conjunto de conectivos es **funcionalmente completo** si con él se puede expresar **toda** función booleana $f : \{0,1\}^n \to \{0,1\}$. Hay que probar dos cosas: que los conectivos de G bastan y que la gramática permite escribir cualquier fórmula con ellos.

**(a) {not, and, or} es funcionalmente completo (forma normal disyuntiva).** Sea $f$ una función de $n$ argumentos y sea $T_f = \{\,c \in \{0,1\}^n : f(c) = 1\,\}$.

- Para cada $c \in T_f$, el **mintérmino** $m_c = \ell_1 \wedge \dots \wedge \ell_n$, con $\ell_i = x_i$ si $c_i = 1$ y $\ell_i = \neg x_i$ si $c_i = 0$, vale 1 exactamente en $c$.
- Por tanto, $f \equiv \bigvee_{c \in T_f} m_c$.
- Si $T_f = \varnothing$, $f \equiv x_1 \wedge \neg x_1$.

Solo se usan ¬, ∧ y ∨. ∎

**(b) G puede escribir cualquier fórmula sobre esos conectivos.** Por P6, P4 y P2, si $e \in L(\text{ExpB})$ entonces:

$$\texttt{(}e\texttt{)} \in L(\text{FactB}) \subseteq L(\text{TermB}) \subseteq L(\text{ExpB}).$$

Se define la traducción $\tau$ de fórmulas a cadenas:

| Fórmula φ | τ(φ) | Producciones |
|---|---|---|
| 1 / 0 | `true` / `false` | P7 / P8 |
| ¬φ | `not (` τ(φ) `)` | P5, P6 |
| φ ∧ ψ | `(` τ(φ) `) and (` τ(ψ) `)` | P3, P6 |
| φ ∨ ψ | `(` τ(φ) `) or (` τ(ψ) `)` | P1, P6 |

Por inducción estructural, $\tau(\varphi) \in L(G)$ para toda fórmula φ. Además, por la unicidad del árbol (§6), su valor es el de φ: los paréntesis de τ fuerzan la misma agrupación que tiene φ.

**Conclusión.** Para toda función booleana $f$ y toda entrada $c$ de constantes, la cadena $\tau(\varphi_f[x := c])$ pertenece a $L(G)$ y se evalúa a $f(c)$. **G es funcionalmente completa.** Gracias a la precedencia, en la práctica no hacen falta todos los paréntesis de τ:

| Función | Expresión en boollang (x, y ∈ {true, false}) |
|---|---|
| x → y (implicación) | `not x or y` |
| x ↔ y (equivalencia) | `x and y or not x and not y` |
| x ⊕ y (xor) | `x and not y or not x and y` |
| x ↑ y (nand) | `not (x and y)` |
| x ↓ y (nor) | `not (x or y)` |

**Verificación automática.** `verificar_completitud_funcional()` genera la FND de las **16 funciones booleanas binarias**. Para cada una sustituye las 4 combinaciones de `true`/`false` y comprueba tres cosas: que la cadena es aceptada por el parser LALR(1), que tiene exactamente un árbol y que su valor coincide con la tabla de verdad. Resultado: **16/16 OK**.

---

## 8. Resumen

| Propiedad | Resultado | Cómo se prueba |
|---|---|---|
| GLC bien formada | ✔ | §1: forma de las producciones |
| Símbolos productivos | ✔ V | §2: punto fijo en 3 iteraciones |
| Símbolos alcanzables | ✔ V ∪ Σ | §3: punto fijo en 3 iteraciones |
| Sin producciones ε | ✔ 0, sin anulables | §4 |
| Sin ciclos | ✔ grafo unitario acíclico | §5 |
| No ambigua | ✔ | §6.2 inducción + §6.4 LALR(1) con 0 conflictos + §6.5 exhaustiva n ≤ 7 |
| Precedencia not > and > or, asociatividad izquierda | ✔ | §6.3, sin tabla `precedence` |
| Funcionalmente completa | ✔ | §7: FND + traducción τ, 16/16 funciones binarias |

## 9. Relación con `parser.py` (Integrante 3)

El parser del proyecto agrega a estas 8 reglas las de **Programa** y **Sentencia** (sección 2 de `gramatica.ebnf`) y la recuperación de errores `error NEWLINE` / `error PUNTOYCOMA`. Esas reglas solo actúan **por encima** de ExpB. Los separadores `;` y `\n` no aparecen dentro de ninguna de las 8 producciones: solo se agregan a SIGUIENTE(ExpB), SIGUIENTE(TermB) y SIGUIENTE(FactB) como terminadores. En los estados de la Figura 3 esos tokens solo pueden provocar reducciones, igual que `$` hoy, así que no generan conflictos nuevos en la parte de expresiones. Cuando se integre `parser.py`, conviene generar su `parser.out` y confirmar que también reporta 0 conflictos.

## 10. Cómo reproducir

```bash
pip install -r requirements.txt
python docs/numeral1/verificar_glc.py        # informe + regenera parser.out
python -m pytest tests/test_gramatica.py -v  # 21 pruebas del Numeral 1
```
