#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import io
import os.path
import re
import tarfile
import urllib.request
import zipfile
from argparse import Namespace

from cocoapods.downloaders.downloader import Downloader


class FileType:
    TGZ = "tgz"
    TAR = "tar"
    TBZ = "tbz"
    TXZ = "txz"
    ZIP = "zip"
    DMG = "dmg"


def type_with_url(url):
    if re.findall(r"\.zip$", url):
        return FileType.ZIP
    elif re.findall(r"\.(tgz|tar\.gz)$", url):
        return FileType.TGZ
    elif re.findall(r"\.tar$", url):
        return FileType.TAR
    elif re.findall(r"\.(tbz|tar\.bz2)$", url):
        return FileType.TBZ
    elif re.findall(r"\.(txz|tar\.xz)$", url):
        return FileType.TXZ
    elif re.findall(r"\.dmg$", url):
        return FileType.DMG


def should_flatten(file_type):
    if file_type in [FileType.TGZ, FileType.TAR, FileType.TBZ, FileType.TXZ]:
        return True  # those archives flatten by default
    else:
        return False  # all others (actually only .zip) default not to flatten


def get_members(tar, strip):
    for member in tar.getmembers():
        member.path = member.path.split("/", strip)[-1]
        yield member


class HttpDownloader(Downloader):
    type = "http"
    timeout = 600

    @classmethod
    def download(
        cls,
        source: dict,
        root_dir: str,
        target_dir: str = None,
        name: str = None,
        options: Namespace = None,
        cache_dir: str = None,
    ):
        url = source["http"]
        req = urllib.request.Request(source["http"], method="GET")
        res = urllib.request.urlopen(req, timeout=cls.timeout)

        file_obj = io.BytesIO(res.read())
        target_dir = target_dir or root_dir
        file_type = type_with_url(url)
        if file_type == FileType.ZIP:
            compressed = zipfile.ZipFile(file=file_obj, mode="r")
            # compressed.extractall(target_dir)
        elif file_type in [FileType.TGZ, FileType.TXZ]:
            compressed = tarfile.open(fileobj=file_obj, mode="r")
            # compressed.extractall(target_dir)
        else:
            raise Exception(f"can not decompress file {url.split('/')[-1]}")

        if should_flatten(file_type) and os.path.commonprefix(compressed.getnames()):
            compressed.extractall(target_dir, members=get_members(compressed, 1))
        else:
            compressed.extractall(target_dir)

        return target_dir
