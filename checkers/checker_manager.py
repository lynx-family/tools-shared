# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import checkers
import os
import sys
import importlib
from config import Config
from checkers.checker import Checker
from utils.find_classes import find_classes
from utils.merge_request import MergeRequest


def is_checker(cls):
    return issubclass(cls, Checker) and cls != Checker


class CheckerManager:
    def __init__(self, ignore):
        self.checker_classes = {
            c.name: c for c in find_classes(checkers, is_checker, recursive=False)
        }

        self.load_external_checker()
        self.remove_ignore_checker(ignore)
        default_disable_checkers = Config.value(
            "checker-config", "default-disable-checkers"
        )
        if default_disable_checkers is None:
            return
        disable_checkers = ",".join(default_disable_checkers)
        self.remove_ignore_checker(disable_checkers)

    def remove_ignore_checker(self, ignore):
        old_checker_class = self.checker_classes
        self.checker_classes = {
            name: cls
            for name, cls in old_checker_class.items()
            if name not in ignore.split(",")
        }

    def load_external_checker(self):
        external_checker_path = Config.value("external-checker-path")
        if external_checker_path is None:
            return
        mr = MergeRequest()
        project_root = mr.GetRootDirectory()
        abs_dir_path = os.path.abspath(external_checker_path)
        if not os.path.isdir(abs_dir_path):
            raise NotADirectoryError(f"The path {abs_dir_path} is not a directory.")
        sys.path.insert(0, project_root)
        try:
            external_checkers = external_checker_path.replace("/", ".")
            external_checkers_module = importlib.import_module(external_checkers)

            classes = find_classes(
                external_checkers_module, is_checker, recursive=False
            )
            for c in classes:
                self.checker_classes[c.name] = c
        except Exception as e:
            print(f"Import external checker error {e}")


if __name__ == "__main__":
    Config.init()
    CheckerManager()
