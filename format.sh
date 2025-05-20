#!/usr/bin/env bash
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

ignores=(
    "./venv/*" 
    "./buildtools/*"
)  

find_args=()

for item in "${ignores[@]}"; do
    find_args+=(-not -path "$item")
done

find . -type f -name "*.py" "${find_args[@]}" | xargs black
