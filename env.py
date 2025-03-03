#!/usr/bin/env python
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os

script_path = os.path.abspath(__file__)
root_dir = os.path.dirname(script_path)


class Env:
    BUILD_TOOLS_PATH = os.path.join(root_dir, "buildtools")
    JAVA_LINT_CONFIG_PATH = os.path.join(root_dir, "checkers", "java-lint-check")
    SELF_ROOT_PATH = script_path
