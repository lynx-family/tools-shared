#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import re
import sys, os, subprocess
import platform
from utils.merge_request import MergeRequest
from config import Config
import checkers.cpplint as cpplint

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
    ".yml": "npx --quiet --no-install prettier@2.2.1",
    ".yaml": "npx --quiet --no-install prettier@2.2.1",
    ".ts": "npx --quiet --no-install prettier@2.2.1",
    ".tsx": "npx --quiet --no-install prettier@2.2.1",
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


def getFormatCommand(path):
    format_command = _FORMAT_COMMAND

    # read configuration
    npx_no_install = Config.get("npx-no-install")
    if npx_no_install:
        format_command = __FORMAT_COMMAND_NO_INSTALL

    for ext, command in list(format_command.items()):
        if path.endswith(ext):
            if system == "windows":
                # On windows, concatenate commands into a string and execute them using PowerShell.
                command_str = " ".join(command + [path])
                newline_command = " ".join(getEndWithNewlineCommand(path))
                return ["powershell", "-Command", f"{command_str}; {newline_command}"]
            else:
                return command + [path] + [";"] + getEndWithNewlineCommand(path)
    if path.endswith("h") or path.endswith("hpp"):
        cpplint.ProcessFileForLynx(path, 6)
    # defaults to clang-format
    if system == "windows":
        clang_command = " ".join(["clang-format", "-i", path])
        newline_command = " ".join(getEndWithNewlineCommand(path))
        return ["powershell", "-Command", f"{clang_command}; {newline_command}"]
    return ["clang-format", "-i", path] + [";"] + getEndWithNewlineCommand(path)


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
