# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os
import subprocess
import sys

from checkers.checker import Checker, CheckResult
from config import Config

ANDROID_PATH = Config.value("checker-config", "api-checker", "api-dirs", "android")
IOS_PATH = Config.value("checker-config", "api-checker", "api-dirs", "ios")
IOS_COMMON_PATH = Config.value(
    "checker-config", "api-checker", "api-dirs", "ios-common"
)
INSTRUCTION_DOC = Config.value("checker-config", "api-checker", "instruction-doc")


class APIChecker(Checker):
    name = "api-check"
    help = "Update api metadata"

    def run(self, options, mr, changed_files):
        if self.skip(options, mr, changed_files):
            return CheckResult.PASSED

        LYNX_ROOT_PATH = mr.GetRootDirectory()
        cmd = [
            sys.executable,
            os.path.join(LYNX_ROOT_PATH, "tools", "api", "main.py"),
            "-u",
        ]
        try:
            result = subprocess.run(cmd, text=True, check=True, cwd=LYNX_ROOT_PATH)
        except subprocess.CalledProcessError as e:
            print(e.stderr)
            return CheckResult.FAILED

        cmd = ["git", "diff"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if len(result.stdout) > 0 and (
            "lynx_android.api" in result.stdout or "lynx_ios.api" in result.stdout
        ):
            print(
                f"Found files possibly not containing proper api metadata, please refer to {INSTRUCTION_DOC} for more information."
            )
            print(result.stdout)
            print(
                'Please run "git status" or "git diff" to check local changes. You can "git add" these files and commit again.'
            )
            print(
                "If there are false positives or any other unexpected issues , please kindly inform 16253004+pilipala195@users.noreply.github.com the situation so that we shall improve it."
            )
            print("Sorry for your trouble. Appreciate your help.")

            return CheckResult.FAILED
        else:
            return CheckResult.PASSED

    def skip(self, options, mr, changed_files) -> bool:
        changed_files = [
            file
            for file in changed_files
            if (ANDROID_PATH in file and file.endswith(".java"))
            or ((IOS_PATH in file or IOS_COMMON_PATH in file) and file.endswith(".h"))
            or file.endswith(".api")
        ]
        if len(changed_files) == 0:
            print("No changed files related with lynx native api, skip api check")
            return True
        return False
