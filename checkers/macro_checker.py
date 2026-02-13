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

import os
import re

_PP_KIND_RE = re.compile(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b")
_IFDEF_NDEF_RE = re.compile(
    r"^\s*#\s*(ifdef|ifndef)\b\s+(?P<macro_name>[A-Za-z_]\w*)"
)
_IF_ELIF_RE = re.compile(r"^\s*#\s*(if|elif)\b\s+(?P<expression>.*)$")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/")
_LINE_COMMENT_RE = re.compile(r"//.*")
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")
_SOURCE_FILE_RE = re.compile(r"^(?!.*_jni\.h$).*\.(c|cc|cpp|h|hpp|m|mm)$")

WHITELIST_MACROS = frozenset({
    "_WIN32",
    "_WIN64"
})

# helper funcs

# parse directive kind
def _pp_directive_kind(line):
    m = _PP_KIND_RE.match(line)
    return m.group(1) if m else None

# find the corresponding if/def/ndef/elif directive lines for a given #else line number
def _collect_upper_level_condition_lines(all_lines, else_line_no):
    depth = 0
    elif_lines_reversed = []

    for idx in range(else_line_no - 1, 0, -1):
        line = all_lines[idx - 1]
        kind = _pp_directive_kind(line)
        if kind is None:
            continue

        if kind == "endif":
            depth += 1
            continue
        if kind in {"if", "ifdef", "ifndef"}:
            if depth == 0:
                condition_lines = [line.rstrip("\n")]
                condition_lines.extend(reversed(elif_lines_reversed))
                return condition_lines
            depth -= 1
            continue
        if depth != 0:
            continue
        if kind == "elif":
            elif_lines_reversed.append(line.rstrip("\n"))
        elif kind == "else":
            return None

    return None

# check if a #else directive change is illegal by checking if the 
# condition of the enclosing #if/elif directive contains any macro that is not whitelisted
def _is_else_only_change_illegal(file_path, else_line_no):
    if not os.path.isfile(file_path):
        print(f"File {file_path} does not exist.")
        return True, None
 
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception:
        print(f"Failed to read file {file_path}.")
        return True, None
 
    condition_lines = _collect_upper_level_condition_lines(all_lines, else_line_no)
    
    if condition_lines is None:
        print(f"Failed to find the corresponding conditional directives for #else line {else_line_no}.")
        return True, None
 
    for directive_line in condition_lines:
        if check_macros(directive_line):
            return True, directive_line
 
    return False, None



# categorize all changed files into two categories:
# 1. files that only changed #else directives
# 2. files that changed any of #if, #elif, #ifdef, #ifndef directives
def _categorize_changed_lines(lines, line_indexes, get_file_name):
    else_only_targets = {}
    files_with_if_family = set()
 
    for i, line in enumerate(lines):
        file_name_index, line_no = line_indexes[i]
        file_name = get_file_name(file_name_index)
 
        if not match_file(file_name):
            continue
 
        kind = _pp_directive_kind(line)
        if kind == "else":
            else_only_targets.setdefault(file_name, []).append((line_no, line))
        elif kind in {"if", "elif", "ifdef", "ifndef"}:
            files_with_if_family.add(file_name)
 
    return else_only_targets, files_with_if_family

# the parser builds an abstract syntax tree
class MacroParser:
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
    ifdef_ndef_match = _IFDEF_NDEF_RE.match(content)
    if ifdef_ndef_match:
        macro_name = ifdef_ndef_match.group("macro_name").strip()
        return macro_name not in WHITELIST_MACROS

    # #if/elif supports nestings and logical operators
    # here we build a lexer and parser for the simplified grammar
    ifelif_match = _IF_ELIF_RE.match(content)
    if ifelif_match:
        expression = ifelif_match.group("expression")
        # strip comments
        expression = _BLOCK_COMMENT_RE.sub("", expression) # a bit conservative as it fails /* only lines
        expression = _LINE_COMMENT_RE.sub("", expression) 

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

                m = _IDENT_RE.match(expression, i)
                if m:
                    ident = m.group(0)
                    tokens.append(("DEFINED" if ident == "defined" else "IDENT", ident))
                    i += len(ident)
                    continue
                # errors will be captured and return True for.
                # we rely on preprocessor for grammar validation, so no actual exception here
                # e.g., unsupported operators
                raise ValueError("unsupported_operator")

            parser = MacroParser(tokens)
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

def match_file(filename):
    # regular expression pattern to match C/C++ and Objective-C source and header files
    # also exclude macro checker test files just in case:  test_macro_checker
    return _SOURCE_FILE_RE.match(filename) is not None and "test_macro_checker" not in filename  

class MacroChecker(Checker):
    name = "macro"
    help = "Check if macro is used in c/c++/objective-c"

    def check_changed_lines(self, options, lines, line_indexes, changed_files):

        result = CheckResult.PASSED

        else_only_targets, files_with_if_family = _categorize_changed_lines(
            lines, line_indexes, self.get_file_name
        )

        # get the diff of the 2 sets of files
        for file_name, targets in else_only_targets.items():
            if file_name in files_with_if_family:
                continue
 
            for line_no, line in targets:
                res, line = _is_else_only_change_illegal(file_name, line_no)
                if res:
                    print("The pairing directive(s) of your #else directive change here is illegal:")
                    print(r"%s:%d: %s" % (file_name, line_no, line))
                    if line:
                        print(f"Please check the pairing directive {line.strip()}.")
                    else:
                        print("Grammar issue or script bug.")
                    result = CheckResult.FAILED

        for i, line in enumerate(lines):
            file_name_index, line_no = line_indexes[i]
            file_name = self.get_file_name(file_name_index)
            if not match_file(file_name):
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
    assert check_macros("#if _WIN32 > 12")
    assert check_macros("#if _WIN32 | 12")
    assert check_macros("#if _WIN32 & 12")
    assert check_macros("#if _WIN32 < 12")

    assert check_macros("#elif FOO")

    assert check_macros("#if (OS_POSIX) // a comment")
    assert check_macros("#if (OS_POSIX) /* a comment */")
    assert not check_macros("#if defined(_WIN32) /* a comment */")

    print("TESTS PASSED")