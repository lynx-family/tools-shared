#!/usr/bin/env python3

# Copyright 2023 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import argparse
import subprocess
import os
import re
import sys
import time

# Add the path of this file to system path, so we can import log
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import log


class ConstVars:
    # Supported file suffixes,
    # should be arranged in sequence of probability/proportion for better performance.
    # Suffix .js is not supported because there are binary template files in the project.
    suffixes_slash_as_comment = [
        ".h",
        ".cc",
        ".cpp",
        ".mm",
        ".m",
        ".java",
        ".kt",
        ".gradle",
    ]
    suffixes_pound_as_comment = [".gn", ".py", ".sh"]

    # Traverse result will be saved in this.
    file_list_unfiltered_template = "file_unfiltered_{}.list"
    # Escaped means: not changed, not 3rd party, not new. We don't know what it is.
    # This script need to be updated to support such cases.
    file_list_escaped_template = "file_escaped_{}.list"

    # This list is such high maintenance. DARN IT.
    third_party_list_file_name = "third_party_copyright_list"
    third_party_list = []

    # TODO(yueming): Add more to block list, or load from gitignore
    # If a directory contains any of these words, it's blocked
    directory_keyword_block_list = ["/.cxx", "/build"]

    class ActionType:
        CHECK = 0
        TRAVERSE = 1

    class TargetType:
        FILES = 1
        LIST = 2
        COMMIT = 3
        DIRECTORY = 4
        PROJ_LYNX = 5

    class ErrorCode:
        OK = 0
        INVALID_PARAMETER = -1
        INVALID_SETTINGS = -2
        UNKNOWN_ERROR = -99

    class ProjectLynxVars:
        anchor = "template-assembler"
        # Traverse these directories and only
        directory_allow_list = [
            "platfrom/android",
            "platfrom/darwin",
            "example",
            "lynx",
            "devtool",
            "oliver",
            "testing",
            "tools",
        ]


class Settings:
    # Save target files to a list and interrupt, so that we shall re-process this list of files anytime.
    # This is mainly for debug purpose.
    save_lists_to_files = False
    interrupt_after_list_saved = False

    # Save files that have escaped to a list, so that we shall re-process them after we make some changes.
    # This could be used for both debug purpose and actual online feature.
    save_escaped_cases_to_list = False


# ENTER DANGER ZONE ##################################################################################################
# Do NOT change the patterns, not even indents or newlines, unless you REALLY know what you are doing.
class Patterns:
    # FIXME(yueming): if useful comments follow old pattern with no empty line in between, the comments will be
    #   substituted and lost.
    #   It seems un-resolvable since we do want to substitute some comments and can only judge manually whether comments
    #   are useful or not.

    slash_pattern_1 = r"(//[\sa-zA-Z.+-_]*\n)*//\s*Copyright (\d{4}) The Lynx Authors. All rights reserved.?(\n//.*)*"
    slash_pattern_2 = r"(//[\sa-zA-Z.+-_]*\n)*//\s*Created by [\w.\s\u4e00-\u9fa5]* on (\d{4})[/\-\d]{4,6}.(\n//.*)*"
    slash_pattern_3 = r"//\s*Copyright © (\d{4}) Lynx. All rights reserved."
    slash_pattern_4 = r"\n*/\*(\n\s\*)* Copyright (\d{4}) The Lynx Authors. All rights reserved.(\n\s\*)*\n? \*/"
    pound_pattern_1 = r"# Copyright (\d{4}) The Lynx Authors. All rights reserved."

    # The elements in this array indicates the group index we must use to do the substitution.
    # BTW, a group is those enclosed by ( and ).
    # Using this index, we shall format the new_copyright_pattern string with the right value.
    # For example, when substituting slash_pattern_1,
    # we use the slash_substitution_group_index[0], i.e. 2.
    # Then we find the 2nd group in slash_pattern_1, (\d{4}), which is exactly the year we are looking for.
    # That makes the new pattern "// Copyright \g<2> The Lynx Authors ..."
    slash_substitution_group_index = [2, 2, 1, 2]
    pound_substitution_group_index = [1]

    # We have 2 formats (slash and pound) and 3 usages (sub, match and concat) of the new pattern.
    # In order not to declare 2 * 3 = 6 patterns here, we use a meta pattern.
    # It could be quite a bit tricky to understand.
    # For the 1st, 3rd and 4th {}, they should be replaced by comment mark, i.e. slash(//) or pound(#).
    # While for the 2nd {}, according to the usage of the regex, it should be replaced by
    # \d{4} for match
    # or \g<{}> for another format and further group substitution
    # or directly the year (say 2023) for concatenation.
    # Check the following examples:
    #
    # If used for re.match:
    #     r"""// Copyright \d{4} The Lynx Authors. All rights reserved.
    # // Licensed under the Apache License Version 2.0 that can be found in the
    # // LICENSE file in the root directory of this source tree."""
    #
    # If used for re.sub:
    #     r"""// Copyright \g<{}> The Lynx Authors. All rights reserved.
    # // Licensed under the Apache License Version 2.0 that can be found in the
    # // LICENSE file in the root directory of this source tree."""
    #
    # If used for string concatenation
    #     r"""// Copyright 2023 The Lynx Authors. All rights reserved.
    # // Licensed under the Apache License Version 2.0 that can be found in the
    # // LICENSE file in the root directory of this source tree."""
    new_meta_pattern = r"""{} Copyright {} The Lynx Authors. All rights reserved.
{} Licensed under the Apache License Version 2.0 that can be found in the
{} LICENSE file in the root directory of this source tree."""

    # This full version is only for match existing header.
    # Since it appears that only slash-comment code files have it, we just don't use meta pattern for this.
    new_pattern_for_match_slash_full = r"""// Copyright \d{4} The Lynx Authors. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 \(the \"License\"\);
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an \"AS IS\" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License."""


