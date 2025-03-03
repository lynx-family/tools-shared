# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import inspect
import pkgutil
import sys
import importlib
import os


def find_classes(module, is_target=None, handle_error=None, recursive=True):
    classes = set()
    submodules = []
    if not inspect.ismodule(module):
        return classes
    for info, name, is_pkg in pkgutil.iter_modules(module.__path__):
        full_name = module.__name__ + "." + name
        mod = sys.modules.get(full_name)
        if not mod:
            try:
                mod = info.find_module(full_name).load_module(full_name)
            except AttributeError:
                mod = info.find_spec(full_name).loader.load_module(full_name)
            except Exception as e:
                print(e)
                if handle_error:
                    handle_error(e)
                continue
        if is_pkg and recursive:
            submodules.append(mod)
        else:
            classes = classes.union(
                [
                    c[1]
                    for c in inspect.getmembers(mod, inspect.isclass)
                    if (
                        (is_target is None or is_target(c[1]))
                        and c[1].__module__ == mod.__name__
                    )
                ]
            )
    for m in submodules:
        classes = classes.union(
            find_classes(
                m, is_target=is_target, handle_error=handle_error, recursive=recursive
            )
        )
    return classes
