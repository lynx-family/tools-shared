#!/usr/bin/env python
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import subprocess


class MergeRequest:
    def __init__(self):
        pass

    def RunCommand(self, command):
        p = subprocess.Popen(
            " ".join(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        result, error = p.communicate()
        # Compatibale with Python 3.
        # Since the return value of communicate is bytes instead of str in Python 3.
        return result.decode("utf-8"), error.decode("utf-8")

    # Get project/git root directory
    def GetRootDirectory(self):
        command = ["git", "rev-parse", "--show-toplevel"]
        result, error = self.RunCommand(command)
        if error:
            print(
                (
                    "Error, can not get top directory, make sure it is a git repo: %s"
                    % (error)
                )
            )
            return None
        return result.strip()

    # Get uncommitted changed files.
    def GetChangedFiles(self):
        file_list = []
        # Staged files
        command = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"]
        result, error = self.RunCommand(command)
        if error:
            print(
                (
                    "Error, can not get staged files, make sure it is a git repo: %s"
                    % (error)
                )
            )
        for filename in result.split("\n"):
            filename = filename.strip()
            if filename and filename != "":
                file_list.append(filename)
        # Unstaged files
        command = ["git", "diff", "--name-only", "--diff-filter=ACMRT"]
        result, error = self.RunCommand(command)
        if error:
            print(
                (
                    "Error, can not get staged files, make sure it is a git repo: %s"
                    % (error)
                )
            )
        for filename in result.split("\n"):
            filename = filename.strip()
            if filename and filename != "":
                file_list.append(filename)
        return file_list

    # Get changed files of last commit.
    def GetLastCommitFiles(self):
        command = [
            "git",
            "show",
            "HEAD",
            "--diff-filter=d",
            "--name-only",
            "--pretty=format:",
        ]
        result, error = self.RunCommand(command)
        if error:
            print(("Error: can not get change list of last commit: %s" % (error)))
            return []
        file_list = []
        for filename in result.split("\n"):
            filename = filename.strip()
            if filename and filename != "":
                file_list.append(filename)
        return file_list

    def GetLastCommitLines(self):
        cmd = ["git", "diff", "HEAD^", "HEAD", "-U0"]
        result, error = self.RunCommand(cmd)
        if error:
            print(("Error, can not get changed lines of last commit: %s" % error))
        return result

    # Get commit log of last commit.
    def GetCommitLog(self):
        command = ["git", "log", "--format=%B", "-n", "1"]
        result, error = self.RunCommand(command)
        if error:
            print("Error: can not get the commit log of last change.")
            return None
        return result

    # Get all file in the repo.
    def GetAllFiles(self):
        command = ["git", "ls-tree", "--full-tree", "-r", "--name-only", "HEAD"]
        result, error = self.RunCommand(command)
        if error:
            print("Error: can not get all files, please check it is a git repo.")
            return None
        file_list = []
        for filename in result.split("\n"):
            filename = filename.strip()
            if filename and filename != "":
                file_list.append(filename)
        return file_list


if __name__ == "__main__":
    mr = MergeRequest()
    print((mr.GetRootDirectory()))
    print((mr.GetChangedFiles()))
    print((mr.GetCommitLog()))
    print((mr.GetAllFiles()))
