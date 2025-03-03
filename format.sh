#!/usr/bin/env bash
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

find . -type f -name "*.py" -not -path "./venv/*" | grep '\.py$' | xargs black