# EXIT DANGER ZONE ###################################################################################################


class AbstractCodeProcessor:
    def __init__(self):
        # A list of regex as old patterns which are possibly already used in files.
        # These patterns could be matched and substituted later.
        self.old_patterns = []
        # The new pattern that is to be substituted with.
        self.new_pattern_for_sub = r""
        # For different old patterns, the group index of year varies.
        # We need a list to record the indexes.
        self.sub_group_index = []
        # The new pattern used to match, in order to check if the file already contains it.
        # Be aware that re.match() checks the very start of the target string.
        # So you should deal with those characters in front of the copyright.
        self.new_pattern_for_match = r""
        # The full version new pattern used to match, in order to check if the file already contains it.
        self.new_pattern_for_match_full = r""
        # The new pattern used to concatenate.
        self.new_pattern_for_concat = r""

        self.current_year = time.localtime().tm_year

    def _get_file_starting_comment(self, content):
        """
        Get the starting comment part in a file.
        This is an abstract method for derived classes to override.

        Parameters:
        content: string contains the whole file
        Returns:
        string: the starting comment part.
        """
        return ""

    def _insert_copyright(self, content):
        """
        When none patterns (old/new/third) found, we assume there is no copyright.
        Then we just insert the new copyright at the proprietary position.
        The position depends on whether there is shebang.
        This is an abstract method for derived classes to override.

        Parameters:
        content: content of the file
        Returns:
        string: updated content of the file
        """
        updated_content = content
        return updated_content

    def _get_old_patterns_list(self):
        return self.old_patterns

    def _get_new_pattern_for_sub(self):
        return self.new_pattern_for_sub

    def _get_sub_group_index(self):
        return self.sub_group_index

    def _get_new_pattern_for_match(self):
        return self.new_pattern_for_match

    def _get_new_pattern_for_match_full(self):
        return self.new_pattern_for_match_full

    def _get_new_pattern_for_concat(self):
        return self.new_pattern_for_concat

    def _try_patterns(self, content):
        """
        Check if the file content matches any of the old patterns and substitute if matched

        Parameters:
        content: string contains the whole file
        Returns:
        boolean: whether file content matches any pattern
        string: content after substitution, could be the same if not matched any pattern
        """
        changed = False
        updated_content = ""
        old_patterns = self._get_old_patterns_list()
        new_pattern = self._get_new_pattern_for_sub()
        i = 0
        for old in old_patterns:
            updated_content = re.sub(
                old, new_pattern.format(self._get_sub_group_index()[i]), content
            )
            i += 1
            if updated_content != content:
                changed = True
                break
        return changed, updated_content

    @staticmethod
    def _has_third_party_copyright(comments):
        """
        Check if there is already 3rd-party copyright in the comments

        Parameters:
        comments: string with no '//' or '#' at the beginning of each line
        Returns:
        boolean: whether we found 3rd-party copyright.
        """
        # FIXME(yueming): multi copyright, the latter ones could be lost
        #   mainly Chromium copyright in cc files
        buffer = comments
        # Here 9 means the length of "Copyright"
        while len(buffer) > 9:
            copyright_index = buffer.find("opyright")
            if copyright_index < 0:
                # No more "Copyright" statement
                return False

            buffer = buffer[copyright_index:]
            newline_index = buffer.find("\n")
            if newline_index < 0:
                # WTF? An empty file?
                newline_index = len(buffer)

            # slice the single line
            sliced_single_line = buffer[:newline_index]
            # log.d(sliced_single_line)
            if any(sliced_single_line.find(e) >= 0 for e in ConstVars.third_party_list):
                # log.d("Found 3rd party copyright: {}".format(sliced_single_line))
                return True

            # Move on the next part
            buffer = buffer[newline_index:]
        # Not enough buffer and never found 3rd party
        return False

    def _is_already_new_copyright(self, content):
        """
        Check if the copyright is already what we want

        Parameters:
        content: string contains the whole file
        Returns:
        Match: new copyright of short version or full version if pattern matched, otherwise null
        """
        # Try short version
        match = re.match(self._get_new_pattern_for_match(), content)
        if not match:
            # Try full version
            match = re.match(self._get_new_pattern_for_match_full(), content)
        return match

    def _process_file_inner(self, file_path_name):
        """
        read content of the file, and update the copyright if necessary

        Parameters:
        file_path_name: string of the path and the name of the file
        Returns:
        boolean: whether file content matches any pattern
        boolean: whether we found 3rd-party copyright at the beginning part
        boolean: whether new copyright already exists
        string: content after substitution, could be the same if not matched any pattern
        """
        changed = False
        is_third_party_copyright = False
        is_already_new = False
        updated_content = ""
        with open(file_path_name, "r") as file:
            try:
                content = file.read()
            except UnicodeDecodeError:
                log.e("Couldn't read the file {}".format(file_path_name))
                file.close()
                # early return
                return (
                    changed,
                    is_third_party_copyright,
                    is_already_new,
                    updated_content,
                )

        comment_part = self._get_file_starting_comment(content)
        if len(comment_part) == 0:
            # There were no comments at the beginning. We just insert the copyright.
            updated_content = self._insert_copyright(content)
            changed = True
        else:
            # There were comments.
            if self._has_third_party_copyright(comment_part):
                # The copyright belongs to a 3rd party. Don't do anything.
                # Let's update it manually later with the information in log.
                # You can never be too careful with it.
                is_third_party_copyright = True
            else:
                # FIXME(yueming): content could start with blank line, which makes the judgement of new copyright
                #  incorrect
                if self._is_already_new_copyright(content):
                    # It's already the new copyright. Don't do anything.
                    is_already_new = True
                else:
                    changed, updated_content = self._try_patterns(content)

        file.close()
        return changed, is_third_party_copyright, is_already_new, updated_content

    @staticmethod
    def _process_file_inner_post(
        file_path_name,
        changed,
        is_third_party_copyright,
        is_already_new,
        updated_content,
    ):
        """
        After updating the file content, write back to the file. If nothing changed, log an entry.

        Parameters:
        file_path_name: string of the path and the name of the file
        changed: whether file content has been changed
        is_third_party_copyright: whether we found 3rd-party copyright at the beginning part
        is_already_new: whether new copyright already exists
        updated_content: content after substitution, could be the same if not matched any pattern
        """
        if changed:
            with open(file_path_name, "w") as file2:
                file2.write(updated_content)
                file2.close()
        elif is_third_party_copyright:
            log.d("3rd party copyright:\t{}".format(file_path_name))
        elif is_already_new:
            log.d("Already the new copyright:\t{}".format(file_path_name))
        else:
            log.d("Nothing changed:\t{}".format(file_path_name))

    def process_file(self, file_path_name):
        """
        Process a single source code file.

        Parameters:
        file_path_name: string of the path and the name of the file
        Returns:
        boolean: whether file content has been changed
        boolean: whether we found 3rd-party copyright at the beginning part
        boolean: whether new copyright already exists
        """
        log.d("Processing {}".format(file_path_name))
        changed, is_third_party_copyright, is_already_new, updated_content = (
            self._process_file_inner(file_path_name)
        )
        self._process_file_inner_post(
            file_path_name,
            changed,
            is_third_party_copyright,
            is_already_new,
            updated_content,
        )
        return changed, is_third_party_copyright, is_already_new


