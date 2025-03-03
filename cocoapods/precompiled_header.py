#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import os.path


def get_platform_import_header(platform):
    if platform == "ios":
        return "#import <UIKit/UIKit.h>\n"
    elif platform == "tvos":
        return "#import <UIKit/UIKit.h>\n"
    elif platform == "osx":
        return "#import <Cocoa/Cocoa.h>\n"
    return "#import <Foundation/Foundation.h>\n"


class PrecompiledHeader:

    def __init__(self, platform=None):
        self._imports = []
        self._platform = platform

    def add_import(self, imp_):
        self._imports.append(imp_)

    @property
    def imports(self):
        return self._imports

    def generate(self):
        result = ""
        result += "#ifdef __OBJC__\n"
        result += get_platform_import_header(self._platform)
        result += "#else\n"
        result += "#ifndef FOUNDATION_EXPORT\n"
        result += "#if defined(__cplusplus)\n"
        result += '#define FOUNDATION_EXPORT extern "C"\n'
        result += "#else\n"
        result += "#define FOUNDATION_EXPORT extern\n"
        result += "#endif\n"
        result += "#endif\n"
        result += "#endif\n"
        result += "\n"
        return result

    def save_to(self, path):
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, "w") as f:
            f.write(self.generate())
