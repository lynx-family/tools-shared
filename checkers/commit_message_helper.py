#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import re

ERROR_NO_ERROR = 0
ERROR_MALFORMED_MESSAGE = 1
ERROR_MISSING_ISSUE = 2


def IsRevertedCommit(commit_lines):
    for line in commit_lines[1:]:
        if re.match(r"This reverts commit *", line):
            return True
    return False


def IsAutoRollCommit(commit_lines):
    if re.match(r"\[AutoRoll\] Roll revisions automatically *", commit_lines[0]):
        return True
    return False


def CheckCommitMessage(message):
    error_code, error_message = ERROR_NO_ERROR, ""
    commit_lines = message.strip().split("\n")
    # skip revert commit

    if IsRevertedCommit(commit_lines):
        return error_code, error_message
    elif IsAutoRollCommit(commit_lines):
        return error_code, error_message
    else:
        reg_str = r"(\[\S+\])(\s*(\S+))+$"
        if re.match(reg_str, commit_lines[0]):
            pass
        # check title
        else:
            return (
                ERROR_MALFORMED_MESSAGE,
                f'Malformed title. Title "{commit_lines[0]} not match reg "{reg_str}"',
            )

        if commit_lines[1] != "":
            return (
                ERROR_MALFORMED_MESSAGE,
                "No empty lines found between title and summary.",
            )

        # Currently only check whether the 'issue' line is present.
        error_code, error_message = ERROR_MISSING_ISSUE, "Missing issue"
        summary = ""
        for line in commit_lines[2:]:
            summary += line
            if re.match(
                r"((issue):\s*([FfMm]-|(\#))(\d)+)|(no-((meego)|(workitem)))", line
            ):
                if len(summary.strip()) == 0:
                    return ERROR_MALFORMED_MESSAGE, "No summary found."
                error_code, error_message = ERROR_NO_ERROR, ""
                break
    return error_code, error_message


if __name__ == "__main__":
    CheckCommitMessage("Intent to fail")
