#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os
import re
from pathlib import Path

from cocoapods.utils import get_files_in_dir

HEADER_FILES_EXTENSIONS = (
    "h",
    "hh",
    "hpp",
    "ipp",
    "tpp",
    "hxx",
    "def",
    "inl",
    "inc",
    "s",
    "S",
)
SOURCE_FILE_EXTENSIONS = (
    "m",
    "mm",
    "i",
    "c",
    "cc",
    "cxx",
    "cpp",
    "c++",
    "swift",
) + HEADER_FILES_EXTENSIONS

GLOB_PATTERNS = {
    "readme": "readme{*,.*}",
    "license": "licen{c,s}e{*,.*}",
    "source_files": f'*{",".join(SOURCE_FILE_EXTENSIONS)}',
    "public_header_files": f'*{",".join(HEADER_FILES_EXTENSIONS)}',
    "podspecs": "*.{podspec,podspec.json}",
    "docs": "doc{s}{*,.*}/**/*",
}


def expand_matches(s, matches, result):
    if not matches:
        result.append(s)
        return
    for v in matches[0].split(","):
        s_new = s.replace("{" + matches[0] + "}", v)
        expand_matches(s_new, matches[1:], result)


class FilesAccessor:

    def __init__(self, root_dir, spec):
        self._source_files_cache = {}
        self._headers_cache = {}
        self._public_headers_cache = {}
        self.root_dir = root_dir
        self.spec = spec

    def clean_cache(self):
        self._source_files_cache.clear()
        self._headers_cache.clear()
        self._public_headers_cache.clear()

    def glob_files(self, pattern, include_dirs=False):
        if not pattern:
            return []
        if not isinstance(pattern, str):
            raise Exception(f"a string is required not {pattern}")
        matches = re.findall(r"\{(.*?)}", pattern)

        if matches:
            paths = []
            expand_matches(pattern, matches, paths)
        else:
            if pattern.endswith(".h**"):
                pattern = pattern[:-2]
            paths = [pattern]
        files = []
        for path in paths:
            try:
                full_path = os.path.join(self.root_dir, path)
                if os.path.isdir(full_path):
                    files += get_files_in_dir(full_path)
                    continue
                for f in Path(self.root_dir).glob(path):
                    files.append(f)
            except Exception as e:
                raise Exception(
                    f"got an exception when globbing files from {self.root_dir} with pattern {path} "
                    f"for spec {self.spec.get_full_name()}"
                ) from e
        return [str(f) for f in files if include_dirs or os.path.isfile(f)]

    def get_all_files(self, full_path=True):
        files = []
        for platform in [None, "ios", "osx"]:
            files += self.get_vendored_frameworks(platform)
            files += self.get_vendored_libraries(platform)
            files += self.get_resource_bundle_files(platform)
            if not platform:
                files += self.get_license_files()
                files += self.get_readme_files()
            files += self.get_prefix_headers(platform)
            files += self.glob_files_for_attr(
                "preserve_paths", platform, include_dirs=True
            )
            files += self.get_source_files(platform)
            files += self.get_resources(platform)
            files += self.get_modulemap(platform)

        for subspec in self.spec.subspecs:
            accessor = FilesAccessor(self.root_dir, subspec)
            files += accessor.get_all_files()

        if full_path:
            return [os.path.join(self.root_dir, file) for file in files]
        return files

    def get_libraries(self, platform, rebase=None):
        attrs = (
            getattr(self.spec, platform, None) if platform else self.spec.get_attrs()
        )
        return attrs.get("libraries", None) or []

    def get_vendored_frameworks(self, platform, rebase=None):
        return self.glob_files_for_attr(
            "vendored_frameworks",
            platform,
            include_dirs=True,
            rebase=rebase,
            keep_dirs=True,
        )

    def get_vendored_libraries(self, platform, rebase=None):
        return self.glob_files_for_attr(
            "vendored_libraries", platform, include_dirs=False, rebase=rebase
        )

    def get_resources(self, platform, rebase=None):
        return self.glob_files_for_attr(
            "resources", platform, include_dirs=True, rebase=rebase, keep_dirs=True
        )

    def get_modulemap(self, platform, rebase=None):
        return self.glob_files_for_attr(
            "module_map", platform, include_dirs=True, rebase=rebase, keep_dirs=True
        )

    def get_prefix_headers(self, platform):
        attrs = (
            getattr(self.spec, platform, None) if platform else self.spec.get_attrs()
        )
        if attrs is None:
            return []
        prefix_header = attrs.get("prefix_header", "")
        if prefix_header:
            return [prefix_header]
        return []

    def get_license_files(self):
        return self.glob_files(GLOB_PATTERNS["license"])

    def get_readme_files(self):
        return self.glob_files(GLOB_PATTERNS["readme"])

    def get_resource_bundle_files(self, platform):
        attrs = (
            getattr(self.spec, platform, None) if platform else self.spec.get_attrs()
        )
        if attrs is None:
            return []
        resource_bundles = attrs.get("resource_bundles", {})
        if resource_bundles:
            return self.glob_files_with_patterns(
                [
                    f
                    for values in resource_bundles.values()
                    for f in (values if isinstance(values, list) else [values])
                ]
            )
        return []

    def get_source_files(self, platform, rebase=None):
        if platform not in self._source_files_cache:
            self._source_files_cache[platform] = [
                file
                for file in self.glob_files_for_attr(
                    "source_files", platform, rebase=rebase
                )
                if str(file).split(".")[-1] in SOURCE_FILE_EXTENSIONS
            ]
        return self._source_files_cache[platform]

    def get_headers(self, platform, rebase=None):
        if platform not in self._headers_cache:
            source_files = self.get_source_files(platform, rebase=rebase)
            self._headers_cache[platform] = [
                file
                for file in source_files
                if file.split(".")[-1] in HEADER_FILES_EXTENSIONS
            ]
        return self._headers_cache[platform]

    def get_public_headers(self, platform, rebase=None):
        if platform not in self._public_headers_cache:
            public_headers = [
                file
                for file in self.glob_files_for_attr(
                    "public_header_files", platform, rebase=rebase
                )
                if file.split(".")[-1] in HEADER_FILES_EXTENSIONS
            ]
            if not public_headers:
                header_files = self.get_headers(platform, rebase=rebase)
            else:
                header_files = public_headers
            private_headers = [
                file
                for file in self.glob_files_for_attr(
                    "private_header_files", platform, rebase=rebase
                )
                if file.split(".")[-1] in HEADER_FILES_EXTENSIONS
            ]
            self._public_headers_cache[platform] = [
                file for file in header_files if file not in private_headers
            ]
        return self._public_headers_cache[platform]

    def glob_files_with_patterns(
        self,
        file_patterns,
        include_dirs=False,
        exclude_patterns=None,
        rebase=None,
        keep_dirs=False,
    ):
        file_patterns = (
            file_patterns if isinstance(file_patterns, list) else [file_patterns]
        )
        exclude_patterns = (
            exclude_patterns
            if isinstance(exclude_patterns, list)
            else [exclude_patterns]
        )
        # source_dir = self.pod.local_source_dir
        file_list = []
        for pattern in file_patterns:
            if not pattern:
                continue
            # if os.path.isdir(os.path.join(source_dir, pattern)):
            #     file_list += get_files_in_dir(os.path.join(source_dir, pattern))
            #     continue
            #
            # file_list += glob_files(source_dir, pattern)
            if keep_dirs and os.path.isdir(os.path.join(self.root_dir, pattern)):
                file_list.append(os.path.join(self.root_dir, pattern))
            else:
                file_list += self.glob_files(pattern, include_dirs=include_dirs)
        exclude_files = []
        for pattern in exclude_patterns:
            exclude_files += self.glob_files(pattern, include_dirs=include_dirs)
        # return [self.to_path_from_root(file) for file in file_list]
        return [
            os.path.relpath(file, rebase or self.root_dir)
            for file in file_list
            if file not in exclude_files
        ]

    def glob_files_for_attr(
        self, attr, platform, include_dirs=False, rebase=None, keep_dirs=False
    ):
        attrs = (
            getattr(self.spec, platform, None) if platform else self.spec.get_attrs()
        )
        if attrs is None:
            return []
        return self.glob_files_with_patterns(
            attrs.get(attr, []),
            include_dirs=include_dirs,
            exclude_patterns=attrs.get("exclude_files", []),
            rebase=rebase,
            keep_dirs=keep_dirs,
        )
