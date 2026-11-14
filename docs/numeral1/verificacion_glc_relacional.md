# Numeral 1 (Tarea 37) — Extensión Formal de la GLC para Expresiones Proposicionales Relacionales

## 1. Definición Formal de la Gramática Extendida $G_{\text{rel}}$

Tomando como base la GLC de la **Figura 3** (Tarea 36) y la calculadora aritmética de referencia (`LP02 CalculadoraEnFLEX_BISON_y_EnPLY`), se define la gramática libre de contexto extendida:

$$G_{\text{rel}} = (V, \Sigma, P, S)$$

donde:
- **Conjunto de símbolos no terminales ($|V| = 8$):**
  $$V = \{\text{ExpB}, \text{TermB}, \text{FactB}, \text{ExpRel}, \text{OpRel}, \text{ExpA}, \text{TermA}, \text{FactA}\}$$
- **Alfabeto de símbolos terminales ($|\Sigma| = 19$):**
  $$\Sigma = \{\texttt{or}, \texttt{and}, \texttt{not}, \texttt{(}, \texttt{)}, \texttt{true}, \texttt{false}, \texttt{<=}, \texttt{>=}, \texttt{==}, \texttt{!=}, \texttt{<}, \texttt{>}, \texttt{+}, \texttt{-}, \texttt{*}, \texttt{/}, \texttt{NUMBER}, \texttt{ID}\}$$
- **Símbolo inicial:** $S = \text{ExpB}$.
- **Conjunto de 28 reglas de producción ($P_1$ a $P_{28}$):**
  - **Nivel Booleano (Heredado de la Figura 3 + Puente Relacional):**
    - $P_1: \text{ExpB} \to \text{ExpB}\ \texttt{or}\ \text{TermB}$
    - $P_2: \text{ExpB} \to \text{TermB}$
    - $P_3: \text{TermB} \to \text{TermB}\ \texttt{and}\ \text{FactB}$
    - $P_4: \text{TermB} \to \text{FactB}$
    - $P_5: \text{FactB} \to \texttt{not}\ \text{FactB}$
    - $P_6: \text{FactB} \to \texttt{(}\ \text{ExpB}\ \texttt{)}$
    - $P_7: \text{FactB} \to \texttt{true}$
    - $P_8: \text{FactB} \to \texttt{false}$
    - $P_9: \text{FactB} \to \text{ExpRel}$
  - **Nivel Proposicional Relacional:**
    - $P_{10}: \text{ExpRel} \to \text{ExpA}\ \text{OpRel}\ \text{ExpA}$
    - $P_{11..16}: \text{OpRel} \to \texttt{<=} \mid \texttt{>=} \mid \texttt{==} \mid \texttt{!=} \mid \texttt{<} \mid \texttt{>}$
  - **Nivel Aritmético Algebraico (Calculadora LP02 + Multiplicación Implícita en `FactA`):**
    - $P_{17}: \text{ExpA} \to \text{ExpA}\ \texttt{+}\ \text{TermA}$
    - $P_{18}: \text{ExpA} \to \text{ExpA}\ \texttt{-}\ \text{TermA}$
    - $P_{19}: \text{ExpA} \to \text{TermA}$
    - $P_{20}: \text{TermA} \to \text{TermA}\ \texttt{*}\ \text{FactA}$
    - $P_{21}: \text{TermA} \to \text{TermA}\ \texttt{/}\ \text{FactA}$
    - $P_{22}: \text{TermA} \to \text{FactA}$
    - $P_{23}: \text{FactA} \to \texttt{-}\ \text{FactA}$ *(menos unario, ej. `-2X`, `-(X+1)`)*
    - $P_{24}: \text{FactA} \to \texttt{NUMBER}\ \texttt{ID}$ *(multiplicación implícita, ej. `3X`, `5Y`, `6/2X`, `3X*5Y`)*
    - $P_{25}: \text{FactA} \to \texttt{NUMBER}\ \texttt{(}\ \text{ExpA}\ \texttt{)}$ *(multiplicación implícita, ej. `2(X+1)`)*
    - $P_{26}: \text{FactA} \to \texttt{(}\ \text{ExpA}\ \texttt{)}$
    - $P_{27}: \text{FactA} \to \texttt{NUMBER}$
    - $P_{28}: \text{FactA} \to \texttt{ID}$

## 2. Especificación en Estándar E-BNF (Figura 2)

```ebnf
ExpB       ::= TermB ( 'or' TermB )*
TermB      ::= FactB ( 'and' FactB )*
FactB      ::= 'not' FactB | '(' ExpB ')' | 'true' | 'false' | ExpRel
ExpRel     ::= ExpA OpRel ExpA
OpRel      ::= '<=' | '>=' | '==' | '!=' | '<' | '>'
ExpA       ::= TermA ( ( '+' | '-' ) TermA )*
TermA      ::= FactA ( ( '*' | '/' ) FactA )*
FactA      ::= '-' FactA | NUMBER ID | NUMBER '(' ExpA ')' | '(' ExpA ')' | NUMBER | ID
```

## 3. Escalera de 7 Niveles de Precedencia y No Ambigüedad

| Nivel | Categoría | Operadores | Asociatividad | No terminal en $G_{\text{rel}}$ |
| :---: | :--- | :--- | :---: | :--- |
| **1** | Disyunción lógica | `or` | Izquierda | `ExpB` |
| **2** | Conjunción lógica | `and` | Izquierda | `TermB` |
| **3** | Negación lógica | `not` | Derecha (prefijo) | `FactB` |
| **4** | Comparación relacional | `<=`, `>=`, `==`, `!=`, `<`, `>` | No asociativo | `ExpRel` |
| **5** | Aditivo aritmético | `+`, `-` | Izquierda | `ExpA` |
| **6** | Multiplicativo aritmético | `*`, `/` | Izquierda | `TermA` |
| **7** | Unario, implícito y átomos | `-` (unario), `3X`, `2(X+1)`, `( )`, `NUMBER`, `ID` | Derecha (prefijo) | `FactA` |

## 4. Verificación Algorítmica y Tabla LALR(1)

Ejecutando `python docs/numeral1/verificar_glc_relacional.py`:
1. **GLC bien formada:** $V \cap \Sigma = \varnothing$, todos los lados izquierdos pertenecen a $V$.
2. **Productividad:** $\text{Prod}_4 = V$ (los 8 no terminales son productivos).
3. **Alcanzabilidad:** $\text{Alc}_6 = V \cup \Sigma$ (los 8 no terminales y 19 terminales son alcanzables desde `ExpB`).
4. **Ausencia de $\varepsilon$ y de ciclos:** 0 producciones nulas, 0 símbolos anulables y grafo unitario acíclico (`ExpB -> TermB -> FactB -> ExpRel` y `ExpA -> TermA -> FactA`).
5. **Tabla LALR(1) en `docs/numeral1/parser_relacional.out`:** **47 estados**, **0 conflictos shift/reduce** y **0 conflictos reduce/reduce**.
