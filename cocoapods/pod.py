#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import hashlib
import json
import os
import shutil
import subprocess

from cocoapods.files_accessor import FilesAccessor
from cocoapods.precompiled_header import PrecompiledHeader
from cocoapods.sources import ExternalSource
from cocoapods.specification import Specification
from cocoapods.utils import get_downloaders, create_temp_dir


class SubSpec:

    def __init__(self, pod, name):
        self.pod = pod
        self.name = name
        self.deps = []

    def addDependencies(self, deps):
        self.deps += deps


class Pod:

    def __init__(self, name, version, source, cache_dir=None):
        self._pch_files = {}
        self.name = name
        self.version = version
        self.pod_name = None
        self.source = source
        if self.source:
            self.source.add_pod(self)
        self._target_dir = None
        self._local_source_dir = None
        self._cache_dir = cache_dir
        self._prepare_command = None
        self.sub_specs = {}
        self._spec = None

    def add_sub_spec(self, sub_spec):
        self.sub_specs[sub_spec.name] = sub_spec

    @property
    def local_source_dir(self):
        if self._local_source_dir is None:
            raise Exception(f"Pod {self.name} not been downloaded yet")
        return self._local_source_dir

    @property
    def target_dir(self):
        if self._target_dir is None:
            raise Exception(f"Pod {self.name} not been downloaded yet")
        return self._target_dir

    @property
    def path_prefix(self):
        metadata = self.source.metadata
        prefix_length = sum(metadata.get("prefix_lengths", [0]))
        pod_name_digest = hashlib.md5(self.name.encode()).hexdigest()
        return os.path.join(*pod_name_digest[0:prefix_length]) if prefix_length else ""

    @property
    def spec(self):
        if self._spec:
            return self._spec

        if self._cache_dir:
            spec_cache_path = os.path.join(
                self._cache_dir,
                "specs",
                self.name,
                self.version,
                f"{self.name}.podspec.json",
            )
            if not isinstance(self.source, ExternalSource) and os.path.exists(
                spec_cache_path
            ):
                with open(spec_cache_path, "r") as f:
                    try:
                        spec_content = json.load(f)
                        self._spec = Specification(self, None, spec_content)
                        return self._spec
                    except Exception as e:
                        print(e)
                        os.remove(spec_cache_path)

        spec_content = self.source.load_podspec(self.name)

        if self._cache_dir:
            os.makedirs(os.path.dirname(spec_cache_path), exist_ok=True)
            with open(spec_cache_path, "w") as f:
                json.dump(spec_content, f)

        self._spec = Specification(self, None, spec_content)
        return self._spec

    def generate_pch(self, platform):
        pch = PrecompiledHeader(platform)
        pch_path = os.path.join(
            self.target_dir, f'{self.name}-prefix{("-" + platform) or ""}.pch'
        )
        pch.save_to(pch_path)
        self._pch_files[platform] = pch_path
        return pch_path

    def download(self, target_dir, cache_dir=None, skip=False):
        self._target_dir = target_dir
        target_files = []
        if not skip:
            if os.path.islink(target_dir):
                os.unlink(target_dir)
            elif os.path.isdir(target_dir):
                shutil.rmtree(target_dir)

            if isinstance(self.source, ExternalSource):
                local_source_dir = self.source.url
            else:
                need_downloading = False
                if cache_dir:
                    local_source_dir = os.path.join(
                        cache_dir, "sources", self.name, self.version
                    )
                    if not os.path.exists(local_source_dir) or not os.listdir(
                        local_source_dir
                    ):
                        need_downloading = True
                else:
                    local_source_dir = create_temp_dir()
                    need_downloading = True

                if need_downloading:
                    for downloader in get_downloaders():
                        if not downloader.matched(self.spec):
                            continue
                        local_source_dir = downloader.download(
                            self.spec.source,
                            os.path.dirname(local_source_dir),
                            target_dir=local_source_dir,
                            name=self.name,
                            cache_dir=cache_dir,
                        )
                        break

                    prepare_command = getattr(self.spec, "prepare_command", "")
                    if prepare_command:
                        self._prepare_command = prepare_command
                        subprocess.check_call(
                            prepare_command, shell=True, cwd=local_source_dir
                        )

            files_accessor = FilesAccessor(local_source_dir, self.spec)
            all_files = files_accessor.get_all_files(full_path=True)
            for file in all_files:
                target_path = os.path.join(
                    target_dir, os.path.relpath(file, files_accessor.root_dir)
                )
                target_files.append(target_path)

                if os.path.exists(target_path):
                    continue

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                if cache_dir:
                    if os.path.isdir(file):
                        shutil.copytree(file, target_path)
                    else:
                        shutil.copy(file, target_path)
                else:
                    shutil.move(file, target_path)
            if not cache_dir:
                shutil.rmtree(local_source_dir)

            target_files.append(self.generate_pch("ios"))
            target_files.append(self.generate_pch("osx"))

        self._local_source_dir = target_dir
        return target_files

    def to_lcm_dep(self):
        if isinstance(self.source, ExternalSource):
            return None

        source = self.spec.source.copy()
        if "git" in source:
            dep_info = {"type": "git", "url": source.pop("git"), **source}
        elif "http" in source:
            dep_info = source
        else:
            raise Exception("unknown source")
        return dep_info

    def get_header_mappings(self, root_dir):
        mappings = []
        for spec in self.spec.all_specs():
            mappings += [
                (
                    os.path.relpath(mapping[0], root_dir),
                    os.path.relpath(mapping[1], root_dir),
                )
                for mapping in spec.header_mappings
            ]
        return mappings

    def get_pch_file(self, platform):
        return self._pch_files.get(platform, None)
