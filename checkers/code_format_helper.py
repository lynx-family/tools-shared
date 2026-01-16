#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import subprocess
import sys
import os
from utils.merge_request import MergeRequest
from config import Config
import checkers.format_file_filter as format_file_filter


def runCommand(cmd):
    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return p.stdout.readlines()


def check_end_of_newline(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return False
            f.seek(-1, os.SEEK_END)
            return f.read(1) == b"\n"
    except Exception:
        return False


def check_format(path):
    if os.path.islink(path):  # filter the symbol link file
        return True
    if not check_end_of_newline(path):
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            original_content = f.read()

        format_cmd = format_file_filter.getFormatCommand(path, False)
        formatted_result = subprocess.run(
            " ".join(format_cmd), shell=True, capture_output=True, text=True
        )
        if formatted_result.returncode != 0:
            return False

        formatted_content = formatted_result.stdout
        return original_content == formatted_content

    except Exception:
        return False


def cd_to_git_root_directory():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir_path)
    dir = runCommand("git rev-parse --show-toplevel")[0].strip()
    os.chdir(dir)


def print_current_path():
    cwd = os.getcwd()
    print(("current path:" + cwd))


if __name__ == "__main__":
    print_current_path()
    cd_to_git_root_directory()
    print_current_path()
