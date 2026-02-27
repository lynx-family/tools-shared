# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
from config import Config
import subprocess, sys, os

PRETTIER_VERSION = "2.2.1"
PRETTIER_FULL_NAME = f"prettier@{PRETTIER_VERSION}"


def check_and_install_prettier():
    """
    Check if the specified version of prettier exists locally, download it via npx if not (download only, no execution)
    """
    try:
        result = subprocess.run(
            ["npx", "--no-install", PRETTIER_FULL_NAME, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            return True

        print(
            f"\033[33mprettier@{PRETTIER_VERSION} not found locally, starting download...\033[0m"
        )
        download_result = subprocess.run(
            [
                "npx",
                "--quiet",
                "--yes",
                "--ignore-existing",
                PRETTIER_FULL_NAME,
                "--version",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if download_result.returncode != 0:
            print(
                f"\033[33mFailed to download prettier@{PRETTIER_VERSION}: {download_result.stderr}\033[0m",
                file=sys.stderr,
            )
            return False
        print(f"\033[33mprettier@{PRETTIER_VERSION} downloaded successfully\033[0m")
        return True
    except Exception as e:
        print(
            f"Exception occurred while checking/downloading prettier: {str(e)}",
            file=sys.stderr,
        )
        return False


def code_format_env_setup():
    # read configuration
    prefer_local_prettier = Config.get("prefer_local_prettier")
    if not prefer_local_prettier:
        check_and_install_prettier()
