# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import sys

from checkers.checker import Checker, CheckResult
from checkers.commit_message_helper import CheckCommitMessage


class CommitMessageChecker(Checker):
    name = "commit-message"
    help = "Check style of commit message"

    def run(self, options, mr, changed_files):
        print("Checking commit message...")
        commit_message = mr.GetCommitLog()
        has_error, message = CheckCommitMessage(commit_message)
        if has_error:
            print("Error checking commit message:")
            print(("    ==> %s\n" % message))
            print("The commit message should be formatted as follow:\n")
            print(
                "    [label] {title}\n\n"
                "    {summary}\n\n"
                "    issue: #issueID\n"
                "    doc: https://xxxxxx (Optional)\n"
                "    TEST: Test cases (Optional)\n"
            )
            print("Please make sure the commit message conforms to:")
            print("    https://XXX\n")
            return CheckResult.FAILED
        else:
            return CheckResult.PASSED
