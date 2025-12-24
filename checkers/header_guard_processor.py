#!/usr/bin/env python3

# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

# Objective-C headers that will directly skip to format header guard.
OBJECT_C_HEADERS = []

# Objective-C keywords.
OBJC_KEYWORDS = [
    "@interface",
    "@property",
    "@end",
    "@class",
    "@defs",
    "@protocol",
    "@selector",
    "@synthesize",
    "@dynamic",
    "NSString",
    "NSInteger",
    "NS_ENUM",
    "NS_OPTIONS",
    "NSDictionary",
    "#import",
    "NSObject",
    "NSValue",
    "NSArray",
    "NSSet",
    "NSNumber",
    "NSData",
    "NSURL",
    "NSMutableArray",
    "NSMutableDictionary",
    "NSMutableSet",
    "NSMutableString",
    "NSMutableData",
    "NSMutableURLRequest",
    "NSViewController",
    "NSResponder",
    "NSView",
    "NSColor",
    "NSFont",
    "NSTextField",
    "NSClickGestureRecognizer",
]


class HeaderGuardInfo:
    def __init__(
        self,
        file_path,
        ifndef,
        ifndef_linenum,
        define,
        endif,
        endif_linenum,
        correct_guard,
    ):
        self.file_path = file_path
        self.ifndef = ifndef
        self.ifndef_linenum = ifndef_linenum
        self.define = define
        self.endif = endif
        self.endif_linenum = endif_linenum
        self.correct_guard = correct_guard


def is_object_c_header(file_path, raw_lines):
    if file_path in OBJECT_C_HEADERS:
        return True
    file_content = " ".join(raw_lines)
    return any(keyword in file_content for keyword in OBJC_KEYWORDS)


def process_file_header_guard_if_needed(header_guard_info, raw_lines):
    file_path = header_guard_info.file_path
    ifndef = header_guard_info.ifndef
    ifndef_linenum = header_guard_info.ifndef_linenum
    define = header_guard_info.define
    endif = header_guard_info.endif
    endif_linenum = header_guard_info.endif_linenum
    correct_guard = header_guard_info.correct_guard

    new_contents = list(raw_lines)

    ifndef_line = f"#ifndef {correct_guard}"
    def_line = f"#define {correct_guard}"
    endif_line = f"#endif  // {correct_guard}"

    if not ifndef or not define or ifndef != define:
        new_contents = []
        header_guard_added = False
        for line in raw_lines:
            if not header_guard_added:
                if line.startswith("//"):
                    new_contents.append(line)
                else:
                    new_contents.append(ifndef_line)
                    new_contents.append(def_line + "\n")
                    header_guard_added = True
            else:
                if line == raw_lines[-1]:
                    new_contents.append(endif_line)
                new_contents.append(line)
    else:
        # ifndef
        new_contents[ifndef_linenum] = ifndef_line
        # define
        new_contents[ifndef_linenum + 1] = def_line
        # endif
        new_contents[endif_linenum] = endif_line

    new_content = "\n".join(new_contents[1:-1])
    raw_lines = "\n".join(raw_lines[1:-1])
    if raw_lines != new_content:
        with open(file_path, "w") as file:
            file.write(new_content)
        file.close()
