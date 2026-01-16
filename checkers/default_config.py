# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.


checker_default_config = {
    "default-disable-checkers": [],
    "file-type-checker": {
        "binary-files-allow-list": [],
    },
    "coding-style-checker": {"ignore-suffixes": [], "ignore-dirs": []},
    "cpplint-checker": {"ignore-suffixes": [], "ignore-dirs": [], "sub-git-dirs": []},
    "header-path-checker": {
        "processed-file-dirs": [],
        "exclude-processed-file-dirs": [],
        "ignore-header-files": [],
        "header-search-paths": [],
        "header-extend-prefixes": [],
        "first-header-search-paths": [],
        "header-dirs-managed-by-habitat": [],
        "ignore-suffixes": [],
        "ignore-dirs": [],
    },
    "api-checker": {
        "api-check-bin": "api-checker/main.py",
        "java-path": [],
        "cpp-path": [],
        "check-file-suffixes": [],
        "check-file-subpaths": [],
        "instruction-doc": None,
    },
    "gn-relative-path-checker": {"skip-prefixes": ["//out/"]},
    "deps-checker": {
        "ignore-dirs": [],
        "gn-targets": [],
        "gn-args": "",
    },
}

command_default_config = {
    "format-command": {"ignore-suffixes": [], "ignore-dirs": []},
}

ai_commit_request_url = None

external_checker_path = None
