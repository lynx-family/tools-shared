#!/usr/bin/env python
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
"""
This script check if test targets can be built.
"""

import os
import subprocess
import sys
import platform

from config import Config
import checkers.code_format_helper
import checkers.format_file_filter
from checkers.checker import Checker, CheckResult

system = platform.system().lower()


def CheckGNDependency():
    gn_common_build_args = Config.value("checker-config", "deps-checker", "gn-args")
    if system == "darwin":
        gn_common_build_args += ' target_os="ios"'
    gn_gen_cmd = """gn gen out/Default --args='%s' """ % (gn_common_build_args)
    gn_check_cmd = "gn check out/Default"
    # check specific targets to prevent being affected by the changes
    targets_to_be_checked = Config.value("checker-config", "deps-checker", "gn-targets")

    subprocess.check_call(gn_gen_cmd, shell=True)

    for target in targets_to_be_checked:
        print("Checking header dependency for " + target)
        subprocess.check_call(gn_check_cmd + " " + target, shell=True)

    # ignore check all now because we are migrating lynx code
    # check all targets
    # if system == "darwin":
    #     subprocess.check_call(gn_check_cmd, shell=True)

    # generate remaining no check targets errors information
    GenerateNoCheckTargetsInfo()

    # check source files
    if system == "darwin":
        AnalyzeGnSourceFileCheckResult()


def GenerateNoCheckTargetsInfo():
    result = subprocess.run(
        r"gn check out/Default | grep -E -A1 '(The target:|It is not in)' | grep '//' | grep -v '//build/toolchain' | cut -f1 -d: | sort | uniq -c | sed -e 's/ *\([0-9]*\) *\(.*\)/  \"\2:*\",  # \1 errors/'",
        shell=True,
        encoding="utf-8",
    )

    if result.returncode == 0 and result.stdout:
        for line in result.stdout.splitlines():
            print(line)


def AnalyzeGnSourceFileCheckResult():
    source_file_check_ignore_folders = Config.value(
        "checker-config", "deps-checker", "ignore-dirs"
    )
    check_result = subprocess.check_output(
        r"gn check --force out/Default '*' | grep -E -A6 '(Source file not found)'",
        shell=True,
        encoding="utf-8",
    )
    missing_targets = {}
    get_target_next_line = False
    get_source_file_next_line = False
    cur_target = ""
    if check_result:
        for line in check_result.splitlines():
            if get_target_next_line:
                get_target_next_line = False
                cur_target = line
                continue
            if get_source_file_next_line and cur_target:
                get_source_file_next_line = False
                if line.find("/gen/") != -1:  # ignore generated files
                    continue
                if cur_target not in missing_targets:
                    missing_targets[cur_target] = set()
                missing_targets[cur_target].add(line)
                cur_target = ""
                continue
            if line.startswith("The target:"):
                get_target_next_line = True
                continue
            if line.startswith("has a source file:"):
                get_source_file_next_line = True

    raise_exception = False
    for target, source_files in missing_targets.items():
        ignore_target = False
        for ignore_folder in source_file_check_ignore_folders:
            if target.find(ignore_folder) != -1:
                ignore_target = True
                break
        if ignore_target:
            continue

        print(f"{target.strip()} has missing source files:")
        for source_file in source_files:
            print(f"  {source_file.strip()}")
        # not raise exception for now because it is not checked on CQ
        # raise_exception = True

    if raise_exception:
        raise Exception("source files missing")

    return missing_targets


class DependencyChecker(Checker):
    name = "deps"
    help = "Check dependency validity"

    def run(self, options, mr, changed_files):
        try:
            CheckGNDependency()
        except:
            return CheckResult.FAILED
        return CheckResult.PASSED
