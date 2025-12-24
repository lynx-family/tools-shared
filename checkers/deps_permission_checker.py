#!/usr/bin/env python3
# Copyright 2023 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import os
import re
import requests
import subprocess
from subprocess import Popen, PIPE
from config import Config

from checkers.checker import Checker, CheckResult

CHECK_REPO_PERMISSION_URL = Config.value(
    "checker-config", "deps-permission-checker", "check-repo-permission-url"
)
HAB_COMMAND = Config.value("checker-config", "deps-permission-checker", "hab-command")
DEPS_TARGET_WHITE_LIST = Config.value(
    "checker-config", "deps-permission-checker", "deps-target-white-list"
)
REPO_URL_PATTERN = Config.value(
    "checker-config", "deps-permission-checker", "repo-url-pattern"
)

"""
Check the Habitat source code repositories added in the Habitat DEPS files,
and verify whether the repository has added access permissions to the necessary robot accounts.
"""


class DepsPermissionChecker(Checker):
    name = "deps-permission"
    help = "Check Deps Permission"

    def check_changed_lines(self, options, lines, line_indexes, changed_files):
        deps_changed = False
        for f in changed_files:
            if re.search(r"^DEPS(\..*)?$", os.path.basename(f)):
                deps_changed = True
                break

        if not deps_changed:
            print("No DEPS changed. Skip check.")
            return CheckResult.PASSED

        command = f"{HAB_COMMAND}{','.join(DEPS_TARGET_WHITE_LIST)}"
        if not command or not REPO_URL_PATTERN:
            print("Check repo permission config is empty. Skip check.")
            return CheckResult.PASSED
        try:
            output = subprocess.check_output(
                command, shell=True, stderr=subprocess.STDOUT
            ).decode("utf-8")
            output_array = output.split("\n")
            for item in output_array:
                match_result = re.findall(REPO_URL_PATTERN, item)
                if match_result is not None and len(match_result) > 0:
                    json = {
                        "repo": match_result[0],
                    }
                    res = requests.post(url=CHECK_REPO_PERMISSION_URL, json=json)
                    res.raise_for_status()
                    json_res = res.json()
                    if json_res["status"] == "fail":
                        print(
                            "Failed to check repo permission:\n" + json_res["message"]
                        )
                        return CheckResult.FAILED
        except subprocess.CalledProcessError as err:
            print(f"Check repo permission meets error: {err.output.decode()}")
            return CheckResult.FAILED
        return CheckResult.PASSED
