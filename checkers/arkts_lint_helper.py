# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os
import subprocess
import json
import platform
from default_env import Env


def run_ets_lint(options, changed_files):
    print("Run arkts lint in helper")

    # filter changed files
    changed_files = [
        file
        for file in changed_files
        if file.endswith(".ets") or (file.endswith(".ts") and "harmony" in file)
    ]
    print("changed_files related with arkts : {}".format(changed_files))

    if len(changed_files) == 0:
        print("No changed files related with arkts, skip arkts lint")
        return True

    project_root_path = Env.SELF_PARENT_PATH
    harmony_path = os.path.abspath(os.path.join(project_root_path, "harmony"))
    config_file_path = os.path.join(harmony_path, "code-linter.json")
    codelinter_path = os.path.join(
        project_root_path, "buildtools", "harmony", "codelinter", "bin", "codelinter"
    )
    if platform.system().lower() == "window":
        codelinter_path += ".bat"

    # if not hab sync (codelinter is not exist) or not source with harmony(not working with harmony), skip
    # check DEVECO_SDK_HOME but not HARMONY_HOME as the later one maybe setup by every harmony developer but the former one is only be set after source envsetup
    is_source_with_harmony = "DEVECO_SDK_HOME" in os.environ
    if not os.path.exists(codelinter_path) or not is_source_with_harmony:
        print("codelinter not found or not sourced with harmony, skip arkts lint")
        return True

    local_properties_path = os.path.join(harmony_path, "local.properties")
    if not os.path.exists(local_properties_path):
        print("harmony/local.properties not found")
        if "HARMONY_HOME" in os.environ:
            # write hwsdk.dir to local.properties
            harmony_sdk_path = os.environ["HARMONY_HOME"]
            print(
                "harmony/local.properties not found, write hwsdk.dir with {} to it".format(
                    harmony_sdk_path
                )
            )
            with open(local_properties_path, "w") as f:
                f.write("hwsdk.dir={}".format(harmony_sdk_path))
        else:
            print("harmony/local.properties not found, skip arkts lint")
            return True

    cmd = 'bash -c "{codelinter_path} {root_path} --format json --config {config_file}"'.format(
        codelinter_path=codelinter_path,
        root_path=harmony_path,
        config_file=config_file_path,
    )
    if options.verbose:
        print("run command {}".format(cmd))
    ret_value, output = subprocess.getstatusoutput(cmd)
    if options.verbose:
        print("ret_value: {}".format(ret_value))
        print("------- origin output")
        print(output)

    if ret_value != 0:
        print("Failed to execute CodeLinter. Now showing the log file from CodeLinter.")
        print("------------------------------")
        # print buildtools/harmony/codelinter/result/codelinter.log for more details
        with open(
            os.path.join(
                project_root_path,
                "buildtools",
                "harmony",
                "codelinter",
                "result",
                "codelinter.log",
            ),
            "r",
        ) as f:
            print(f.read())
        return False

    prefix_str = "CodeLinter found some defects in your code."
    index = output.index(prefix_str)
    output = output[
        index + len(prefix_str) + 5 :
    ]  # remove suffix color pattern & newline
    if options.verbose:
        print("----- remove prefix")
        print(output)

    parsed_output = json.loads(output)
    found_issue_count = len(parsed_output)
    if found_issue_count:
        print("Found {} files have issues in arkts lint".format(found_issue_count))
        print(json.dumps(parsed_output, indent=4))
        print(
            "You can try run {codelinter_path} {root_path} --fix --config {config_file} to auto fix issues.".format(
                codelinter_path=codelinter_path,
                root_path=harmony_path,
                config_file=config_file_path,
            )
        )
        return False
    else:
        return True
