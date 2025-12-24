# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

from checkers.arkts_lint_helper import run_ets_lint
from checkers.checker import Checker, CheckResult


class ArkTsLintChecker(Checker):
    name = "arkts-lint"
    help = "Run arkts / ts lint in harmony directory"

    def run(self, options, mr, changed_files):
        if run_ets_lint(options, changed_files):
            return CheckResult.PASSED
        else:
            return CheckResult.FAILED
