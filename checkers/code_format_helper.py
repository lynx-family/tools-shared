#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import subprocess, sys, os
from utils.merge_request import MergeRequest
from config import Config


def runCommand(cmd):
    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return p.stdout.readlines()


_CHECK_FORMAT_COMMAND = {
    ".yml": "npx --quiet --yes prettier@2.2.1",
    ".yaml": "npx --quiet --yes prettier@2.2.1",
    ".ts": "npx --quiet --yes prettier@2.2.1",
    ".tsx": "npx --quiet --yes prettier@2.2.1",
}

_CHECK_FORMAT_COMMAND_NO_INSTALL = {
    ".yml": "npx --quiet --no-install prettier@2.2.1",
    ".yaml": "npx --quiet --no-install prettier@2.2.1",
    ".ts": "npx --quiet --no-install prettier@2.2.1",
    ".tsx": "npx --quiet --no-install prettier@2.2.1",
}


def get_check_format_command(path):
    check_format_command = _CHECK_FORMAT_COMMAND

    # read configuration
    npx_no_install = Config.get("npx-no-install")
    if npx_no_install:
        check_format_command = _CHECK_FORMAT_COMMAND_NO_INSTALL

    for ext, command in list(check_format_command.items()):
        if path.endswith(ext):
            return command
    # defaults to clang-format
    return "clang-format -style=file"


def check_end_of_newline(path):
    cmd = "tail -c1 < {}".format(path)
    output = runCommand(cmd)
    return len(output) == 1 and output[0] == b"\n"


def check_gn_suffix(path):
    return path.endswith(".gn") or path.endswith(".gni")


def check_gn_format(path):
    cmd = "gn format --dry-run {}".format(path)
    output = runCommand(cmd)
    lines = int(len(output))
    return not lines and check_end_of_newline(path)


def check_format(path):
    if check_gn_suffix(path):
        return check_gn_format(path)
    cmd = "{} {} | diff {} - | wc -l".format(get_check_format_command(path), path, path)
    if os.path.islink(path):  # filter the symbol link file
        return True
    output = runCommand(cmd)
    lines = int(output[0].strip())
    return not lines and check_end_of_newline(path)


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
