#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import io
import json
import os.path
import subprocess
import tarfile
import tempfile
import random
import string

from abc import ABC
import requests

import yaml


COCOAPODS_VERSION_FILE_PATH = "CocoaPods-version.yml"
COCOAPODS_GIT_SOURCE_DEFAULT_BRANCH = "master"
TRUNK_REPO_URL = "https://github.com/CocoaPods/Specs.git"


def random_string(size=8, chars=string.ascii_letters + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def convert_podspec_to_json(spec):
    temp_spec_path = os.path.join(tempfile.gettempdir(), random_string() + ".podspec")
    with open(temp_spec_path, "w") as f:
        f.write(spec)

    spec = convert_podspec_file_to_json(temp_spec_path)
    os.remove(temp_spec_path)
    return spec


def convert_podspec_file_to_json(spec_file):
    cmd = ["pod", "ipc", "--silent", "spec", spec_file]
    output = subprocess.check_output(cmd)
    return output.decode()


class Source(ABC):

    def __init__(self):
        self.pods = {}
        self.url = None

    def add_pod(self, pod):
        self.pods[pod.name] = pod

    @property
    def metadata(self):
        return None

    def load_podspec(self, pod_name):
        raise NotImplementedError


class ExternalSource(Source):

    def __init__(self, url: str = None):
        super().__init__()
        self.url = url

    def load_podspec(self, pod_name):
        podspec_path = os.path.join(self.url, f"{pod_name}.podspec")
        if os.path.exists(podspec_path):
            spec = convert_podspec_file_to_json(spec_file=podspec_path)
            return json.loads(spec)
        else:
            with open(f"{podspec_path}.json", "r") as f:
                return json.load(f)


class GitSource(Source):

    def __init__(
        self,
        url=TRUNK_REPO_URL,
        branch=COCOAPODS_GIT_SOURCE_DEFAULT_BRANCH,
        specs_dir="Specs",
    ):
        super().__init__()
        self.url = url
        self.branch = branch
        self.specs_dir = specs_dir
        self._metadata = None

    def _get_metadata(self):
        cmd = [
            "git",
            "archive",
            f"--remote={self.url}",
            self.branch,
            COCOAPODS_VERSION_FILE_PATH,
        ]

        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            return yaml.load(output, Loader=yaml.FullLoader)
        except subprocess.CalledProcessError:
            return {}

    @property
    def metadata(self):
        if self._metadata is None:
            self._metadata = self._get_metadata()
        return self._metadata

    def _get_podspec_file(self, pod_name, file_type):
        pod = self.pods.get(pod_name)
        podspec_file_path = "/".join(
            [
                p
                for p in (
                    self.specs_dir,
                    pod.path_prefix,
                    pod_name,
                    pod.version,
                    f"{pod_name}.{file_type}",
                )
                if p
            ]
        )
        cmd = ["git", "archive", f"--remote={self.url}", self.branch, podspec_file_path]

        output = subprocess.check_output(cmd)
        tar = tarfile.open(fileobj=io.BytesIO(output), mode="r")
        tar.getmember(podspec_file_path)
        return tar.extractfile(podspec_file_path).read().decode()

    def load_podspec(self, pod_name):
        try:
            content = self._get_podspec_file(pod_name, "podspec.json")
        except subprocess.CalledProcessError:
            try:
                content = self._get_podspec_file(pod_name, "podspec")
                content = convert_podspec_to_json(content)
            except subprocess.CalledProcessError as e:
                raise Exception(f"podspec file of pod {pod_name} not found") from e
        print(content)
        podspec = json.loads(content)

        return podspec
