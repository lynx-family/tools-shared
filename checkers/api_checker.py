# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os
import subprocess
import sys

from checkers.checker import Checker, CheckResult
from config import Config

API_CHECK_BIN = Config.value("checker-config", "api-checker", "api-check-bin")
FILE_SUFFIXES = Config.value("checker-config", "api-checker", "check-file-suffixes")
FILE_SUBPATHS = Config.value("checker-config", "api-checker", "check-file-subpaths")
JAVA_FILE_PATHS = Config.value("checker-config", "api-checker", "java-path")
CPP_FILE_PATHS = Config.value("checker-config", "api-checker", "cpp-path")
INSTRUCTION_DOC = Config.value("checker-config", "api-checker", "instruction-doc")


class APIChecker(Checker):
    name = "api-check"
    help = "Update api metadata"

    def run(self, options, mr, changed_files):
        if self.skip(options, mr, changed_files):
            return CheckResult.PASSED

        LYNX_ROOT_PATH = mr.GetRootDirectory()
        api_check_bin = os.path.join(LYNX_ROOT_PATH, API_CHECK_BIN)
        if not os.path.exists(api_check_bin):
            print(f"api check bin {api_check_bin} not exists")
            return CheckResult.PASSED
        cmd = [
            sys.executable,
            api_check_bin,
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
            "lynx_android.api" in result.stdout
            or "lynx_ios.api" in result.stdout
            or "lynx_harmony.api" in result.stdout
        ):
            print(
                f"Found files possibly not containing proper api metadata, please refer to {INSTRUCTION_DOC} for more information."
            )
            print(result.stdout)
            print(
                'Please run "git status" or "git diff" to check local changes. You can "git add" these files and commit again.'
            )
            print(
                "If there are false positives or any other unexpected issues , please create an issue and inform @pilipala195 the situation so that we shall improve it."
            )
            print("Sorry for your trouble. Appreciate your help.")

            return CheckResult.FAILED
        else:
            return CheckResult.PASSED

    def skip(self, options, mr, changed_files) -> bool:
        if options.all:
            return False

        new_changed_files = []
        for file in changed_files:
            if file.endswith(".java"):
                for java_path in JAVA_FILE_PATHS:
                    if java_path in file:
                        new_changed_files.append(file)
                        break
            elif file.endswith(".h"):
                for cpp_path in CPP_FILE_PATHS:
                    if cpp_path in file:
                        new_changed_files.append(file)
                        break
            else:
                for suffix in FILE_SUFFIXES:
                    if file.endswith(suffix):
                        new_changed_files.append(file)
                        return
                for subpath in FILE_SUBPATHS:
                    if subpath in file:
                        new_changed_files.append(file)
                        return

        if len(new_changed_files) == 0:
            print("No changed files related with lynx native api, skip api check")
            return True
        return False
