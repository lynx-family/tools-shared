# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import checkers.cpplint as cpplint
import checkers.format_file_filter as format_file_filter
from checkers.checker import Checker, CheckResult
from config import Config


class CpplintChecker(Checker):
    name = "cpplint"
    help = "Run cpplint"

    def run(self, options, mr, changed_files):
        forbidden_suffix = Config.value(
            "checker-config", "cpplint-checker", "ignore-suffixes"
        )
        forbidden_dirs = Config.value(
            "checker-config", "cpplint-checker", "ignore-dirs"
        )
        sub_git_dirs = Config.value("checker-config", "cpplint-checker", "sub-git-dirs")
        for filename in changed_files:
            if format_file_filter.shouldFormatFile(
                filename, forbidden_suffix, forbidden_dirs
            ):
                print(f"checking {filename}")
                cpplint.ProcessFileWithSubDirs(filename, 0, sub_git_dirs)
        if (cpplint.GetErrorCount()) > 0:
            print("Please check the following errors:\n")
            for error in cpplint.GetErrorStingList():
                print(("    %s" % error))
            return CheckResult.FAILED
        else:
            return CheckResult.PASSED
