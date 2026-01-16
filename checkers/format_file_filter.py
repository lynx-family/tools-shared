#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import re
import sys, os, subprocess
import platform
from utils.merge_request import MergeRequest
from config import Config

system = platform.system().lower()
gn_path = "gn"

# Only check format for following file types.
_FILE_EXTENSIONS = [
    ".java",
    ".h",
    ".hpp",
    ".c",
    ".cc",
    ".cpp",
    ".m",
    ".mm",
    ".ts",
    ".tsx",
    ".yml",
    ".yaml",
    ".gn",
    ".gni",
]
# Commands should be used.
_FORMAT_COMMAND = {
    ".yml": ["npx", "--quiet", "--yes", "prettier@2.2.1 -w"],
    ".yaml": ["npx", "--quiet", "--yes", "prettier@2.2.1 -w"],
    ".ts": ["npx", "--quiet", "--yes", "prettier@2.2.1 -w"],
    ".tsx": ["npx", "--quiet", "--yes", "prettier@2.2.1 -w"],
    ".gn": ["{} format ".format(gn_path)],
    ".gni": ["{} format ".format(gn_path)],
}
__FORMAT_COMMAND_NO_INSTALL = {
    ".yml": ["npx", "--quiet", "--no-install", "prettier@2.2.1"],
    ".yaml": ["npx", "--quiet", "--no-install", "prettier@2.2.1"],
    ".ts": ["npx", "--quiet", "--no-install", "prettier@2.2.1"],
    ".tsx": ["npx", "--quiet", "--no-install", "prettier@2.2.1"],
    ".gn": ["{} format ".format(gn_path)],
    ".gni": ["{} format ".format(gn_path)],
}


def init(options):
    if options.ktlint:
        # if ktlint enabled, add ktlint rules
        _FORMAT_COMMAND.update({".kt": ["ktlint -F"]})
        __FORMAT_COMMAND_NO_INSTALL.update({".kt": "ktlint -F"})
        _FILE_EXTENSIONS.append(".kt")


def filterFileExtension(path):
    for ext in _FILE_EXTENSIONS:
        if path.endswith(ext):
            return True
    return False


def filterSuffix(path, forbidden_suffixes):
    for suffix in forbidden_suffixes:
        if path.endswith(suffix):
            return False
    return True


def filterPathPrefix(path, forbidden_dirs):
    for dir in forbidden_dirs:
        if re.match(dir, path):
            return False
    return True


def getEndWithNewlineCommand(path):
    if system == "windows":
        return [
            f'$content = Get-Content -Path "{path}" -Raw; if (-not $content.EndsWith(\\"`n\\")) {{ Add-Content -Path "{path}" -Value \\"`n\\" -NoNewline }}'
        ]
    else:
        return [
            "tail",
            "-c1",
            "<",
            path,
            "|",
            "read",
            "-r",
            "_",
            "||",
            "echo",
            ">>",
            path,
        ]


def getClangFormatCommand(path, is_in_place):
    if is_in_place:
        return ["clang-format", "-style=file", "-i", path]
    return ["clang-format", "-style=file", path]


def addCommandIfNeeded(cmd_one, cmd_two, is_needed):
    if is_needed:
        if system == "windows":
            # On windows, concatenate commands into a string and execute them using PowerShell.
            command_1 = " ".join(cmd_one)
            command_2 = " ".join(cmd_two)
            return ["powershell", "-Command", f"{command_1}; {command_2}"]
        else:
            return cmd_one + [";"] + cmd_two
    else:
        return cmd_one


def getFormatCommand(path, is_in_place=True):
    format_command = __FORMAT_COMMAND_NO_INSTALL
    if is_in_place:
        format_command = _FORMAT_COMMAND

    for ext, command in format_command.items():
        if path.endswith(ext):
            return addCommandIfNeeded(
                command + [path], getEndWithNewlineCommand(path), is_in_place
            )
    # defaults to clang-format
    return addCommandIfNeeded(
        getClangFormatCommand(path, is_in_place),
        getEndWithNewlineCommand(path),
        is_in_place,
    )


def shouldFormatFile(path, forbidden_suffixes=[], forbidden_dirs=[]):
    return (
        filterFileExtension(path)
        and filterSuffix(path, forbidden_suffixes)
        and filterPathPrefix(path, forbidden_dirs)
    )


if __name__ == "__main__":

    def testFile(path):
        print(("test for path: " + str(path)))
        print(("filterFileExtension: " + str(filterFileExtension(path))))
        print(("filterSuffix: " + str(filterSuffix(path))))
        print(("filterPathPrefix: " + str(filterPathPrefix(path))))
        print(("shouldFormatFile: " + str(shouldFormatFile(path))))
        print(("getFormatCommand: " + str(getFormatCommand(path))))
        print("")

    testFile("aaa.h")
    testFile("test/B.java")
    testFile("dafdasf.js")
    testFile("Lynx/aaa_jni.h")
    testFile("Lynx/BUILD.gn")
    testFile("core/Lynx.gni")
    testFile("Lynx/third_party/ddd.h")
    testFile("oliver/lynx-kernel/src/index.ts")
    testFile("oliver/lynx-kernel/gulpfile.js")
    testFile("oliver/compiler-ng/src/index.ts")
