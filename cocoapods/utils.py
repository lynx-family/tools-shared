#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import logging
import os
import re
import sys
import string
import subprocess
from pathlib import Path
import random
import inspect
import pkgutil

from cocoapods import downloaders
from cocoapods.downloaders.downloader import Downloader

CACHE_DIR_PREFIX = "TEMP-"


def find_classes(module, is_target=None, handle_error=None, recursive=True):
    classes = set()
    submodules = []
    if not inspect.ismodule(module):
        return classes
    for info, name, is_pkg in pkgutil.iter_modules(module.__path__):
        full_name = module.__name__ + "." + name
        mod = sys.modules.get(full_name)
        if not mod:
            try:
                mod = info.find_module(full_name).load_module(full_name)
            except Exception as e:
                logging.debug(str(e))
                if handle_error:
                    handle_error(e)
                else:
                    raise e
                continue
        if is_pkg and recursive:
            submodules.append(mod)
        else:
            classes = classes.union(
                [
                    c[1]
                    for c in inspect.getmembers(mod, inspect.isclass)
                    if (
                        (is_target is None or is_target(c[1]))
                        and c[1].__module__ == mod.__name__
                    )
                ]
            )
    for m in submodules:
        classes = classes.union(
            find_classes(
                m, is_target=is_target, handle_error=handle_error, recursive=recursive
            )
        )
    return classes


def get_downloaders() -> list[Downloader]:
    classes = find_classes(downloaders, lambda cls: issubclass(cls, Downloader))
    if not classes:
        raise Exception("can not any downloaders")
    return classes


def random_string(size=8, chars=string.ascii_letters + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def is_git_repo(path):
    if not os.path.exists(path):
        return False
    cmd = f"git -C {path} rev-parse"
    try:
        check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
        return False
    else:
        return True


def git_root_dir(path=None):
    command = ["git", "rev-parse", "--show-toplevel"]
    p = subprocess.Popen(
        " ".join(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=path,
    )
    result, error = p.communicate()
    if error:
        raise Exception(
            "Error, can not get git root in path %s, "
            "make sure it is a git repo: %s" % (error.decode("utf-8"), path)
        )
    return Path(result.decode("utf-8").strip())


def is_git_root(path):
    if not is_git_repo(path):
        return False

    return Path(git_root_dir(path)) == Path(path)


def get_full_commit_id(shot_id, url):
    cmd = ["git", "ls-remote", url]
    output = subprocess.check_output(cmd)
    for line in output.decode().splitlines():
        if line.startswith(shot_id):
            return line.split()[0].strip()
    raise Exception(f"commit id {shot_id} not found on remote")


def check_call(*args, **kwargs):
    logging.debug(f"Run command: {args[0]} (args: {args} kwargs: {kwargs}")
    subprocess.check_call(*args, **kwargs)


def convert_git_url_to_http(url, auth=None):
    if url.startswith("git@"):
        url = "/".join(url.rsplit(":", 1))
    url = url.replace("git@", "https://")
    if auth:
        url = url.replace("://", f"://{auth}@")
    return url


def create_temp_dir(root_dir=os.getcwd(), name=None):
    cache_dir = os.path.join(
        root_dir, f'{CACHE_DIR_PREFIX}{name + "-" if name else ""}{random_string()}'
    )
    os.mkdir(cache_dir)
    return cache_dir


def glob_files(root_dir, pattern):
    matches = re.match(r"(.*)\.\{(.*)}", pattern)
    if matches:
        files = []
        for suffix in matches.group(2).split(","):
            file_path = f"{matches.group(1)}.{suffix}"
            files += [f for f in Path(root_dir).glob(file_path)]
    else:
        if pattern.endswith(".h**"):
            pattern = pattern[:-2]
        files = [f for f in Path(root_dir).glob(pattern)]
    return [f for f in files if os.path.isfile(f)]


def find_file(name, target_dir):
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file == name:
                return os.path.join(root, file)
    return None


def parse_shell_style_vars(line):

    def escape_quotes(s):
        if s.startswith('"') and s.endswith('"'):
            table = str.maketrans({"'": r"\'"})
        elif s.startswith("'") and s.endswith("'"):
            table = str.maketrans({'"': r"\""})
        else:
            return s
        return s.translate(table)

    state = 0  # 0-idle 1-parse key 2-parse value start 3-parse value
    kvs = {}
    k = ""
    v = ""
    quote = False
    finish = False
    for c in line:
        if state == 0:
            if c == " ":
                continue
            k += c
            state = 1
        elif state == 1:
            if c == "=":
                state = 2
            elif c == " ":
                finish = True
            else:
                k += c
        elif state == 2:
            if c == '"':
                quote = True
            else:
                v += c
            state = 3
        elif state == 3:
            if (not quote and c == " ") or (quote and c == '"'):
                finish = True
            else:
                v += c

        if not finish:
            continue

        finish = False
        v = escape_quotes(v)
        kvs[k] = v
        state = 0
        quote = False
        k = ""
        v = ""
    if k:
        v = escape_quotes(v)
        kvs[k] = v

    return kvs


def escape(s):
    table = str.maketrans({'"': '\\"', "\\": "\\\\"})
    return s.translate(table)


def expandvars(s):
    return os.path.expandvars(s.replace("(", "{").replace(")", "}")).replace('"', "")


def get_files_in_dir(dir_):
    file_list = []
    for root, dirs, files in os.walk(dir_):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list
