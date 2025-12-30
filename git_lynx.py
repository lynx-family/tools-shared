#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import inspect
import json
import optparse
import os
import pkgutil
import requests

import checkers
import subcommand
import sys
import subprocess

from checkers.checker import Checker, CheckResult
from checkers.checker_manager import CheckerManager
from utils.merge_request import MergeRequest
from config import Config


def print_cutting_line(desc="", width=80):
    if desc:
        half_line = "=" * int((width - len(desc) - 2) / 2)
        line = half_line + " " + desc + " " + half_line
        if len(line) < width:
            line = line + "="
    else:
        line = "=" * width
    print(line)


# git lynx build: Run build.
def CMDbuild(parser, args):
    parser.add_option("--ios", action="store_true", help="Check iOS build.")
    parser.add_option("--android", action="store_true", help="Check Android build")
    parser.add_option("--unittests", action="store_true", help="Check unittests build")
    parser.add_option(
        "--encoder-ut", action="store_true", help="Check encoder ut build"
    )
    parser.add_option("--debug", action="store_true", help="If --debug, Build debug ut")
    parser.add_option("--asan", action="store_true", help="run ut on asan mode")
    options, args = parser.parse_args(args)
    mr = MergeRequest()
    root_directory = mr.GetRootDirectory()
    try:
        ci_build_path = os.path.join(root_directory, "tools", "ci")
        sys.path.append(ci_build_path)
        from check_android_build import CheckAndroidBuild
        from check_test_build import CheckTestTargetBuild, CheckEncoderUTBuild
    except ImportError as error:
        print(("Import Error: %s" % (error)))
    old_cwd = os.getcwd()
    os.chdir(root_directory)
    try:
        if options.unittests:
            CheckTestTargetBuild(options)
        elif options.encoder_ut:
            CheckEncoderUTBuild(options)
        elif options.android:
            CheckAndroidBuild()
        else:
            print("Error build check: invalid target")
    finally:
        os.chdir(old_cwd)


def CMDcheck(parser, args):
    parser.add_option("--checkers", help="Checkers to run, default all", default="all")
    parser.add_option("--list", action="store_true", help="List available checkers")
    parser.add_option(
        "--all", action="store_true", help="Check all source files in the project."
    )
    parser.add_option("--changed", action="store_true", help="Check all changed files")
    parser.add_option("--verbose", action="store_true", help="Print details")

    parser.add_option(
        "--ignore", help="Ignore checkers, separated with commas", default="none"
    )

    options, args = parser.parse_args(args)

    checker_manager = CheckerManager(options.ignore)

    if options.list:
        print("Available checkers:")
        print(
            "\n\n".join(
                "  " + name + ": " + cls.help
                for name, cls in checker_manager.checker_classes.items()
            )
        )
        return

    mr = MergeRequest()
    if options.all:
        changed_files = mr.GetAllFiles()
    elif options.changed:
        changed_files = mr.GetChangedFiles()
    else:
        changed_files = mr.GetLastCommitFiles()

    if options.verbose:
        print("Changed files:\n  " + "\n  ".join(changed_files) + "\n")

    # If a user specifies to skip certain check(s) in the commit message, skip local check(s)
    # as well.
    #
    # e.g. adding a "SkipChecks: dependency-check, macros-check" at the end of commit message
    # to skip CQ jobs dependency-check and macros-check as well as local git lynx check of
    # deps and macro.
    log = mr.GetCommitLog().split("\n")
    skipped_checks = []
    for line in log:
        if line.startswith("SkipChecks:"):
            items = line.split(":", 1)[1].split(",")
            skipped_checks.extend([i.strip() for i in items])

    if skipped_checks:
        print(f"{skipped_checks} has been skipped due to commit message.")

    # filter checkers
    target_checkers = []
    if options.checkers == "all":
        target_checkers = [
            c()
            for c in checker_manager.checker_classes.values()
            if c.name not in skipped_checks
        ]
    else:
        checker_names = options.checkers.split(",")
        for name in checker_names:
            if name not in checker_manager.checker_classes:
                raise Exception("Checker " + name + " not found")
            if name not in skipped_checks:
                target_checkers.append(checker_manager.checker_classes.get(name)())
    old_cwd = os.getcwd()
    os.chdir(mr.GetRootDirectory())
    try:
        for c in target_checkers:
            if options.checkers != "all" and c.name not in options.checkers.split(","):
                continue
            print_cutting_line(c.name)
            res = c.run(options, mr, changed_files)
            print("\n[%s] %s" % (c.name, res))
            print_cutting_line()
            print("")
            if res != CheckResult.PASSED:
                sys.exit(1)
    finally:
        os.chdir(old_cwd)


