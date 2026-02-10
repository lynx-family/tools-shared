# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.


"""
This script uses a simple lexer+parser to check if a macro can be used in directives.

Lexical tokens:
IDENT   := [A-Za-z_][A-Za-z0-9_]* - "defined"
DEFINED := "defined"
NOT     := !
AND     := &&
OR      := ||
LPAREN  := (
RPAREN  := )

Parser grammar:
expr        := or_expr ;

or_expr     := and_expr ( OR and_expr )* ;

and_expr    := unary ( AND unary )* ;

unary       := NOT unary
            | primary ;

primary     := defined_expr
            | IDENT
            | LPAREN expr RPAREN ;

defined_expr := DEFINED ( LPAREN IDENT RPAREN | IDENT ) ;
"""
from checkers.checker import Checker, CheckResult

import re


WHITELIST_MACROS = {
    "_WIN32"
}

# the parser builds an abstract syntax tree
class Parser:
    def __init__(self, toks):
        self.toks = toks
        self.pos = 0

    def _peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else ("EOF", "")

    def _accept(self, kind):
        if self._peek()[0] == kind:
            tok = self._peek()
            self.pos += 1
            return tok
        return None

    def _expect(self, kind):
        tok = self._accept(kind)
        if tok is None:
            raise ValueError("expected_" + kind)
        return tok

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        node = self.parse_and()
        while self._accept("OR") is not None:
            rhs = self.parse_and()
            node = ("or", node, rhs)
        return node

    def parse_and(self):
        node = self.parse_unary()
        while self._accept("AND") is not None:
            rhs = self.parse_unary()
            node = ("and", node, rhs)
        return node

    def parse_unary(self):
        if self._accept("NOT") is not None:
            return ("not", self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        if self._accept("DEFINED") is not None:
            if self._accept("LPAREN") is not None:
                ident = self._expect("IDENT")[1]
                self._expect("RPAREN")
                return ("defined", ident)
            ident = self._expect("IDENT")[1]
            return ("defined", ident)

        ident_tok = self._accept("IDENT")
        if ident_tok is not None:
            return ("ident", ident_tok[1])

        if self._accept("LPAREN") is not None:
            node = self.parse_expr()
            self._expect("RPAREN")
            return node

        raise ValueError("expected_primary")



def check_macros(content):
    content = content.strip()
    if not content.startswith("#"):
        return False
    # skip header guard
    if content.endswith("_H_") or content.endswith("_JNI"):
        return False

    # #ifdef/ndef is simple as they only support for one identifier
    ifdef_ndef_match = re.search(r"^\s*#(ifdef|ifndef)\b\s+(?P<macro_name>[A-Za-z_]\w*)", content)
    if ifdef_ndef_match:
        macro_name = ifdef_ndef_match.group("macro_name").strip()
        return macro_name not in WHITELIST_MACROS

    # #if/elif supports nestings and logical operators
    # here we build a lexer and parser for the simplified grammar
    ifelif_match = re.search(r"^\s*#(if|elif)\b\s+(?P<expression>.*)$", content)
    if ifelif_match:
        expression = ifelif_match.group("expression")
        # strip comments
        expression = re.sub(r"/\*.*?\*/", "", expression)
        expression = re.sub(r"//.*", "", expression)

        try:
            # the lexer tokenizes all the symbols in the expression
            tokens = []
            i = 0
            n = len(expression)
            while i < n:
                ch = expression[i]
                if ch.isspace():
                    i += 1
                    continue
                if expression.startswith("&&", i):
                    tokens.append(("AND", "&&"))
                    i += 2
                    continue
                if expression.startswith("||", i):
                    tokens.append(("OR", "||"))
                    i += 2
                    continue
                if ch == "!":
                    tokens.append(("NOT", "!"))
                    i += 1
                    continue
                if ch == "(":
                    tokens.append(("LPAREN", "("))
                    i += 1
                    continue
                if ch == ")":
                    tokens.append(("RPAREN", ")"))
                    i += 1
                    continue

                m = re.match(r"[A-Za-z_]\w*", expression[i:])
                if m:
                    ident = m.group(0)
                    tokens.append(("DEFINED" if ident == "defined" else "IDENT", ident))
                    i += len(ident)
                    continue
                # errors will be captured and return True for.
                # we rely on preprocessor for grammar validation, so no actual exception here
                # e.g., unsupported operators
                raise ValueError("unsupported_operator")

            parser = Parser(tokens)
            ast = parser.parse_expr()
            if parser._peek()[0] != "EOF":
                raise ValueError("trailing_tokens")

            # quick AST traversal
            def _validate(node):
                kind = node[0]
                if kind == "defined":
                    return node[1] in WHITELIST_MACROS
                if kind == "ident":
                    return node[1] in WHITELIST_MACROS
                if kind == "not":
                    return _validate(node[1])
                if kind == "and" or kind == "or":
                    return _validate(node[1]) and _validate(node[2])
                return False

            return not _validate(ast)
        except Exception:
            return True

    return False

def match_files(file_list):
    # regular expression pattern to match C/C++ and Objective-C source and header files
    pattern = r"^(?!.*_jni\.h$).*\.(c|cc|cpp|h|hpp|m|mm)$"

    for filename in file_list:
        # check if the file matches the pattern
        return bool(re.match(pattern, filename))


class SpellChecker(Checker):
    name = "macro"
    help = "Check if macro is used in c/c++/objective-c"

    def check_changed_lines(self, options, lines, line_indexes, changed_files):
        result = CheckResult.PASSED
        for i, line in enumerate(lines):
            file_name_index, line_no = line_indexes[i]
            file_name = self.get_file_name(file_name_index)

            if not match_files([file_name]):
                continue

            if check_macros(line):
                print(r"%s:%d: %s" % (file_name, line_no, line))
                result = CheckResult.FAILED
        if result == CheckResult.FAILED:
            print(f"\n")
            print(
                f"The use of macro expressions are prohibited, please contact project owners for special case."
            )
            print(
                f"Or if you are sure you need to use macro expressions, please add [skipChecks:macro] to your commit message."
            )
        return result


if __name__ == "__main__":
    assert check_macros("#if FOO")
    assert check_macros("#if (FOO)")
    assert not check_macros("#if _WIN32")
    assert not check_macros("#if (_WIN32)")

    assert check_macros("#if defined(FOO)")
    assert not check_macros("#if defined(_WIN32)")
    assert not check_macros("#if !defined(_WIN32)")
    assert not check_macros("#if defined(_WIN32) && defined(_WIN32)")
    assert not check_macros("#if defined(_WIN32) || defined(_WIN32)")

    assert check_macros("#if defined(_WIN32) && defined(FOO)")
    assert check_macros("#if _WIN32 && defined(FOO)")
    assert not check_macros("#if _WIN32 && defined(_WIN32)")

    assert check_macros("#if (OS_POSIX)")
    assert check_macros("#if (OS_POSIX) && defined(_WIN32)")
    assert check_macros("#if defined(_WIN32) == 1")

    assert check_macros("#elif FOO")

    assert check_macros("#if (OS_POSIX) // a comment")
    assert check_macros("#if (OS_POSIX) /* a comment */")
    assert not check_macros("#if defined(_WIN32) /* a comment */")

    print("TESTS PASSED")