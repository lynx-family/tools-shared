#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import os.path

from cocoapods.attr_types import Rebase
from cocoapods.files_accessor import FilesAccessor
from cocoapods.precompiled_header import PrecompiledHeader
from cocoapods.targets.gn.utils import create_target
from cocoapods.utils import parse_shell_style_vars, expandvars

HEADER_FILES_EXTENSIONS = (
    "h",
    "hh",
    "hpp",
    "ipp",
    "tpp",
    "hxx",
    "def",
    "inl",
    "inc",
    "s",
    "S",
)
SOURCE_FILE_EXTENSIONS = (
    "m",
    "mm",
    "i",
    "c",
    "cc",
    "cxx",
    "cpp",
    "c++",
    "swift",
) + HEADER_FILES_EXTENSIONS
GLOBAL_CFLAGS = ["-Wno-error"]
GLOBAL_REMOVED_CONFIGS = ["//build/config/gcc:no_exceptions"]

GLOB_PATTERNS = {
    "readme": "readme{*,.*}",
    "license": "licen{c,s}e{*,.*}",
    "source_files": f'*{",".join(SOURCE_FILE_EXTENSIONS)}',
    "public_header_files": f'*{",".join(HEADER_FILES_EXTENSIONS)}',
    "podspecs": "*.{podspec,podspec.json}",
    "docs": "doc{s}{*,.*}/**/*",
}


