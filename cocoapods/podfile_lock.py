#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os.path
import re

import yaml

from cocoapods.pod import Pod, SubSpec
from cocoapods.sources import ExternalSource, GitSource

NAME_VERSION_PATTERN = r"(\S+) \((.*)\)"


def create_source(repo):
    if isinstance(repo, dict) and ":path" in repo:
        return ExternalSource(repo[":path"])
    elif isinstance(repo, str) and repo == "trunk":
        return GitSource()
    elif isinstance(repo, str) and repo.startswith("file://"):
        return GitSource(repo, specs_dir="")
    else:
        raise NotImplementedError


class PodfileLock:

    def __init__(self, file_path, cache_dir=None):
        self.pods = {}
        self.contents = None
        self.sources = []
        self.file_path = file_path
        self.spec_names = []
        self.cache_dir = cache_dir

        with open(file_path, "r") as f:
            content = yaml.load(f, Loader=yaml.FullLoader)
            self.contents = content

        for item in content.get("PODS", []):
            name, version = re.match(
                NAME_VERSION_PATTERN,
                (list(item)[0] if isinstance(item, dict) else item),
            ).groups()
            self.spec_names.append(name)

            name_parts = name.split("/", maxsplit=1)
            pod = self.pods.setdefault(
                name_parts[0], Pod(name_parts[0], version, None, cache_dir=cache_dir)
            )

            if version != pod.version:
                raise Exception(
                    f"version conflicts: existing: {pod.version} new: {version}"
                )

            if len(name_parts) > 1:
                pod.add_sub_spec(SubSpec(pod, name_parts[1]))

        for repo, pod_names in content.get("SPEC REPOS", {}).items():
            source = create_source(repo)
            for pod_name in pod_names:
                pod: Pod = self.pods.get(pod_name)
                pod.source = source
                source.add_pod(pod)
            self.sources.append(source)

        for pod_name, external_source in content.get("EXTERNAL SOURCES", {}).items():
            source_root_dir = os.path.join(
                os.path.dirname(self.file_path), external_source[":path"]
            )
            source = create_source({":path": source_root_dir})
            pod: Pod = self.pods.get(pod_name)
            pod.source = source
            source.add_pod(pod)
            self.sources.append(source)

    @classmethod
    def load_from_file(cls, path, cache_dir=None):
        if not os.path.exists(path):
            raise Exception(f"file {path} not exist")
        return cls(path, cache_dir=cache_dir)
