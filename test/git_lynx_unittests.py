# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import shutil

import os
import unittest
import optparse
import subprocess
import git_lynx

INTERMEDIATE_DIR = "intermediate"

old_cwd = ""


def commit_valid_change():
    with open("hello.cpp", "w") as f:
        f.write(
            """
// Copyright 2023

#include <iostream>
using namespace std; // NOLINT

int main() {
  cout << "Hello, World!" << endl;
  return 0;
}"""
        )
    subprocess.check_call(["git", "add", "."])
    subprocess.check_call(["git", "commit", "-m", "valid"])


def commit_invalid_change():
    with open("hello_invalid.cpp", "w") as f:
        f.write(
            """
#include <iostream>
using namespace std;
int main() {
    cout << "Hello, World!" << endl;
  return 0;
}
      """
        )
    subprocess.check_call(["git", "add", "."])
    subprocess.check_call(["git", "commit", "-m", "invalid"])


class GitLynxTest(unittest.TestCase):

    def setUp(self):
        print("setUp")

    def tearDown(self):
        print("tearDown")

    def checkout(tag_or_commit):
        subprocess.check_call(["git", "checkout", tag_or_commit])

    def checkGitStatusClean(working_tree=True):
        command = ["git", "diff"]
        if not working_tree:
            command.append("--cached")
        result = subprocess.check_output(command)
        print(f"git status: {result}")
        return not result or result == ""

    def test_format_no_change(self):
        print("test format with valid change")

        print("check valid")
        commit_valid_change()
        git_lynx.CMDformat(optparse.OptionParser(), ["--verbose"])
        self.assertTrue(self.checkGitStatusClean())
        print("check invalid")
        commit_invalid_change()
        git_lynx.CMDformat(optparse.OptionParser(), ["--verbose"])
        self.assertFalse(self.checkGitStatusClean())


if __name__ == "__main__":
    old_cwd = os.getcwd()

    shutil.rmtree(INTERMEDIATE_DIR, True)
    os.makedirs(INTERMEDIATE_DIR)
    os.chdir(INTERMEDIATE_DIR)

    unittest.main()

    os.chdir(old_cwd)