class SlashCommentCodeProcessor(AbstractCodeProcessor):
    def __init__(self):
        super().__init__()
        self.old_patterns = [
            Patterns.slash_pattern_1,
            Patterns.slash_pattern_2,
            Patterns.slash_pattern_3,
            Patterns.slash_pattern_4,
        ]
        self.new_pattern_for_sub = Patterns.new_meta_pattern.format(
            "//", "\g<{}>", "//", "//"
        )
        self.sub_group_index = Patterns.slash_substitution_group_index
        # Ignore the starting characters
        self.new_pattern_for_match = Patterns.new_meta_pattern.format(
            "[\S\s]*//", "\d{4}", "//", "//"
        )
        # Just use directly the pattern with no format, assuming that the copyright is at the start.
        self.new_pattern_for_match_full = Patterns.new_pattern_for_match_slash_full
        self.new_pattern_for_concat = Patterns.new_meta_pattern.format(
            "//", self.current_year, "//", "//"
        )

    def _get_file_starting_comment(self, content):
        lines = content.split("\n")
        comments = []
        in_multi_line_mode = False

        for line in lines:
            line = line.strip()

            if len(line) == 0:
                # Ignore blank lines before "real" code starts
                continue

            if line.startswith("//"):
                comments.append(line[2:].strip())
            elif line.startswith("/*"):
                comments.append(line[2:].strip())
                in_multi_line_mode = True
            elif line.startswith("*"):
                if in_multi_line_mode:
                    comments.append(line[1:].strip())
                else:
                    # End of comments. And the real code starts with an '*'
                    break
            elif line.startswith("*/"):
                # FIXME(yueming): What if '*/' was at the end of a line
                in_multi_line_mode = False
            else:
                if in_multi_line_mode:
                    comments.append(line.strip())
                else:
                    break

        return "\n".join(comments)

    def _insert_copyright(self, content):
        # Just insert at the beginning
        return self._get_new_pattern_for_concat() + "\n" + content


