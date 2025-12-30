# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import sys

import checkers.format_file_filter as format_file_filter
from checkers.checker import Checker, CheckResult
from checkers.process_header_path_helper import (
    shouldProcessIncludeHeader,
    findSearchHeaders,
)
from config import Config

suggestions = """If you don't find a suitable path among the candidates of header paths, \
maybe you can exclude it from header-path-checker.ignore-header-files in .tools_shared."""


class CppHeaderPathChecker(Checker):
    name = "cpp-header-path"
    help = "Check cpp header path"

    def run(self, options, mr, changed_files):
        result = True
        print("Checking cpp header path...")
        search_headers = findSearchHeaders()
        forbidden_suffix = Config.value(
            "checker-config", "header-path-checker", "ignore-suffixes"
        )
        forbidden_dirs = Config.value(
            "checker-config", "header-path-checker", "ignore-dirs"
        )
        for filename in changed_files:
            if format_file_filter.shouldFormatFile(filename):
                if shouldProcessIncludeHeader(filename, search_headers):
                    result = False
        if result:
            return CheckResult.PASSED
        else:
            print(suggestions)
            return CheckResult.FAILED
