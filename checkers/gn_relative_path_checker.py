#!/usr/bin/env python3
# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import subprocess
import sys
import os

from default_env import Env
from gn_tools.gn_relative_path_converter import process_file
from checkers.checker import Checker, CheckResult

COLORED_YELLOW_MSG = "\033[33m"
COLORED_RED_MSG = "\033[31m"
COLORED_PRINT_END = "\033[0m"

suggestions = f'{COLORED_YELLOW_MSG}Please run "git status" or "git diff" to check local changes, and then run "git lynx format --changed" to format local changes.{COLORED_PRINT_END}'


def process_gn_relative_path(changed_files):
    """
    Process GN/GNI files in the changed_files list
    """
    gn_file_modified = True
    for file in changed_files:
        if file.endswith(".gn") or file.endswith(".gni"):
            is_need_process, _ = process_file(file, Env.SELF_PARENT_PATH)
            if is_need_process:
                print(
                    f"{COLORED_RED_MSG}Found gn files with absolute path in {file}. {COLORED_PRINT_END}"
                )
                gn_file_modified = False

    return gn_file_modified


class GnRelativePathChecker(Checker):
    name = "gn-relative-path-check"
    help = "Check gn files with relative path"

    def run(self, options, mr, changed_files):
        print("Checking gn relative path...")
        result = process_gn_relative_path(changed_files)
        if result:
            return CheckResult.PASSED
        else:
            print(suggestions)
            return CheckResult.FAILED
