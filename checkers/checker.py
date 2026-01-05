# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
import re


class CheckResult:
    PASSED = "\033[32mPASSED\033[0m"
    FAILED = "\033[31mFAILED\033[0m"


class SimpleCache:
    def __init__(self):
        self._cache = {}

    def set(self, value):
        key = hash(value)
        self._cache.setdefault(key, value)
        return key

    def get(self, key):
        return self._cache.get(key)


class Checker:
    name = None
    help = None

    def __init__(self):
        self._file_name_cache = SimpleCache()

    def check_changed_lines(self, options, lines, line_indexes, changed_files):
        pass

    def check_changed_files(self, options, mr, changed_files):
        pass

    def get_file_name(self, key):
        return self._file_name_cache.get(key)

    def _check_changed_lines(
        self, options, changed_files, changed_lines, verbose=False
    ):
        current_file = None
        current_start_line = 0
        current_lines = []
        sections = []

        def finish_section(file, start_line, lines):
            if lines:
                key = self._file_name_cache.set(file)
                sections.append((key, start_line, lines))

        for line in changed_lines:
            if line.startswith("-"):
                continue
            elif line.startswith("+++"):
                finish_section(current_file, current_start_line, current_lines)
                current_lines = []
                matches = re.match(r"\+\+\+ b/(.*)", line)
                if not matches:
                    continue
                (current_file,) = matches.groups()
            elif line.startswith("@@"):
                finish_section(current_file, current_start_line, current_lines)
                current_lines = []

                matches = re.match(r"@@ -\d+(,\d+)? \+(\d+)(,\d+)? @@.*", line)
                if not matches:
                    continue
                line_number = matches.groups()[1]
                current_start_line = int(line_number)
            elif line.startswith("+"):
                current_lines.append(line[1:])

        finish_section(current_file, current_start_line, current_lines)

        # calculate offsets
        line_indexes = {}
        current_offset = -1
        changed_lines = []
        for section in sections:
            # section => (file_name_index, base_line_number, lines)
            if verbose:
                print(f"check section {section[0]}:{section[1]}")
            for i in range(len(section[2])):
                current_offset += 1
                line_indexes[current_offset] = (section[0], section[1] + i)
            changed_lines.extend(section[2])

        if verbose:
            for i, line in enumerate(changed_lines):
                print(f"{i}: {line}")
                file_name_index, line_no = line_indexes[i]
                print(self._file_name_cache.get(file_name_index) + ":" + str(line_no))

        return self.check_changed_lines(
            options, changed_lines, line_indexes, changed_files
        )

    def run(self, options, mr, changed_files):
        if options.all:
            return self.check_changed_files(options, mr, changed_files)
        else:
            if options.changed:
                changed_lines = mr.GetChangedLines().split("\n")
            else:
                changed_lines = mr.GetLastCommitLines().split("\n")

            return self._check_changed_lines(
                options, changed_files, changed_lines, options.verbose
            )
