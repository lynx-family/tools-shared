# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import checkers.cpplint as cpplint
import checkers.format_file_filter as format_file_filter
from checkers.checker import Checker, CheckResult


class CpplintChecker(Checker):
    name = "cpplint"
    help = "Run cpplint"

    def run(self, options, mr, changed_files):
        for filename in changed_files:
            if format_file_filter.shouldFormatFile(filename):
                print(f"checking {filename}")
                cpplint.ProcessFile(filename, 0)
        if (cpplint.GetErrorCount()) > 0:
            print("Please check the following errors:\n")
            for error in cpplint.GetErrorStingList():
                print(("    %s" % error))
            return CheckResult.FAILED
        else:
            return CheckResult.PASSED
