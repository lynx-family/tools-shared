#!/usr/bin/env python
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os
import sys
import json
import argparse
import subprocess
from cocoapods.specification import Specification
from cocoapods.pod import Pod
import shutil

target_dir = "source_package"


def run_command(command, check=True):
    # When the "command" is a multi-line command, only the status of the last line of the command is checked.
    # Therefore, it is necessary to add "set -e" to ensure that any error in any line of the command will cause the script to exit immediately.
    command = "set -e\n" + command

    print(f"run command: {command}")
    res = subprocess.run(
        ["bash", "-c", command], stderr=subprocess.STDOUT, check=check, text=True
    )

def get_podspec_version(repo_name):
    with open(f"{repo_name}.podspec.json", "r") as f:
        content = json.load(f)
    return content["version"]

def get_source_files(repo_name):
    content = None
    with open(f"{repo_name}.podspec.json", "r") as f:
        content = json.load(f)

    if "prepare_command" in content and content["prepare_command"] != "":
        prepare_command = content["prepare_command"]
        run_command(prepare_command)

    # get the source file name by using the Specification
    pod = Pod(name="", version="", source=None)
    # only need use pod.target_dir
    pod._target_dir = ""

    spec = Specification(pod, None, content)
    files = spec._files_accessor.get_all_files()
    return files


def delete_useless_files(source_files, repo_name, source_dirs):
    """
    @source_files:  source files need to be preserved
    @repo_name: name of repository
    @source_dirs: additional dirs need to be preserved
    """
    print("run delete_useless_files")
    current_directory = os.getcwd()
    source_files = [
        os.path.join(current_directory, file_name) for file_name in source_files
    ]
    source_dirs_list = [
        os.path.join(current_directory, dir_item) for dir_item in source_dirs
    ]
    for root, dirnames, filenames in os.walk(current_directory):
        if root in source_dirs_list:
            continue
        for dirname in dirnames:
            if os.path.islink(os.path.join(root, dirname)):
                os.unlink(os.path.join(root, dirname))
        for file_name in filenames:
            file_name = os.path.join(root, file_name)
            if file_name not in source_files:
                base_name = os.path.basename(file_name)
                if base_name != f"{repo_name}.podspec.json" and base_name != "LICENSE":
                    os.remove(file_name)

    run_command("find . -type d -empty -delete")


def copy_to_target_folder(source_files, repo_name, source_dirs):
    """
    @source_files:  source files need to be preserved
    @repo_name: name of repository
    @source_dirs: additional dirs need to be preserved
    """
    run_command(f"rm -rf {target_dir}")
    run_command(f"mkdir {target_dir}")
    print("copy files to target directory")
    current_directory = os.getcwd()
    source_files = [
        os.path.join(current_directory, file_name) for file_name in source_files
    ]
    source_dirs_list = [
        os.path.join(current_directory, dir_item) for dir_item in source_dirs
    ]
    for root, dirnames, filenames in os.walk(current_directory):
        # exclude target file in os.walk
        dirnames[:] = [d for d in dirnames if d != target_dir]

        if root in source_dirs_list:
            relative_dir_path = os.path.relpath(root, current_directory)
            target_dir_path = os.path.join(target_dir, relative_dir_path)
            shutil.copytree(relative_dir_path, target_dir_path)

        for file_name in filenames:
            complete_file_name = os.path.join(root, file_name)
            if (
                complete_file_name in source_files
                or file_name == f"{repo_name}.podspec.json"
                or (file_name == "LICENSE" and root == current_directory)
            ):
                relative_path = os.path.relpath(complete_file_name, current_directory)
                target_path = os.path.join(target_dir, relative_path)

                # create the directory
                destination_dir = os.path.dirname(target_path)
                if not os.path.exists(destination_dir):
                    os.makedirs(destination_dir)
                shutil.copyfile(relative_path, os.path.join(target_dir, relative_path))
                continue


def replace_source_of_podspec(repo_name, tag, zip_name):
    with open(f"{repo_name}.podspec.json", "r") as f:
        content = json.load(f)
    if "prepare_command" in content:
        content.pop("prepare_command")
    source_code_repo = os.environ.get("GITHUB_REPOSITORY")
    target_source = {}
    target_source["http"] = (
        f"https://github.com/{source_code_repo}/releases/download/{tag}/{zip_name}"
    )
    content["source"] = target_source
    # update the podspec
    with open(f"{repo_name}.podspec.json", "w") as f:
        json.dump(content, f, indent=4)


def main():
    parser = argparse.ArgumentParser(description="Generate a iOS source code zip")
    parser.add_argument(
        "--output_type",
        choices=["zip", "podspec", "both"],
        default="both",
        help="The valid output of this script",
    )
    # no_json means that using the podspec file as the final file rather than podspec.json file
    parser.add_argument(
        "--no_json", action="store_true", help="Whether to generate podspec.json"
    )

    parser.add_argument(
        "--cache_path",
        type=str,
        default="./bundle",
        help="Set the ruby cache dir",
    )

    parser.add_argument("--repo", type=str, help="Replace the source of podspec")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Whether to delete files other than the source code package",
    )
    parser.add_argument("--tag", type=str, help="The release tag of component")
    parser.add_argument("--package_dir", type=str, help="The root dir of package")
    args = parser.parse_args()

    repo_name = args.repo
    source_dirs = ["build"]

    
    print("run generate_podspec")
    run_command(
        f"SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk bundle install --path {args.cache_path}"
    )
    run_command(
        f"bundle exec pod ipc spec {repo_name}.podspec > {repo_name}.podspec.json"
    )
    
    version = get_podspec_version(repo_name)
    zip_name = f"{repo_name}-{version}.zip"

    # step1: generate the zip file
    if args.output_type == "both" or args.output_type == "zip":
        source_files = get_source_files(repo_name)

        if args.delete:
            delete_useless_files(source_files, repo_name, source_dirs)
        else:
            copy_to_target_folder(source_files, repo_name, source_dirs)
        # get the zip package
        if not args.delete:
            if args.package_dir:
                # move all files under package_dir
                tmp_dir = "tmp_dir"
                run_command(f"mkdir {tmp_dir}")
                run_command(f"mv {target_dir}/* {tmp_dir}")
                # move hidden files
                run_command(f"mv {target_dir}/.* {tmp_dir}", check=False)

                run_command(f"mkdir {target_dir}/{args.package_dir}")
                run_command(f"mv {tmp_dir}/* {target_dir}/{args.package_dir}")
                run_command(
                    f"mv {tmp_dir}/.* {target_dir}/{args.package_dir}", check=False
                )
            run_command(f'cd {target_dir} && zip -r ../{zip_name} * -x "*.zip"')
        else:
            run_command(f'zip -r {zip_name} * -x "*.zip"')

    # step2: udapte the podspec file
    if args.output_type == "both" or args.output_type == "podspec":
        # replace the source of podspec
        print("start replacing source of podspec")
        replace_source_of_podspec(repo_name, args.tag, zip_name)
        if args.no_json:
            run_command(f"rm -rf {repo_name}.podspec.json")
    else:
        # delete all podspec files regardless of whether a JSON file is generated.
        run_command(f"rm -rf {repo_name}.podspec.json")
        run_command(f"rm -rf {repo_name}.podspec")


if __name__ == "__main__":
    sys.exit(main())
