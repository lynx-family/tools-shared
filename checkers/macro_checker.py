# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
from checkers.checker import Checker, CheckResult

import re


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
    # search for macro expressions using a regular expression pattern
    pattern = r"^\s*#(define|ifdef|ifndef|if|elif|else)\b(?!.*\(.*\)).*$"
    match = re.search(pattern, content)

    return bool(match)


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
