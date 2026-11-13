"""
Pruebas unitarias para el analizador léxico de boollang.
"""

from boollang.lexer import (
    build_lexer,
    find_column,
    tokenize,
)


class TestTokensBasicos:
    """Pruebas de reconocimiento de tokens válidos individuales."""

    def test_palabras_reservadas(self):
        entrada = "true false and or not"
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        tipos = [t.type for t in toks]
        valores = [t.value for t in toks]

        assert tipos == ['TRUE', 'FALSE', 'AND', 'OR', 'NOT']
        assert valores == ['true', 'false', 'and', 'or', 'not']

    def test_simbolos_puntuacion(self):
        entrada = "( ) ;"
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        tipos = [t.type for t in toks]
        valores = [t.value for t in toks]

        assert tipos == ['LPAREN', 'RPAREN', 'PUNTOYCOMA']
        assert valores == ['(', ')', ';']

    def test_saltos_de_linea(self):
        entrada = "true\nfalse\n"
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        tipos = [t.type for t in toks]
        assert tipos == ['TRUE', 'NEWLINE', 'FALSE', 'NEWLINE']


class TestComentariosYEspacios:
    """Pruebas para ignorar comentarios y espacios."""

    def test_espacios_y_tabulaciones_ignorados(self):
        entrada = "   \t  true  \t  \r and  \t false   "
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        assert [t.type for t in toks] == ['TRUE', 'AND', 'FALSE']

    def test_comentario_linea_simple(self):
        entrada = "// Este es un comentario\ntrue and false"
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        # El comentario no genera tokens, el \n genera NEWLINE
        tipos = [t.type for t in toks]
        assert tipos == ['NEWLINE', 'TRUE', 'AND', 'FALSE']

    def test_comentario_al_final_de_linea(self):
        entrada = "true and false // comentario al final\nnot true"
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        tipos = [t.type for t in toks]
        assert tipos == ['TRUE', 'AND', 'FALSE', 'NEWLINE', 'NOT', 'TRUE']

    def test_comentario_multilinea(self):
        entrada = "true /* comentario bloque */ and false"
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        assert [t.type for t in toks] == ['TRUE', 'AND', 'FALSE']

    def test_comentario_multilinea_con_saltos_de_linea(self):
        entrada = "true /* linea 1\nlinea 2\nlinea 3 */ and false"
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        assert [t.type for t in toks] == ['TRUE', 'AND', 'FALSE']
        # 'and' y 'false' deben estar en la línea 3 (1 + 2 saltos)
        and_token = toks[1]
        assert and_token.lineno == 3


class TestConteoLineasYColumnas:
    """Pruebas para el conteo de líneas y cálculo de columna."""

    def test_conteo_de_lineas(self):
        entrada = "true\nfalse\nnot true"
        toks, errs = tokenize(entrada)

        assert len(errs) == 0
        assert toks[0].lineno == 1  # true
        assert toks[1].lineno == 1  # NEWLINE
        assert toks[2].lineno == 2  # false
        assert toks[3].lineno == 2  # NEWLINE
        assert toks[4].lineno == 3  # not
        assert toks[5].lineno == 3  # true

    def test_calculo_columna_primera_linea(self):
        entrada = "true and false"
        toks, _ = tokenize(entrada)

        # true empieza en col 1
        assert find_column(entrada, toks[0]) == 1
        # and empieza en col 6
        assert find_column(entrada, toks[1]) == 6
        # false empieza en col 10
        assert find_column(entrada, toks[2]) == 10

    def test_calculo_columna_lineas_posteriores(self):
        entrada = "true\n  and false"
        toks, _ = tokenize(entrada)

        # 'and' está en la segunda línea tras 2 espacios -> col 3
        token_and = toks[2]
        assert token_and.type == 'AND'
        assert token_and.lineno == 2
        assert find_column(entrada, token_and) == 3


class TestManejoDeErrores:
    """Pruebas de detección y recuperación de errores léxicos."""

    def test_palabra_no_valida_mayusculas(self):
        entrada = "true and TRUE"
        toks, errs = tokenize(entrada)

        # Solo true y and deben generar tokens
        assert [t.type for t in toks] == ['TRUE', 'AND']
        # Debe haber 1 error léxico por 'TRUE'
        assert len(errs) == 1
        assert errs[0].line == 1
        assert errs[0].column == 10
        assert errs[0].value == 'TRUE'
        assert errs[0].message == "ERROR lexico (col 10): palabra no valida 'TRUE'"

    def test_palabra_no_valida_identificador_desconocido(self):
        entrada = "true xor false"
        toks, errs = tokenize(entrada)

        assert [t.type for t in toks] == ['TRUE', 'FALSE']
        assert len(errs) == 1
        assert errs[0].column == 6
        assert errs[0].value == 'xor'
        assert errs[0].message == "ERROR lexico (col 6): palabra no valida 'xor'"

    def test_caracter_ilegal(self):
        entrada = "true @ false # not"
        toks, errs = tokenize(entrada)

        assert [t.type for t in toks] == ['TRUE', 'FALSE', 'NOT']
        assert len(errs) == 2
        assert errs[0].column == 6
        assert errs[0].value == '@'
        assert errs[0].message == "ERROR lexico (col 6): caracter ilegal '@'"
        assert errs[1].column == 14
        assert errs[1].value == '#'
        assert errs[1].message == "ERROR lexico (col 14): caracter ilegal '#'"

    def test_recuperacion_no_detiene_analisis(self):
        entrada = "$$ true && false !!"
        toks, errs = tokenize(entrada)

        # Los tokens válidos deben reconocerse a pesar de los caracteres ilegales
        assert [t.type for t in toks] == ['TRUE', 'FALSE']
        # Cuatro errores por '$', '$', '&', '&', '!', '!' = 6 caracteres ilegales
        assert len(errs) == 6


class TestEscenarioOficialEnunciado:
    """
    Prueba que replica el archivo de ejemplo oficial escenario3_recuperacion.bool
    para verificar el comportamiento léxico exacto esperado en el documento.
    """

    def test_escenario3_recuperacion_lexico(self):
        texto = (
            "// Pruebas del lenguaje de expresiones booleanas (Tarea 36)\n"
            "not (true and false) or false and not false\n"
            "not not (false or true and not false) and (true or false) and not (true and true);\n"
            "(true or not false) and not or false\n"
            "true and TRUE\n"
            "true and (false or true\n"
            "not false and true\n"
        )

        lx = build_lexer()
        toks, errs = tokenize(texto, lx)

        # En todo el archivo solo hay un error léxico: 'TRUE' en la línea 5, columna 10
        assert len(errs) == 1
        error_true = errs[0]
        assert error_true.line == 5
        assert error_true.column == 10
        assert error_true.value == 'TRUE'
        assert error_true.message == "ERROR lexico (col 10): palabra no valida 'TRUE'"

        # Verificar que la línea 5 generó los tokens TRUE y AND antes del error
        # Busquemos los tokens en la línea 5
        toks_linea_5 = [t for t in toks if t.lineno == 5]
        tipos_l5 = [t.type for t in toks_linea_5]
        assert tipos_l5 == ['TRUE', 'AND', 'NEWLINE']

        # Verificar que las líneas posteriores se analizaron normalmente
        toks_linea_7 = [t for t in toks if t.lineno == 7]
        tipos_l7 = [t.type for t in toks_linea_7]
        assert tipos_l7 == ['NOT', 'FALSE', 'AND', 'TRUE', 'NEWLINE']
