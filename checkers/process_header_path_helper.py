#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

"""
usage: process_header_path_helper.py [-h] [-pd PROCESS_DIR] [-epd EXCLUDE_PROCESS_DIR] [-sd SEARCH_DIR] [-fsd FIRST_SEARCH_PATH] [-mfs MATCH_FILE_SUFFIX] [-eh EXCLUDE_HEADER]

optional arguments:
  -h, --help            show this help message and exit
  -pd PROCESS_DIR, --process-dir PROCESS_DIR
                        The directory where the header path needs to be processed
  -epd EXCLUDE_PROCESS_DIR, --exclude-process-dir EXCLUDE_PROCESS_DIR
                        The directory where the header path doesn't need to be processed
  -sd SEARCH_DIR, --search-dir SEARCH_DIR
                        The directory to find the header
  -fsd FIRST_SEARCH_PATH, --first-search-path FIRST_SEARCH_PATH
                        The paths that prioritizes lookup headers
  -mfs MATCH_FILE_SUFFIX, --match-file-suffix MATCH_FILE_SUFFIX
                        The file suffixes that the header need to be processed
  -eh EXCLUDE_HEADER, --exclude-header EXCLUDE_HEADER
                        Headers that don't need to be processed
"""

import os
import sys
import re
import argparse
import subprocess
from config import Config

# Set the directory where the header path needs to be processed.
DEFAULT_NEED_PROCESSED_FILE_DIRS = Config.value(
    "checker-config", "header-path-checker", "processed-file-dirs"
)

# Set the directory where the header path doesn't need to be processed.
DEFAULT_EXCLUDE_PROCESSED_FILES = Config.value(
    "checker-config", "header-path-checker", "exclude-processed-file-dirs"
)
# Set the directory to find the header.
DEFAULT_HEADER_SEARCH_DIRS = Config.value(
    "checker-config", "header-path-checker", "header-search-paths"
)
# Set the prefix paths that can be omitted when including or importing header
# files in DEFAULT_NEED_PROCESSED_FILE_DIRS files.
HEADER_EXTEND_PREFIX_PATHS = Config.value(
    "checker-config", "header-path-checker", "header-extend-prefixes"
)
# Set the paths that prioritizes lookup headers.
DEFAULT_FIRST_SEARCH_PATHS = Config.value(
    "checker-config", "header-path-checker", "first-header-search-paths"
)
# Set the file suffixes that the header need to be processed.
DEFAULT_FILE_SUFFIX_MATCH = [".h", ".hpp", ".c", ".cc", ".cpp", ".m", ".mm"]
# Set headers or header paths that don't need to be processed.
DEFAULT_EXCLUDE_PROCESSED_HEADERS = Config.value(
    "checker-config", "header-path-checker", "ignore-header-files"
)
# The following directories are managed by LCM
HEADER_DIRS_MANAGED_BY_LCM = Config.value(
    "checker-config", "header-path-checker", "header-dirs-managed-by-habitat"
)
# Project root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def formatString(string_set):
    string_ret = ""
    for str in string_set:
        string_ret += "{}|".format(str)
    string_ret = string_ret[:-1]
    return string_ret


def isIncludeLine(include_str):
    match = re.match(r'^ *#(include) +["].*["]', include_str)
    if match:
        return True
    return False


def isInSpecifiedDir(file_relative_path, dirs):
    for dir in dirs:
        regex = r"^{}/".format(dir)
        if re.match(regex, file_relative_path):
            return True
    return False


def hasSubstring(str, substring_list):
    for substring in substring_list:
        if str.find(substring) != -1:
            return True
    return False


def findHeaderCandidatesByOsWalk(dirs):
    file_path_list = []
    for dir in dirs:
        for dirpath, dirname, files in os.walk(os.path.join(ROOT_DIR, dir)):
            file_paths = [
                os.path.join(dirpath, file).replace(ROOT_DIR + "/", "")
                for file in files
            ]
            file_path_list += file_paths
    return file_path_list


def findHeaderCandidatesByGit(dirs):
    if not dirs:
        return []
    search_dir = formatString(dirs)
    header_candidates = []
    cmd = "git ls-tree -r HEAD --name-only | grep -E '^({})/.*(.h|.hpp)$'".format(
        search_dir
    )
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        header_candidates = list(result.stdout.strip().split("\n"))
    except Exception as e:
        print("An error occurred:", e)
    return header_candidates


def findHeaderCandidates(dirs):
    get_header_by_oswalk = []
    get_header_by_git = []
    for dir in dirs:
        if isInSpecifiedDir(dir, HEADER_DIRS_MANAGED_BY_LCM):
            get_header_by_oswalk.append(dir)
        else:
            get_header_by_git.append(dir)
    return findHeaderCandidatesByOsWalk(
        get_header_by_oswalk
    ) + findHeaderCandidatesByGit(get_header_by_git)


def findAllFiles(dirs):
    if not dirs:
        return []
    search_dir = formatString(dirs)
    file_suffix = formatString(DEFAULT_FILE_SUFFIX_MATCH)
    file_candidates = []
    cmd = "git ls-tree -r HEAD --name-only | grep -E '^({})/.*({})$'".format(
        search_dir, file_suffix
    )
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        file_candidates = list(result.stdout.strip().split("\n"))
    except Exception as e:
        print("An error occurred:", e)
    return file_candidates


def findSearchHeaders():
    return findHeaderCandidates(DEFAULT_HEADER_SEARCH_DIRS + HEADER_DIRS_MANAGED_BY_LCM)


