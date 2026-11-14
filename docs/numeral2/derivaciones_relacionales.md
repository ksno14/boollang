# Numeral 2 — Derivaciones por la izquierda y comprobación formal de pertenencia (Expresiones Relacionales)

Verificación formal sobre la GLC extendida (`gramatica_relacional.ebnf`) con el símbolo inicial `ExpB`:

1. **`R1`: `(3X+5Y) <= X/(3-Z)`** — **Aceptada** en **25 pasos** (`=>lm`). Con el entorno `{'X': 2, 'Y': 1, 'Z': 2}`, `(3*2 + 5*1) = 11 <= 2/(3-2) = 2` evalúa a `false`.
2. **`R2`: `not ((3X+5Y) <= X/(3-Z)) and (2X + Y == 5) or false`** — **Aceptada** en **48 pasos** (`=>lm`). Con `{'X': 2, 'Y': 1, 'Z': 2}`, `not(false) and (5 == 5) or false` evalúa a `true`.
3. **`R3`: `(3X+5Y) <= <= 10`** — **Rechazada** (bloqueo determinista en LALR(1)): `ERROR sintactico (col 12): token inesperado '<='`, pues tras `OpRel -> <=` solo se admite `ExpA` (cuyo conjunto `FIRST(ExpA)` es `{-, (, NUMBER, ID}`, excluyendo cualquier operador relacional).

Script ejecutable: [`derivaciones_relacionales.py`](./derivaciones_relacionales.py) y salida verificada en [`salida_numeral2_relacional.txt`](./salida_numeral2_relacional.txt).
