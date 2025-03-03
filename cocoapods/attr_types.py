#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.


class Raw:
    pass


class StringList:
    pass


class Rebase:

    def __init__(self, path, base):
        self.path = path
        self.base = base
