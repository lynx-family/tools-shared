#!/usr/bin/env python3

# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import subprocess
from checkers.checker import Checker, CheckResult
from checkers.copyright.copyright_processor import process_list_unfiltered_from_memory


class CopyrightNoticeChecker(Checker):
    name = "copyright"
    help = "Check copyright notice"

    def run(self, options, mr, changed_files):
        changed = process_list_unfiltered_from_memory(
            changed_files, save_lists_to_files=False
        )
        if changed > 0:
            print("Found files possibly not containing proper copyright notice.")
            cmd = ["git", "diff", "--name-only"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(result.stdout)
            print('Please run "git status" or "git diff" to check local changes.')
            print(" ")
            print("This checker is EXPERIMENTAL at the moment and may make mistakes.")
            print(
                'If the result seems a false alarm, you shall utilize CQ Options (add "SkipChecks:copyright" in the'
                " commit message) to skip this. Don't forget to restore local changes if necessary."
            )
            print("Sorry for your trouble. Appreciate your help.")
            return CheckResult.FAILED
        else:
            return CheckResult.PASSED
