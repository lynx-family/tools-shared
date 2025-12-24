# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import inspect
import pkgutil
import sys
import importlib
import os
import importlib.util


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
                if hasattr(info, "find_spec"):
                    spec = info.find_spec(full_name)
                else:
                    loader = info.find_module(full_name)
                    if hasattr(loader, "create_module"):
                        spec = importlib.machinery.ModuleSpec(full_name, loader)
                    else:
                        spec = None

                if spec:
                    mod = importlib.util.module_from_spec(spec)

                    mod.__dict__["sys"] = sys
                    mod.__dict__["os"] = os
                    mod.__dict__["importlib"] = importlib

                    sys.modules[full_name] = mod

                    spec.loader.exec_module(mod)
                else:
                    if hasattr(info, "find_module"):
                        loader = info.find_module(full_name)
                        mod = loader.load_module(full_name)
                    else:
                        print(f"Cannot find module {full_name}")
                        continue

            except AttributeError as ae:
                print(f"AttributeError loading {full_name}: {ae}")
                if handle_error:
                    handle_error(ae)
                continue
            except Exception as e:
                print(f"Error loading {full_name}: {e}")
                if handle_error:
                    handle_error(e)
                continue

        if is_pkg and recursive:
            submodules.append(mod)
        else:
            try:
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
            except Exception as e:
                print(f"Error inspecting {full_name}: {e}")
                if handle_error:
                    handle_error(e)
                continue

    for m in submodules:
        try:
            classes = classes.union(
                find_classes(
                    m,
                    is_target=is_target,
                    handle_error=handle_error,
                    recursive=recursive,
                )
            )
        except Exception as e:
            print(f"Error processing submodule {m.__name__}: {e}")
            if handle_error:
                handle_error(e)

    return classes
