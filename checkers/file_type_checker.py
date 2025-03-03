# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import re
import os
import subprocess

from checkers.checker import Checker, CheckResult
from config import Config


BINARY_FILES_ALLOW_LIST = Config.value(
    "checker-config", "file-type-checker", "binary-files-allow-list"
)


def is_binary(file_path):
    chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
    with open(file_path, "rb") as f:
        return bool(f.read(1024).translate(None, chars))


def in_allow_list(file_path):
    for r in BINARY_FILES_ALLOW_LIST:
        if re.search(r, file_path):
            return True
    return False


def is_lfs_files(file_path):
    lfs_files = get_lfs_files()
    if file_path in lfs_files:
        return True
    else:
        return False


def get_lfs_files():
    output = subprocess.check_output(["git", "lfs", "ls-files", "--name-only"])
    file_list = output.decode("utf-8").splitlines()
    return file_list


class FileTypeChecker(Checker):
    name = "file-type"
    help = "Check file type"

    def run(self, options, mr, changed_files):
        binary_files = []
        for filename in changed_files:
            print(f"checking {filename}")
            if in_allow_list(filename):
                continue
            if os.path.isdir(filename):
                continue
            if is_lfs_files(filename):
                continue
            if is_binary(filename):
                binary_files.append(filename)

        if len(binary_files) > 0:
            print("Please check the following errors:\n")
            print(
                "Binary files are not allowed to commit to the git repository. "
                "Please use Habitat tool to manage these files:\n"
            )
            print("    " + "\n    ".join(binary_files))
            return CheckResult.FAILED
        else:
            return CheckResult.PASSED