class PoundCommentCodeProcessor(AbstractCodeProcessor):
    def __init__(self):
        super().__init__()
        self.old_patterns = [Patterns.pound_pattern_1]
        self.new_pattern_for_sub = Patterns.new_meta_pattern.format(
            "#", "\g<{}>", "#", "#"
        )
        self.sub_group_index = Patterns.pound_substitution_group_index
        # Ignore the starting characters
        self.new_pattern_for_match = Patterns.new_meta_pattern.format(
            "[\S\s]*#", "\d{4}", "#", "#"
        )
        # Just leave a dummy regex here since the case is unlikely
        self.new_pattern_for_match_full = r"This is a dummy regex"
        self.new_pattern_for_concat = Patterns.new_meta_pattern.format(
            "#", self.current_year, "#", "#"
        )
        self.shebang = ""

    def _get_file_starting_comment(self, content):
        lines = content.split("\n")
        shebang_checked = False
        comments = []
        in_multi_line_mode = False

        for line in lines:
            line = line.strip()

            if len(line) == 0:
                # Ignore blank lines before "real" code starts
                continue

            if not shebang_checked and line.startswith("#!/usr/bin/env"):
                # Check shebang once
                self.shebang = line
                shebang_checked = True
                continue

            if line.startswith("#"):
                comments.append(line[1:].strip())
            elif line.startswith('"""') or line.startswith("'''"):
                # FIXME(yueming): What if '"""' was at the end of a line
                if in_multi_line_mode:
                    # End of multi line comments
                    in_multi_line_mode = False
                else:
                    # Start of multi line comments
                    in_multi_line_mode = True
                    comments.append(line[3:].strip())
            else:
                if in_multi_line_mode:
                    continue
                else:
                    break

        return "\n".join(comments)

    def _insert_copyright(self, content):
        first_next_line = content.find("\n")
        first_line = content[:first_next_line]
        if first_line.startswith("#!/usr/bin/env"):
            # has shebang at the beginning
            updated_content = (
                first_line
                + "\n"
                + self._get_new_pattern_for_concat()
                + content[first_next_line:]
            )
        else:
            # no shebang
            updated_content = self._get_new_pattern_for_concat() + "\n" + content
        return updated_content