def closest_match(paths, target):
    if len(paths) == 1:
        return paths[0]

    prefixes = [os.path.commonprefix([p, target]) for p in paths]
    closest_prefix = max(prefixes, key=len)
    closest_path = min([p for p in paths if closest_prefix in p], key=len)
    return closest_path


def is_correct_path(old_path, full_path):
    prefix_path = full_path.partition(old_path)[0]
    is_correct = False
    for prefix_search_path in HEADER_EXTEND_PREFIX_PATHS:
        partitions = prefix_path.lower().partition(prefix_search_path.lower())
        if len(partitions[0]) == 0 and len(partitions[2].replace(os.sep, "")) == 0:
            is_correct = True
            break
    return is_correct


def replaceFullPath(
    file, include_str, search_headers, search_dir, exclude_processed_headers
):
    str_list = re.split(r'(["])', include_str)
    relative_path = str_list[2]
    path_candidates = []

    if isInSpecifiedDir(relative_path, search_dir):
        return include_str, path_candidates

    if hasSubstring(relative_path, exclude_processed_headers):
        return include_str, path_candidates

    for header in search_headers:
        if header.endswith(relative_path) and os.path.basename(
            relative_path
        ) == os.path.basename(header):
            path_candidates.append(header)
    if path_candidates:
        str_list[2] = closest_match(path_candidates, file)
        if not is_correct_path(relative_path, str_list[2]):
            return "".join(str_list), path_candidates
    return include_str, path_candidates


def processIncludeHeader(
    files,
    search_headers,
    search_dir,
    match_file_suffix,
    exclude_processed_headers,
    exclude_processed_file_dirs,
):
    for file in files:
        if hasSubstring(file, exclude_processed_file_dirs):
            continue
        file_suffix = os.path.splitext(file)[-1]
        if file_suffix not in match_file_suffix:
            continue

        lines = []
        with open(file, "r") as context:
            lines = context.readlines()
            for idx, line in enumerate(lines):
                if isIncludeLine(line):
                    lines[idx], _ = replaceFullPath(
                        file,
                        line,
                        search_headers,
                        search_dir,
                        exclude_processed_headers,
                    )
            context.close()
        with open(file, "w") as f:
            f.writelines(lines)
            f.close()


def shouldProcessIncludeHeader(file_name, search_headers):
    # print("checking {} include header path.".format(file_name))

    if not isInSpecifiedDir(file_name, DEFAULT_NEED_PROCESSED_FILE_DIRS):
        return False

    if hasSubstring(file_name, DEFAULT_EXCLUDE_PROCESSED_FILES):
        return False

    file = os.path.join(ROOT_DIR, file_name)
    file_suffix = os.path.splitext(file)[-1]
    if file_suffix not in DEFAULT_FILE_SUFFIX_MATCH:
        return False

    should_process = False
    with open(file, "r") as context:
        lines = context.readlines()
        for idx, line in enumerate(lines):
            if isIncludeLine(line):
                new_line, header_candidates = replaceFullPath(
                    file,
                    line,
                    search_headers,
                    DEFAULT_HEADER_SEARCH_DIRS,
                    DEFAULT_EXCLUDE_PROCESSED_HEADERS,
                )
                if header_candidates:
                    str_list = re.split(r'(["])', line)
                    row_num = int(idx + 1)
                    col_num = int(len(str_list[0]) + len(str_list[1]) + 1)
                    if line != new_line:
                        print(
                            "{}:{}:{} include header path is incomplete, please use full path. Maybe you'll use : ".format(
                                file_name, row_num, col_num
                            )
                        )
                        print("{}".format(header_candidates))
                        should_process = True
        context.close()
    return should_process


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-pd",
        "--process-dir",
        type=list,
        required=False,
        default=DEFAULT_NEED_PROCESSED_FILE_DIRS,
        help="The directory where the header path needs to be processed",
    )
    parser.add_argument(
        "-epd",
        "--exclude-process-dir",
        type=list,
        required=False,
        default=DEFAULT_EXCLUDE_PROCESSED_FILES,
        help="The directory where the header path doesn't need to be processed",
    )
    parser.add_argument(
        "-sd",
        "--search-dir",
        type=list,
        required=False,
        default=DEFAULT_HEADER_SEARCH_DIRS + HEADER_DIRS_MANAGED_BY_LCM,
        help="The directory to find the header",
    )
    parser.add_argument(
        "-fsd",
        "--first-search-path",
        type=list,
        required=False,
        default=DEFAULT_FIRST_SEARCH_PATHS,
        help="The paths that prioritizes lookup headers",
    )
    parser.add_argument(
        "-mfs",
        "--match-file-suffix",
        type=list,
        required=False,
        default=DEFAULT_FILE_SUFFIX_MATCH,
        help="The file suffixes that the header need to be processed",
    )
    parser.add_argument(
        "-eh",
        "--exclude-header",
        type=list,
        required=False,
        default=DEFAULT_EXCLUDE_PROCESSED_HEADERS,
        help="Headers that don't need to be processed",
    )
    args = parser.parse_args()

    search_dir = args.search_dir
    first_search_paths = args.first_search_path
    need_processed_file_dirs = args.process_dir
    exclude_processed_file_dirs = args.exclude_process_dir

    match_file_suffix = args.match_file_suffix
    exclude_processed_headers = args.exclude_header

    first_search_headers = findHeaderCandidates(first_search_paths)
    search_headers = findHeaderCandidates(search_dir)
    search_headers.sort()
    search_headers = first_search_headers + search_headers
    need_fix_files = findAllFiles(need_processed_file_dirs)

    processIncludeHeader(
        need_fix_files,
        search_headers,
        search_dir,
        match_file_suffix,
        exclude_processed_headers,
        exclude_processed_file_dirs,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
