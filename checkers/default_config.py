# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.


checker_default_config = {
    "file-type-checker": {
        "binary-files-allow-list": [],
    },
    "coding-style-checker": {"ignore-suffixes": [], "ignore-dirs": []},
    "header-path-checker": {
        "processed-file-dirs": [],
        "exclude-processed-file-dirs": [],
        "ignore-header-files": [],
        "header-search-paths": [],
        "first-header-search-paths": [],
    },
    "api-checker": {
        "api-dirs": {
            "android": None,
            "ios": None,
            "ios-common": None,
        },
        "instruction-doc": None,
    },
}