class Utils:
    @staticmethod
    def save_list_to_file(string_list, file_path):
        count = len(string_list)
        if count <= 0:
            return

        log.i("Saving list with {} items to file: {}".format(count, file_path))
        # append to the file
        with open(file_path, "a") as file:
            for string in string_list:
                # write an extra newline
                file.write(string + "\n")

    @staticmethod
    def load_list_from_file(file_path):
        log.i("Loading list from file: {}".format(file_path))
        string_list = []
        try:
            file = open(file_path, "r")
            for line in file:
                # remove the extra newline
                string_list.append(line.rstrip("\n"))
            file.close()
        except FileExistsError:
            log.e(f"File not exist:{file_path}")
        return string_list


def list_files_in_directory(directory):
    """
    List all files under certain directory, excluding those directories in the block list

    Parameters:
    directory (string): the directory to be traversed
    Returns:
    list (of strings): file list.
    """
    out_list = []
    for root, dirs, files in os.walk(directory):
        if any(
            root.find(block) != -1 for block in ConstVars.directory_keyword_block_list
        ):
            # log.d("Path skipped: {}".format(root))
            continue
        # log.d("{} has {} dirs and {} files in total".format(root, len(dirs), len(files)))
        for file in files:
            full_file_name = os.path.join(root, file)
            out_list.append(full_file_name)
    return out_list


def process_file_unfiltered(file_path_name):
    """
    Process a file with unfiltered suffixes.

    Parameters:
    file_path_name: the file name of the list file.
    Returns:
    int: the number of files whose content has been changed, 1 or 0 in this case.
    """
    if any(
        file_path_name.endswith(slash) for slash in ConstVars.suffixes_slash_as_comment
    ):
        processor = SlashCommentCodeProcessor()
    elif any(
        file_path_name.endswith(pound) for pound in ConstVars.suffixes_pound_as_comment
    ):
        processor = PoundCommentCodeProcessor()
    else:
        log.d("{} is not supported, skipping...".format(file_path_name))
        return 0

    changed, is_third_party_copyright, is_already_new = processor.process_file(
        file_path_name
    )
    return 1 if changed else 0


def process_list_of_one_type_with_processor(file_list, processor):
    """
    Process a list of files with suffixes of the same category (e.g. slash, pound), using specified processor.

    Parameters:
    file_list: list of files with certain suffixes of the same category.
    processor: processor to use
    Returns:
    int: the number of files whose content has been changed.
    """
    changed_count = 0
    third_party_count = 0
    already_new_count = 0
    escaped_list = []

    for f in file_list:
        changed, is_third_party_copyright, is_already_new = processor.process_file(f)
        if changed:
            changed_count += 1
        elif is_third_party_copyright:
            third_party_count += 1
        elif is_already_new:
            already_new_count += 1
        else:
            escaped_list.append(f)
    if Settings.save_escaped_cases_to_list:
        current_time = int(time.time())
        Utils.save_list_to_file(
            escaped_list, ConstVars.file_list_escaped_template.format(current_time)
        )

    log.i(
        "Done processing list including {} files, changed {}, third party {}, already new {}, escaped {}".format(
            len(file_list),
            changed_count,
            third_party_count,
            already_new_count,
            len(escaped_list),
        )
    )
    return changed_count


def process_lists_filtered(slash_file_list, pound_file_list):
    """
    Process two lists containing files with filtered suffixes.
    Each list contains one category of file (slash, pound).

    Parameters:
    slash_file_list: list of files using slash as comment
    pound_file_list: list of files using pound as comment
    Returns:
    int: the number of files whose content has been changed
    """
    changed_count = 0
    if len(slash_file_list) > 0:
        slash_processor = SlashCommentCodeProcessor()
        changed_count = changed_count + process_list_of_one_type_with_processor(
            slash_file_list, slash_processor
        )
    if len(pound_file_list) > 0:
        pound_processor = PoundCommentCodeProcessor()
        changed_count = changed_count + process_list_of_one_type_with_processor(
            pound_file_list, pound_processor
        )
    return changed_count


