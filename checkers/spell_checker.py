# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import os.path
import re
import subprocess
import sys

from checkers.utils import match_globs

try:
    import yaml
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyYAML~=6.0"])
    import yaml

from checkers.checker import Checker, CheckResult

CHECK_COUNT_EACH_TIME = 50
CSPELL_CONFIG_FILE = "cspell.config.yml"
BASE_COMMAND = [
    "npx",
    "--no-install",
    "cspell",
    "lint",
    "--gitignore",
    "--no-must-find-files",
    "--show-suggestions",
    "-c",
    CSPELL_CONFIG_FILE,
]


class SpellChecker(Checker):
    name = "spell"
    help = "Check file type"

    def check_changed_lines(self, options, lines, line_indexes, changed_files):
        with open(CSPELL_CONFIG_FILE, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        tmp_lines = lines
        lines = []
        ignored_files = dict()
        for i, line in enumerate(tmp_lines):
            file_name_index, line_no = line_indexes[i]
            file_name = self.get_file_name(file_name_index)

            if match_globs(file_name, config.get("ignorePaths", [])):
                if not ignored_files.get(file_name):
                    # Only print the ignored message once for each file.
                    print(
                        "path %s is ignored in configure file %s"
                        % (file_name, CSPELL_CONFIG_FILE)
                    )
                    ignored_files[file_name] = True
                # an empty line to avoid line indexes mismatch
                lines.append("")
                continue
            lines.append(line)

        cmd = BASE_COMMAND + ["stdin"]
        try:
            subprocess.check_output(cmd, input="\n".join(lines), encoding="utf-8")
        except subprocess.CalledProcessError as err:

            result = CheckResult.PASSED
            for output_line in err.output.split("\n"):
                if not output_line.strip():
                    continue
                # Use re.search instead of match to match anywhere instead of the beginning of the string
                # see: https://docs.python.org/3/library/re.html#search-vs-match
                match = re.search(r":(\d+)(:\d+ - .*)", output_line)
                if not match:
                    continue
                offset, message = match.groups()
                offset = int(offset) - 1
                file_name_index, line_no = line_indexes[offset]
                file_name = self.get_file_name(file_name_index)

                print(r"%s:%d%s" % (file_name, line_no, message))
                result = CheckResult.FAILED
            return result
        else:
            return CheckResult.PASSED

    def check_changed_files(self, options, mr, changed_files):
        result = CheckResult.PASSED
        count = 0
        files_count = len(changed_files)
        while count < files_count:
            sub_files = changed_files[
                count : min(count + CHECK_COUNT_EACH_TIME, files_count)
            ]
            cmd = BASE_COMMAND + sub_files
            count += CHECK_COUNT_EACH_TIME
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                print(e.output)
                result = CheckResult.FAILED
        return result
