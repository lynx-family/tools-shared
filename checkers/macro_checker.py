# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
from checkers.checker import Checker, CheckResult

import re


whitelist_def_keywords = {
    "_WIN32"
}

def check_if_macro_in_ut(content, file_name):
    content_pattern = r"^#define\s+(private|protected)\s+public$"
    content_match = re.search(content_pattern, content)

    file_pattern = r"^.*_(unittest|testing).*"
    file_match = re.search(file_pattern, file_name)
    if bool(content_match) and bool(file_match):
        return True

    return False


def check_macros(content):
    content = content.strip()
    # skip header guard
    if content.endswith("_H_") or content.endswith("_JNI"):
        return False

    ifdef_ndef_pattern = r"^\s*#(ifdef|ifndef)\b\s+(?P<macro_name>\w+)"
    ifdef_ndef_match = re.search(ifdef_ndef_pattern, content)
    if ifdef_ndef_match:
        macro_name = ifdef_ndef_match.group('macro_name').strip()
        return macro_name not in whitelist_def_keywords

    # if/elif supports operations, so need to be more careful
    ifelif_pattern = r"^\s*#(if|elif)\b\s+(?P<expression>.*)$"
    ifelif_match = re.search(ifelif_pattern, content)

    if ifelif_match:
        expression = ifelif_match.group('expression')
        # capture the op and args
        op_call_pattern = r"!?\s*(?P<op>[A-Za-z_]\w*)?\s*\(\s*(?P<param>[^()]+?)\s*\)"
        # this is for handling cases like "!defined(A) && defined(B)"
        for m in re.finditer(op_call_pattern, expression):
            op = (m.group("op") or "").strip()
            # "" is for cases like #if (OS_POXIS)
            if op != "defined" and op != "":
                return True
            param = m.group("param").strip()
            if param not in whitelist_def_keywords:
                return True

        scrubbed = re.sub(op_call_pattern, " ", expression)
        # Not supporting comparisons
        leftover = re.sub(r"[\s!&|()]+", "", scrubbed)
        if leftover:
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
            # if the macro is used in unittest file for testing, skip check
            if check_if_macro_in_ut(line, file_name):
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
    line = "#define private public"
    file_name = "tttt_unittest.h"
    assert check_if_macro_in_ut(line, file_name)

    file_name = "tttt_unittest.cc"
    assert check_if_macro_in_ut(line, file_name)

    file_name = "tttt_for_testing.h"
    assert check_if_macro_in_ut(line, file_name)

    file_name = "tttt_for_testing.cc"
    assert check_if_macro_in_ut(line, file_name)

    file_name = "tttt.h"
    assert not check_if_macro_in_ut(line, file_name)

    file_name = "tttt_unittest.h"

    line = "#define private public ttttt"
    assert not check_if_macro_in_ut(line, file_name)

    line = "ttttt #define private public"
    assert not check_if_macro_in_ut(line, file_name)

    line = "#define tttt private public"
    assert not check_if_macro_in_ut(line, file_name)