class Specification:
    def __init__(
        self,
        pod,
        parent,
        spec_content,
        test_specification=False,
        app_specification=False,
    ):
        self.parent = parent
        self.pod = pod
        self._files_accessor = FilesAccessor(pod.target_dir, spec=self)

        attrs = {**spec_content}
        subspecs = attrs.pop("subspecs", [])
        testspecs = attrs.pop("testspecs", [])
        appspecs = attrs.pop("appspecs", [])
        self._attrs = attrs
        self._attrs["test_specification"] = "test_type" in attrs or test_specification
        self._attrs["app_specification"] = app_specification

        self.subspecs = (
            [
                Specification(self.pod, self, content, False, False)
                for content in subspecs
            ]
            + [
                Specification(self.pod, self, content, False, True)
                for content in appspecs
            ]
            + [
                Specification(self.pod, self, content, True, False)
                for content in testspecs
            ]
        )
        self.requires = []
        self.required_by = []

        for subspec in self.subspecs:
            for key, value in self._attrs.items():
                if key == "pod_target_xcconfig":
                    subspec.set_attr(
                        key, {**value, **getattr(subspec, "pod_target_xcconfig", {})}
                    )
                elif not hasattr(subspec, key):
                    subspec.set_attr(key, value)

        self._targets = {}
        self.header_mappings = []

    def all_specs(self):
        specs = [self]
        for spec in self.subspecs:
            specs += spec.all_specs()
        return specs

    def get_attrs(self):
        return self._attrs

    def get_header_mappings(self, platform, header_files):
        attrs = getattr(self, platform, None) if platform else self._attrs
        if not attrs:
            return {}
        header_mappings_dir = attrs.get("header_mappings_dir", "")

        mappings = {}
        dir_ = os.path.join(attrs.get("header_dir", ""))

        for header in header_files:
            if header_mappings_dir and header.startswith(header_mappings_dir):
                relative_path = os.path.relpath(header, header_mappings_dir)
                target_header_path = os.path.join(dir_, relative_path)
            else:
                target_header_path = os.path.join(dir_, os.path.basename(header))
            mappings[target_header_path] = header
        return mappings

    def set_attr(self, key, value):
        self._attrs[key] = value

    def add_required_by(self, spec):
        self.required_by.append(spec)

    def add_require(self, spec):
        self.requires.append(spec)
        spec.add_required_by(self)

    def __getattr__(self, item):
        if item.startswith("__"):
            return getattr(super(), item)
        try:
            return self._attrs[item]
        except KeyError:
            raise AttributeError(f"attribute {item} not found")

    def glob_files_with_patterns(self, file_patterns, include_dirs=False):
        file_patterns = (
            file_patterns if isinstance(file_patterns, list) else [file_patterns]
        )
        # source_dir = self.pod.local_source_dir
        file_list = []
        for pattern in file_patterns:
            if not pattern:
                continue
            # if os.path.isdir(os.path.join(source_dir, pattern)):
            #     file_list += get_files_in_dir(os.path.join(source_dir, pattern))
            #     continue
            #
            # file_list += glob_files(source_dir, pattern)
            file_list += self._files_accessor.glob_files(
                pattern, include_dirs=include_dirs
            )
        return file_list

    def glob_files_for_attr(self, attr, platform, include_dirs=False):
        attrs = getattr(self, platform, None) if platform else self._attrs
        if attrs is None:
            return []
        return self.glob_files_with_patterns(
            attrs.get(attr, []), include_dirs=include_dirs
        )

    def convert_xcconfig_for_platform(
        self, target, xcconfig, platform=None, rebase=None
    ):
        definitions = xcconfig.get("GCC_PREPROCESSOR_DEFINITIONS")
        if definitions:
            definitions = definitions.replace("$(inherited)", "")
            definitions = [
                f"{k}={v}" if v else k
                for k, v in parse_shell_style_vars(definitions).items()
            ]
            target.add_defines(definitions)
        header_search_paths = (
            xcconfig.get("HEADER_SEARCH_PATHS", "")
            + " "
            + xcconfig.get("USER_HEADER_SEARCH_PATHS", "")
        )
        if header_search_paths:
            header_search_paths = header_search_paths.replace("$(inherited)", "")
            target.add_include_dirs(
                [
                    os.path.relpath(expandvars(p), rebase or self.pod.target_dir)
                    for p in header_search_paths.split()
                ]
            )
        cplusplus_flags = xcconfig.get("OTHER_CPLUSPLUSFLAGS")
        if cplusplus_flags:
            target.add_cflags_cc(cplusplus_flags.split())

    def convert_attrs_for_platform(
        self, target, attrs, platform, root_dir, rebase=None
    ):
        compiler_flags = attrs.get("compiler_flags", [])
        for f in (
            compiler_flags if isinstance(compiler_flags, list) else [compiler_flags]
        ):
            if f.startswith("-I$"):
                f = expandvars(f)
                target.add_cflags(f, condition=platform)
            else:
                target.add_cflags(tuple(f.split()), condition=platform)
        target.add_cflags("-I.")

        frameworks = attrs.get("frameworks", None)
        if frameworks:
            frameworks = (
                [f"{v}.framework" for v in frameworks]
                if isinstance(frameworks, list)
                else f"{frameworks}.framework"
            )
            target.add_frameworks(frameworks, condition=platform)

        target.add_libs(
            self._files_accessor.get_libraries(platform, rebase=rebase),
            condition=platform,
        )
        vendored_libraries = self._files_accessor.get_vendored_libraries(
            platform, rebase=rebase
        )
        for lib in vendored_libraries:
            target.add_lib_dirs(os.path.dirname(lib), condition=platform)
        target.add_libs(vendored_libraries, condition=platform)

    def all_header_mappings(self):
        private_mappings = []
        public_mappings = []
        for platform in [None, "ios", "osx"]:
            header_files = self._files_accessor.get_headers(platform)
            public_header_files = self._files_accessor.get_public_headers(platform)
            private_mappings += [
                (target, source)
                for target, source in self.get_header_mappings(
                    platform, header_files
                ).items()
            ]
            public_mappings += [
                (target, source)
                for target, source in self.get_header_mappings(
                    platform, public_header_files
                ).items()
            ]

        for spec in self.subspecs:
            private, public = spec.all_header_mappings()
            private_mappings += private
            public_mappings += public
        return private_mappings, public_mappings

    def collect_headers(self, platform):
        header_files = self._files_accessor.get_headers(platform)
        public_header_files = self._files_accessor.get_public_headers(platform)
        header_mappings = self.get_header_mappings(platform, header_files)
        public_header_mappings = self.get_header_mappings(platform, public_header_files)

        header_dir = os.path.join(
            os.path.dirname(self.pod.target_dir),
            "Headers",
        )
        private_header_dir = os.path.join(header_dir, "Private", self.pod.name)
        public_header_dir = os.path.join(header_dir, "Public", self.pod.name)

        for target, source in header_mappings.items():
            target_path = os.path.join(private_header_dir, target)
            source_path = os.path.join(self.pod.target_dir, source)
            self.header_mappings.append((source_path, target_path))

        for target, source in public_header_mappings.items():
            target_path = os.path.join(public_header_dir, target)
            source_path = os.path.join(self.pod.target_dir, source)
            self.header_mappings.append((source_path, target_path))

        return header_mappings, public_header_mappings

    def get_or_create_target(self, type_, name):
        key = f"{name}-{type_}"
        created = False
        if key not in self._targets:
            self._targets[key] = create_target(type_, name)
            created = True
        return self._targets[key], created

    def get_full_name(self, sep="_"):
        names = []
        p = self.parent
        while p:
            names.insert(0, p.name)
            p = p.parent
        names.append(self.name)
        return sep.join(names)

    def convert_vendored_frameworks(self, name, target, platform, rebase):
        vendored_framework_files = self._files_accessor.get_vendored_frameworks(
            platform, rebase=rebase
        )
        if not vendored_framework_files:
            return
        frameworks = {
            f.split("/")[-1].split(".framework")[0]: f for f in vendored_framework_files
        }

        for framework_name, framework in frameworks.items():
            lib_file = os.path.join(framework, framework_name)
            # shared_library
            output_lib_file = "$root_out_dir/" + framework_name
            shared_library_name = f"{name}_{framework_name}_dylib"
            shared_library_target, _ = self.get_or_create_target(
                "shared_library", shared_library_name
            )
            shared_library_target.set_output_name(framework_name)
            shared_library_target.set_output_extension("")
            shared_library_target.set_output_prefix_override(True)
            shared_library_target.add_libs(lib_file)
            shared_library_target.add_ldflags(
                (
                    "-Xlinker",
                    "-install_name",
                    "-Xlinker",
                    f"@rpath/{framework_name}.framework/{framework_name}",
                )
            )

            # bundle_data
            bundle_name = f"{name}_{framework_name}_framework_bundle"
            bundle_target, _ = self.get_or_create_target("bundle_data", bundle_name)
            bundle_target.add_sources(output_lib_file)
            bundle_target.add_sources(os.path.join(framework, "Info.plist"))
            bundle_target.add_outputs(
                "{{bundle_resources_dir}}/Frameworks/"
                + framework_name
                + ".framework/{{source_file_part}}"
            )
            bundle_target.add_public_deps(f":{shared_library_name}")
            target.add_public_deps(f":{bundle_name}")

    def convert_to(self, type_, root_dir, rebase=None):
        self._files_accessor.clean_cache()

        attrs = self._attrs
        name = self.get_full_name()
        target, _ = self.get_or_create_target("source_set", name)

        public_config_name = f"{name}_public_config"
        private_config_name = f"{name}_private_config"
        private_config, _ = self.get_or_create_target("config", private_config_name)
        public_config, _ = self.get_or_create_target("config", public_config_name)

        target.add_configs(f":{private_config_name}")
        target.add_public_configs(f":{public_config_name}")

        requires_arc = attrs.get("requires_arc")
        arc_sources = None
        if isinstance(requires_arc, list):
            arc_source_set_name = f"{name}_arc"
            arc_source_set, _ = self.get_or_create_target(
                "source_set", arc_source_set_name
            )
            arc_sources = self._files_accessor.glob_files_for_attr(
                "requires_arc", None, rebase=rebase
            )
            arc_source_set.add_sources(arc_sources)
            arc_source_set.add_configs(f":{private_config_name}")
            arc_source_set.add_configs(f":{public_config_name}")
            arc_source_set.add_cflags_objc("-fobjc-arc")
            arc_source_set.add_cflags_objcc("-fobjc-arc")

            target.add_deps(f":{arc_source_set_name}")
        elif requires_arc is False:
            private_config.add_cflags_objc("-fno-objc-arc")
            private_config.add_cflags_objcc("-fno-objc-arc")
        else:
            private_config.add_cflags_objc("-fobjc-arc")
            private_config.add_cflags_objcc("-fobjc-arc")

        for platform in [None, "ios", "osx"]:
            if platform:
                pch_path = self.pod.get_pch_file(platform)
                if pch_path:
                    private_config.add_cflags(
                        (
                            "-include",
                            Rebase(
                                os.path.relpath(
                                    pch_path, rebase or self.pod.target_dir
                                ),
                                "root_build_dir",
                            ),
                        ),
                        platform,
                    )

            if platform and not hasattr(self, platform):
                continue
            attrs = self._attrs if platform is None else getattr(self, platform)

            source_files = self._files_accessor.get_source_files(
                platform, rebase=rebase
            )
            target.add_sources(
                source_files
                if not arc_sources
                else [f for f in source_files if f not in arc_sources]
            )

            # resources
            resources = self._files_accessor.get_resources(platform, rebase=rebase)
            # FIXME(wangjianliang): remove the hard coded list
            if resources and name not in ["lens_ImageVRSR", "lens_ImageNNSR"]:
                bundle_name = f"{name}_bundle"
                resources_target, _ = self.get_or_create_target(
                    "bundle_data", bundle_name
                )
                resources_target.add_sources(resources)
                resources_target.add_outputs(
                    "{{bundle_resources_dir}}/{{source_file_part}}"
                )
                target.add_public_deps(f":{bundle_name}")

            for spec in self.requires:
                dep_name = spec.get_full_name()
                if dep_name.startswith("Lynx"):
                    # handle dependency that depends Lynx
                    dep_name = f'//:{dep_name.replace("Lynx_", "")}'
                elif dep_name.startswith(self.pod.name + "_"):
                    dep_name = f":{dep_name}"
                else:
                    dep_name = (
                        f"//{os.path.relpath(os.path.dirname(rebase or self.pod.target_dir), root_dir)}/"
                        f"{spec.pod.name}:{spec.get_full_name()}"
                    )

                target.add_deps(dep_name, condition=platform)

            self.convert_vendored_frameworks(name, target, platform, rebase)
            self.convert_attrs_for_platform(
                private_config, attrs, platform, root_dir=root_dir, rebase=rebase
            )

            if platform is None:
                private_config.add_cflags(GLOBAL_CFLAGS, condition=None)
                target.remove_configs(GLOBAL_REMOVED_CONFIGS, None)

            public_headers_dir = os.path.join("..", "Headers", "Public", self.pod.name)
            private_headers_dir = os.path.join(
                "..", "Headers", "Private", self.pod.name
            )
            private_header_mappings, public_header_mappings = self.collect_headers(
                platform
            )
            if private_header_mappings:
                private_config.add_include_dirs(private_headers_dir, condition=platform)

            private_config.add_include_dirs(
                os.path.dirname(public_headers_dir), condition=platform
            )

            if public_header_mappings:
                public_config.add_include_dirs(public_headers_dir, condition=platform)
                private_config.add_include_dirs(public_headers_dir, condition=platform)

        xcconfig = attrs.get("pod_target_xcconfig", {})
        if xcconfig:
            self.convert_xcconfig_for_platform(
                private_config, xcconfig, None, rebase=rebase
            )

        # FIXME(wangjianliang): find a correct way to fix these temporary solutions
        if name == "lottie-ios":
            private_config.add_include_dirs("../Headers/Private/lottie-ios/Lottie")
        if name == "Mantle":
            target.delete_deps(":Mantle_extobjc")
        if name == "MMKVCore":
            private_config.add_include_dirs("src/Core/crc32")
        if name == "EffectSDK_iOS_Core":
            private_config.delete_libs("src/libEffectSDK/lib/Release/libeffect-sdk.a")
            private_config.add_libs(
                "src/libEffectSDK/lib/Release/libeffect-sdk.a",
                condition='target_cpu == "arm" || target_cpu == "arm64"',
            )

        targets = list(self._targets.values())
        targets.sort(key=lambda t: t.name)
        return targets
