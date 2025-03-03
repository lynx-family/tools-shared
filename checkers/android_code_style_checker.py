# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import os.path
import re
import subprocess
import sys
from checkers.checker import Checker, CheckResult
from env import Env

DEFAULT_XML_CONTENT = """<?xml version="1.0"?>
<!-- 
  Copyright 2024 The Lynx Authors. All rights reserved.
  Licensed under the Apache License Version 2.0 that can be found in the
  LICENSE file in the root directory of this source tree.
-->
<!DOCTYPE module PUBLIC
          "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN"
          "https://checkstyle.org/dtds/configuration_1_3.dtd">
<module name="Checker">
  <module name="TreeWalker">
    <module name="UnusedImports"/>
  </module>
</module>
"""


class AndroidCodeStyleChecker(Checker):
    name = "android-check-style"
    help = "java and kotlin code style check"

    CHECK_STYLE_XML = "check_style.xml"
    TOOL_PATH = f"{Env.BUILD_TOOLS_PATH}/checkstyle/checkstyle.jar"

    def run_check_style(self, file):
        cmd = f"java -jar {self.TOOL_PATH} -c {self.CHECK_STYLE_XML} {file}"
        print(cmd)
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
            return (True, output.decode("utf-8"))
        except Exception as e:
            return (False, e.output.decode("utf-8"))

    def check_resourece(self):
        if not os.path.exists(self.TOOL_PATH):
            return False, f"checkstyle.jar not found!"
        if not os.path.exists(self.CHECK_STYLE_XML):
            print("check_style.yml not found in root path, will auto generate!")
            with open(self.CHECK_STYLE_XML, "w") as f:
                f.write(DEFAULT_XML_CONTENT)
        return True, None

    def get_changed_lines_of_target_file(self, file, line_indexes):
        result = []
        for key in line_indexes.keys():
            file_hash_code, changed_line = line_indexes[key]
            file_name = self.get_file_name(file_hash_code)
            if file == file_name:
                result.append(changed_line)
        return result

    def get_error_line_of_target_file(self, error_message):
        if error_message is None:
            return {"line": -1, "reason": None}
        pattern = r"\[ERROR\] .+:(\d+):\d+: (.+)"
        match = re.search(pattern, error_message)

        if match:
            return {"line": int(match.group(1)), "reason": error_message}
        else:
            return {"line": -1, "reason": None}

    def check_changed_lines(self, options, lines, line_indexes, changed_files):
        success, msg = self.check_resourece()
        if not success:
            print(msg)
            return CheckResult.FAILED
        changed_java_files = [f for f in changed_files if f.endswith(".java")]
        errors = []
        for changed_java_file in changed_java_files:
            print(f"checking {changed_java_file}")
            success, output = self.run_check_style(changed_java_file)
            if not success:
                changed_lines = self.get_changed_lines_of_target_file(
                    changed_java_file, line_indexes
                )
                error_messages = output.splitlines()
                for error_message in error_messages:
                    match_result = self.get_error_line_of_target_file(error_message)
                    if (
                        match_result["line"] != -1
                        and match_result["line"] in changed_lines
                    ):
                        errors.append(match_result["reason"])
        if len(errors) != 0:
            print("android-check-style failed:")
            for error in errors:
                print(error)
            return CheckResult.FAILED
        else:
            return CheckResult.PASSED

    def check_changed_files(self, options, mr, changed_files):
        success, msg = self.check_resourece()
        if not success:
            print(msg)
            return CheckResult.FAILED
        changed_java_files = [f for f in changed_files if f.endswith(".java")]
        errors = []
        for changed_java_file in changed_java_files:
            print(f"checking {changed_java_file}")
            print(subprocess.check_output("pwd", shell=True))
            success, output = self.run_check_style(changed_java_file)
            if not success:
                error_messages = output.splitlines()
                for error_message in error_messages:
                    if "[ERROR]" in error_message:
                        errors.append(error_message)
        if len(errors) != 0:
            print("android-check-style failed:")
            for error in errors:
                print(error)
            return CheckResult.FAILED
        else:
            return CheckResult.PASSED