# git lynx format: Run clang-format for lynx
def CMDformat(parser, args):
    parser.add_option(
        "--all", action="store_true", help="Format all source files in the project."
    )
    parser.add_option("--changed", action="store_true", help="Format all changed files")
    parser.add_option(
        "--verbose", action="store_true", help="Verbose the process of clang-format."
    )
    parser.add_option(
        "--ktlint", action="store_true", help="Enable kotlin format with ktlint"
    )
    options, args = parser.parse_args(args)
    try:
        import checkers.format_file_filter as format_file_filter
    except ImportError:
        print("Can not find format_file_filter in the project.")
        return 1
    old_cwd = os.getcwd()
    mr = MergeRequest()
    os.chdir(mr.GetRootDirectory())
    forbidden_suffix = Config.value(
        "command-config", "format-command", "ignore-suffixes"
    )
    forbidden_dirs = Config.value("command-config", "format-command", "ignore-dirs")
    format_file_filter.init(options)
    try:
        if options.all:
            changed_files = mr.GetAllFiles()
        elif options.changed:
            changed_files = mr.GetChangedFiles()
        else:
            changed_files = mr.GetLastCommitFiles()
        for filename in changed_files:
            if format_file_filter.shouldFormatFile(
                filename, forbidden_suffix, forbidden_dirs
            ):
                command = format_file_filter.getFormatCommand(filename)
                output, error = mr.RunCommand(command)
                if error:
                    print(("Error clang-format %s: %s" % (filename, error)))
                    continue
                if options.verbose:
                    print(("Formatting %s: %s" % (filename, output)))
    finally:
        os.chdir(old_cwd)


# git lynx commit:  The encapsulation of [git commit -t (template-file) ],
# the commit message template used is located in /git_templates/normal.
# When editing the commit message, [label], summary, and issue fields are automatically generated .
def CMDcommit(parser, args):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.system("git commit -t" + script_dir + "/git_templates/normal")


# git lynx aicommit: Generate an AI-powered commit message based on git diff
def CMDaicommit(parser, args):
    parser.add_option(
        "--issue-id",
        help="Optional issue ID to include in the commit message",
        default="",
    )
    parser.add_option(
        "--doc-id",
        help="Optional document ID to include in the commit message",
        default="",
    )
    parser.add_option(
        "--thinking",
        action="store_true",
        help="Enable extended thinking mode for better reasoning",
        default=False,
    )
    options, args = parser.parse_args(args)

    mr = MergeRequest()

    output, error = mr.RunCommand(["git", "diff", "--cached"])
    if error:
        print(f"Error getting git diff: {error}")
        sys.exit(1)

    git_diff = output
    if not git_diff:
        print("No changes to commit. Please stage your changes first.")
        sys.exit(1)

    diff_length = len(git_diff)
    print(f"Staged diff length: {diff_length} characters")
    print()

    payload = {
        "git_diff": git_diff,
        "issue_id": options.issue_id,
        "doc_id": options.doc_id,
        "thinking": options.thinking,
    }

    open_api_url = Config.value("ai-commit-request-url")
    if not open_api_url:
        print(
            "AI commit message API URL not configured. Please set it in the your .tools_shared file."
        )
        sys.exit(1)
    try:
        response = requests.post(
            open_api_url,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error calling AI commit message API: {e}")
        sys.exit(1)

    try:
        result = response.json()
        if result.get("code") != 0:
            print(f'API Error: {result.get("msg", "Unknown error")}')
            sys.exit(1)

        commit_message = result.get("data", {}).get("commit_message", "")
        if not commit_message:
            print("No commit message generated. Please try again.")
            sys.exit(1)

        print("Generated commit message:")
        print("-" * 80)
        print(commit_message)
        print("-" * 80)

    except json.JSONDecodeError:
        print("Error parsing API response")
        sys.exit(1)


def CMDhelp(parser, args):
    if not any(i in ("-h", "--help") for i in args):
        args = args + ["--help"]
    parser.parse_args(args)
    assert False


class OptionParser(optparse.OptionParser):
    def __init__(self, *args, **kwargs):
        optparse.OptionParser.__init__(self, *args, prog="git lynx", **kwargs)

    def parse_args(self, args=None, _values=None):
        try:
            return self._parse_args(args)
        finally:
            pass

    def _parse_args(self, args=None):
        # Create an optparse.Values object that will store only the actual passed
        # options, without the defaults.
        actual_options = optparse.Values()
        _, args = optparse.OptionParser.parse_args(self, args, actual_options)
        # Create an optparse.Values object with the default options.
        options = optparse.Values(self.get_default_values().__dict__)
        # Update it with the options passed by the user.
        options._update_careful(actual_options.__dict__)
        return options, args


def main(argv):
    usage = "git lynx subcommand"
    dispatcher = subcommand.CommandDispatcher(__name__)

    dispatcher.execute(OptionParser(), argv)


if __name__ == "__main__":
    Config.init()
    sys.exit(main(sys.argv[1:]))
