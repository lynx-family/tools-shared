#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

from argparse import Namespace

from cocoapods.downloaders.downloader import Downloader
from cocoapods.sources import ExternalSource


class ExternalDownloader(Downloader):
    type = None

    @classmethod
    def matched(cls, source):
        return isinstance(source, ExternalSource)

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
        pass