def process_list_unfiltered_from_memory(
    file_list, save_lists_to_files=False, interrupt_after_list_saved=False
):
    """
    Process a list containing files with unfiltered suffixes.
    In this method, we also check if we need to save list to a file on disk and if we need to interrupt after that.

    Parameters:
    file_list_of_one_suffix: list of files with unfiltered suffixes
    Returns:
    int: the number of files whose content has been changed
    """
    if save_lists_to_files:
        current_time = int(time.time())
        Utils.save_list_to_file(
            file_list, ConstVars.file_list_unfiltered_template.format(current_time)
        )
        if interrupt_after_list_saved:
            return 0

    log.i("file count: {}".format(len(file_list)))
    slash_file_list = []
    pound_file_list = []
    for f in file_list:
        if any(f.endswith(slash) for slash in ConstVars.suffixes_slash_as_comment):
            slash_file_list.append(f)
        elif any(f.endswith(pound) for pound in ConstVars.suffixes_pound_as_comment):
            pound_file_list.append(f)
        else:
            log.d("{} is not supported, skipping...".format(f))

    return process_lists_filtered(slash_file_list, pound_file_list)


def process_list_unfiltered_from_disk(file_path_name):
    """
    Load a list containing files from disk and process it

    Parameters:
    file_path_name: the file name of the list file
    Returns:
    int: the number of files whose content is changed
    """
    file_list = Utils.load_list_from_file(file_path_name)
    return process_list_unfiltered_from_memory(file_list, save_lists_to_files=False)


def process_commit(commit_id):
    """
    Process all changed files in the commit

    Parameters:
    commit_id: the id of the commit. HEAD works as well.
    Returns:
    int: the number of files whose content is changed
    """
    cmd = ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", commit_id]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    # We will get [change status - file name] pairs
    # For change status, it refers to A(dd), M(odify) or D(elete)
    pair_list = result.stdout.splitlines()
    file_list = []
    # Ignore the deleted files
    # Actually, let's just focus on the added files at the moment.
    for pair in pair_list:
        status, file_name = pair.split("\t")
        if status == "A":
            file_list.append(file_name)

    if len(file_list) == 0:
        return 0

    # Since the filepaths here are relative, so the script is expected be called at the root of the repo
    # Let's do a check here
    if not os.path.isfile(file_list[0]):
        log.e("File not exist: {}".format(file_list[0]))
        log.e("Maybe this script is not called from the root of the repository.")
        return 0

    return process_list_unfiltered_from_memory(file_list, save_lists_to_files=False)


def process_directory(directory):
    """
    Process all files in current directory

    Parameters:
    directory: the directory to be processed
    Returns:
    int: the number of files whose content is changed
    """
    unfiltered_file_list = list_files_in_directory(directory)
    return process_list_unfiltered_from_memory(
        unfiltered_file_list,
        save_lists_to_files=Settings.save_lists_to_files,
        interrupt_after_list_saved=Settings.interrupt_after_list_saved,
    )


def locate_project_root():
    """
    Find the full path of Lynx project from current execution path.

    Returns:
    string: The full path of Lynx project.
    """
    # locate the root directory from current directory
    current_directory = os.getcwd()
    index = current_directory.find(ConstVars.ProjectLynxVars.anchor)
    if index == -1:
        log.e("Could not find root directory.")
        return -1
    root_directory = current_directory[: index + len(ConstVars.ProjectLynxVars.anchor)]
    log.i("Root directory: {}".format(root_directory))
    return root_directory


def process_project_lynx():
    """
    Process all files in current "template-assembler" project

    Returns:
    int: the number of files whose content is changed
    """
    # Get root directory
    root_directory = locate_project_root()
    # Process only files under directories in the allow list
    count = 0
    for e in ConstVars.ProjectLynxVars.directory_allow_list:
        d = os.path.join(root_directory, e)
        count = count + process_directory(d)
    return count


