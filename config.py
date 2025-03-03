# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os
from utils.merge_request import MergeRequest
import subprocess
import sys
from checkers.default_config import checker_default_config


class Config:
    data = {}

    @staticmethod
    def init():
        # merge checker default config
        Config.data["checker-config"] = checker_default_config
        Config.data["external_checker_path"] = None
        # merge custom config
        mr = MergeRequest()
        root_dir = mr.GetRootDirectory()
        config_path = os.path.join(root_dir, ".tools_shared")
        if os.path.exists(config_path):
            try:
                import yaml
            except ImportError:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "PyYAML~=6.0"]
                )
                import yaml
            with open(config_path, encoding="utf-8") as config_f:
                Config.data = Config.merge(
                    Config.data, yaml.load(config_f, Loader=yaml.FullLoader)
                )

    @staticmethod
    def merge(target, source):
        for key, value in source.items():
            if key not in target:
                raise KeyError(f"Key not found: {key}")
            if isinstance(value, dict) and isinstance(target[key], dict):
                target[key] = Config.merge(target[key], value)
            else:
                target[key] = value
        return target

    @staticmethod
    def get(key):
        return Config.data.get(key)

    @staticmethod
    def value(*args):
        target_obj = Config.data
        index = 1
        for arg in args:
            if arg in target_obj:
                if index == len(args):
                    return target_obj[arg]
                else:
                    index += 1
                    target_obj = target_obj[arg]
            else:
                return None


if __name__ == "__main__":
    Config.init()
    # print(Config.value("checker-config", "file-type-checker"))
    print(Config.data)
