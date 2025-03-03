#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import logging
import os
import re
import shutil
import subprocess
import sys
from argparse import Namespace

from cocoapods.downloaders.downloader import Downloader
from cocoapods.utils import (
    check_call,
    convert_git_url_to_http,
    create_temp_dir,
    get_full_commit_id,
    is_git_root,
)


class GitDownloader(Downloader):
    type = "git"

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
        if options is None:
            options = Namespace(raw=False, paths=None, no_history=None, force=False)

        url = source["git"]
        if source.get("git_auth"):
            url = convert_git_url_to_http(url, source["git_auth"])
        logging.info(
            f"Fetch git repository {url if logging.DEBUG else url} to {target_dir}"
        )

        target_dir = target_dir or os.path.join(
            root_dir, url.rsplit("/")[-1].split(".")[0]
        )

        new_init = False
        if not options.raw or not options.clean_fetch:
            source_dir = target_dir
        else:
            source_dir = create_temp_dir(
                root_dir=root_dir, name=f'GIT-FETCHER-{target_dir.replace("/", "_")}'
            )

        if not is_git_root(source_dir):
            cmd = f"git init {source_dir}"
            check_call(cmd, shell=True)
            cmd = "git config remote.origin.url " + url
            check_call(cmd, shell=True, cwd=source_dir)
            new_init = True
        elif options.force:
            if options.raw:
                # check and clean existing paths if user intends to
                if options.paths:
                    paths_to_fetch = options.paths
                else:
                    paths_to_fetch = [target_dir]

                for p in paths_to_fetch:
                    if os.path.exists(p) and (options.clean or options.force):
                        logging.warning(
                            f"remove existing target directory {target_dir}"
                        )
                        shutil.rmtree(p)
                    else:
                        raise Exception(
                            f'directory {target_dir} exist, try use "-f/--force" flag or remove it manually'
                        )
            else:
                cmd = "git clean -f" + "d" if options.clean else ""
                check_call(cmd, shell=True, cwd=source_dir)

        logging.debug(
            f"Fetch git repository {url if logging.DEBUG else url} in {source_dir}"
        )
        # fix reserved name in file path causing the checkout command complain "error: invalid path..." on windows
        if sys.platform == "win32":
            cmd = "git config core.protectNTFS false"
            check_call(cmd, shell=True, cwd=source_dir)

        # Enable sparse checkouts
        try:
            if options.paths:
                cmd = f'git sparse-checkout set {" ".join(options.paths)}'
                check_call(cmd, shell=True, cwd=source_dir)
            else:
                # Repopulate the working directory with all files, disabling sparse checkouts.
                cmd = "git sparse-checkout disable"
                check_call(cmd, shell=True, cwd=source_dir)
        except subprocess.CalledProcessError:
            # Since sparse checkout is not supported by old version of git, just give a warning here.
            logging.warning(f"sparse checkout is not supported, skip cmd {cmd}")

        remote = (
            subprocess.check_output("git remote", shell=True, cwd=source_dir)
            .decode("utf-8")
            .strip()
        )
        if not remote:
            raise Exception("remote repository not exist")

        if "commit" in source:
            ref_spec = (
                source["commit"]
                if len(source["commit"]) == 40
                else get_full_commit_id(source["commit"], url)
            )
            checkout_args = "FETCH_HEAD"
        elif "tag" in source:
            ref_spec = source["tag"]
            checkout_args = "FETCH_HEAD"
        elif "branch" in source:
            branch = source["branch"]
            ref_spec = f"{branch}:refs/remotes/{remote}/{branch}"
            checkout_args = f"-B {branch} refs/remotes/{remote}/{branch}"
        elif new_init:
            remote = "origin"
            cmd = f"git remote show {remote}"
            output = subprocess.check_output(cmd, shell=True, cwd=source_dir).decode(
                "utf-8"
            )
            res = re.search(r"HEAD branch: (\S+)", output)
            if not res:
                raise Exception(f"HEAD branch of remote repository {remote} not found")
            branch_name = res[1]
            ref_spec = f"{branch_name}:refs/remotes/{remote}/{branch_name}"
            checkout_args = f"-B {branch_name} refs/remotes/{remote}/{branch_name}"
        else:
            cmd = "git status -uno"
            output = subprocess.check_output(cmd, shell=True, cwd=target_dir).decode(
                "utf-8"
            )
            if output.startswith("HEAD detached at"):
                # HEAD is detached, do nothing
                return
            elif output.startswith("On branch"):
                branch_name = output.split()[2]
            else:
                raise Exception(output)
            ref_spec = f"{branch_name}:refs/remotes/{remote}/{branch_name}"
            checkout_args = f"-B {branch_name} refs/remotes/{remote}/{branch_name}"

        depth_arg = "--depth=1 --no-tags" if options.no_history else ""
        cmd = f"git fetch {depth_arg} --force --progress --update-head-ok -- {url} {ref_spec}"
        check_call(cmd, shell=True, cwd=source_dir)

        if options.raw and not os.path.exists(target_dir):
            os.mkdir(target_dir)
        if options.raw:
            if not os.path.exists(target_dir):
                os.mkdir(target_dir)
            cmd = f"git --work-tree={target_dir} checkout FETCH_HEAD -- ."
        else:
            cmd = f"git checkout {checkout_args}"
        check_call(cmd, shell=True, cwd=source_dir)

        if target_dir != source_dir and not options.raw:
            shutil.move(source_dir, target_dir)
        elif target_dir != source_dir:
            shutil.rmtree(source_dir, ignore_errors=True)

        return target_dir