def load_third_party_list():
    """
    Load third party allowlist from file
    """
    abs_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ConstVars.third_party_list_file_name
    )
    try:
        with open(abs_file_path, "r") as file:
            third_party_list = file.readlines()
        # Remove the newline character at the end of each line
        ConstVars.third_party_list = [
            line.strip() for line in third_party_list if not line.startswith("#")
        ]
    except FileExistsError:
        log.e(f"File not exist:{ConstVars.third_party_list_file_name}")
        return False
    return True


def parse_args():
    # Create the parser
    parser = argparse.ArgumentParser(description="Update Lynx License")

    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--check",
        "-c",
        help="check if the target files meet the requirement and update",
        action="store_true",
    )
    actions.add_argument(
        "--traverse-only",
        "-t",
        help="only traverse the directory and generate a list "
        "containing all the files in it for later use. No file will be "
        "changed.",
        action="store_true",
    )

    targets = parser.add_mutually_exclusive_group(required=True)

    # targets.add_argument('--file', '-f', help='Process one single given file')
    targets.add_argument(
        "--files", "-f", nargs="+", help="process multiple given files"
    )
    targets.add_argument(
        "--list-file", "-l", help="process all the files in the given list file"
    )
    targets.add_argument("--commit", "-m", help="process files in the given commit-id")
    targets.add_argument(
        "--directory", "-d", help="process recursively given directory"
    )
    targets.add_argument(
        "--project-lynx",
        help="[not recommended]. process the project Lynx, i.e. the "
        "template-assembler repository, with a preset allowlist to specify "
        "directories. Be careful that this can be significantly slow",
        action="store_true",
    )

    parser.add_argument("--verbose", "-v", help="more logs", action="store_true")

    parser.add_argument(
        "--save-escape", help="save escaped cases to a file", action="store_true"
    )

    # Parse the arguments
    args = parser.parse_args()

    # success, action_type, target_type, target
    err_ret = False, None, None, None

    v = True if args.verbose else False
    log.init(verbose=v)

    # Retrieve the action_type
    if args.check:
        action_type = ConstVars.ActionType.CHECK
    elif args.traverse_only:
        action_type = ConstVars.ActionType.TRAVERSE
        Settings.save_lists_to_files = True
        Settings.interrupt_after_list_saved = True
    else:
        # Shouldn't reach here, since required=True is specified
        return err_ret

    # Retrieve the target
    if args.files:
        target_type = ConstVars.TargetType.FILES
        target = args.files
    elif args.list_file:
        target_type = ConstVars.TargetType.LIST
        target = args.list_file
    elif args.commit:
        target_type = ConstVars.TargetType.COMMIT
        target = args.commit
    elif args.directory:
        target_type = ConstVars.TargetType.DIRECTORY
        target = args.directory
    elif args.project_lynx:
        target_type = ConstVars.TargetType.PROJ_LYNX
        target = "project Lynx"
    else:
        # Shouldn't reach here, since required=True is specified
        return err_ret

    # Advanced settings
    if args.save_escape:
        Settings.save_escaped_cases_to_list = True

    return True, action_type, target_type, target


def main():
    success, action_type, target_type, target = parse_args()
    if not success:
        log.e("Parsing arguments failed")
        return ConstVars.ErrorCode.INVALID_PARAMETER

    if action_type is ConstVars.ActionType.TRAVERSE and (
        target_type is not ConstVars.TargetType.DIRECTORY
        or target is not ConstVars.TargetType.PROJ_LYNX
    ):
        log.e("Wrong combination of arguments.")
        return ConstVars.ErrorCode.INVALID_PARAMETER

    # Load stuff after args check, so that this won't be in vain
    if not load_third_party_list():
        return ConstVars.ErrorCode.INVALID_SETTINGS

    if target_type is ConstVars.TargetType.FILES:
        process_list_unfiltered_from_memory(target)
    elif target_type is ConstVars.TargetType.LIST:
        process_list_unfiltered_from_disk(target)
    elif target_type is ConstVars.TargetType.COMMIT:
        process_commit(target)
    elif target_type is ConstVars.TargetType.DIRECTORY:
        process_directory(target)
    elif target_type is ConstVars.TargetType.PROJ_LYNX:
        # TODO(yueming): check this later
        log.w(
            "Processing the whole project is considerably slow. So the function is temporarily disabled."
        )
        # process_project_lynx()

    return ConstVars.ErrorCode.OK


if __name__ == "__main__":
    sys.exit(main())
