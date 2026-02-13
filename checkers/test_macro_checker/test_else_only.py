# Copyright 2026 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os
import sys
from pathlib import Path

# a bit hacky, py needs to search for the checkers module
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from checkers.macro_checker import _is_else_only_change_illegal


def _fixture_path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)

def checker_wrapper(path, line_num):
    res, line = _is_else_only_change_illegal(path, line_num)
    if res:
        print("The pairing directive(s) of your #else directive change here is illegal:")
        print(r"%s:%d: %s" % (path, line_num, line))
        if line:
            print(f"Please check the pairing directive {line.strip()}.")
        else:
            print("Grammar issue or script bug.")
    return res  
    
def test_ok_multiple_else_same_file():
    path = _fixture_path("fixture_ok_multiple_else.c")
    assert checker_wrapper(path, 5) is False
    assert checker_wrapper(path, 17) is False


def test_illegal_elif_condition_contains_non_whitelisted_macro():
    path = _fixture_path("fixture_bad_with_elif.c")
    assert checker_wrapper(path, 5) is True


def test_illegal_if_condition_contains_non_whitelisted_macro():
    path = _fixture_path("fixture_bad_macro_in_condition.c")
    assert checker_wrapper(path, 3) is True


def test_ok_nested_inner_if_does_not_affect_outer_else():
    path = _fixture_path("fixture_ok_nested_inner_bad_macro.c")
    assert checker_wrapper(path, 5) is False


if __name__ == "__main__":
    test_ok_multiple_else_same_file()
    test_illegal_elif_condition_contains_non_whitelisted_macro()
    test_illegal_if_condition_contains_non_whitelisted_macro()
    test_ok_nested_inner_if_does_not_affect_outer_else()
    print("\033[92mTESTS PASSED\033[0m")
