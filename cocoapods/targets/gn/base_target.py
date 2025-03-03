#!/usr/bin/env python3
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import functools

from typing import Iterable

from cocoapods.attr_types import Rebase

TAB_WIDTH = 4


def serialize_bool(value):
    return "true" if value else "false"


def serialize_string(value):
    return f'"{value}"'


def serialize_rebase(value):
    return f'rebase_path("{value.path}", {value.base})'


def serialize_tuple(values):
    return ", ".join([SERIALIZERS[type(value)](value) for value in values])


SERIALIZERS = {
    bool: serialize_bool,
    str: serialize_string,
    Rebase: serialize_rebase,
    tuple: serialize_tuple,
}


def add_or_update_to_set(s, v):
    if isinstance(v, list):
        s.update(v)
    else:
        s.add(v)


class BaseTarget:
    type = "source_set"
    value_fields = ["output_name", "output_extension", "output_prefix_override"]
    list_fields = [
        "sources",
        "include_dirs",
        "frameworks",
        "framework_dirs",
        "deps",
        "cflags",
        "cflags_cc",
        "cflags_objc",
        "cflags_objcc",
        "ldflags",
        "libs",
        "lib_dirs",
        "public_configs",
        "defines",
        "configs",
        "outputs",
        "public_deps",
    ]

    def __init__(self, name=None):
        self.name = name
        self.output_name = None

        self._list_attrs = {}
        self._removed_list_attrs = {}
        self._condition_list_attrs = {}
        self._removed_condition_list_attrs = {}

        for field in self.value_fields:
            self._list_attrs[field] = None
            setattr(self, f"set_{field}", functools.partial(self.set_field, field))

        for field in self.list_fields:
            self._list_attrs[field] = set()
            setattr(self, f"add_{field}", functools.partial(self.add_to_field, field))
            setattr(
                self,
                f"delete_{field}",
                functools.partial(self.delete_from_field, field),
            )
        for field in self.list_fields:
            self._removed_list_attrs[field] = set()
            setattr(
                self,
                f"remove_{field}",
                functools.partial(self.remove_from_field, field),
            )

    def __getattr__(self, item):
        if item.startswith("__"):
            return super().__getattr__(item)
        try:
            return self._list_attrs[item]
        except KeyError:
            raise AttributeError(f"attribute {item} not found")

    def serialize_value(self, name, value, ident=0):
        s = ""
        s += f'{" " * ident}{name} = {SERIALIZERS[type(value)](value)}'
        return s

    def serialize_list(self, name, li, ident=0, append=False, remove=False):
        op = "+" if not remove else "-"
        s = ""
        s += f'{" " * ident}{name} {op if append or (name == "configs" and self.type != "group") else ""}= ['
        ident += TAB_WIDTH
        li = [SERIALIZERS[type(i)](i) for i in li if i is not None]
        li.sort()
        for i in li:
            s += f'\n{" " * ident}{i},'
        ident -= TAB_WIDTH
        if li:
            s += f'\n{" " * ident}]'
        else:
            s += "]"
        return s

    def serialize_list_fields(
        self, list_attrs, ident=0, existing_fields=[], remove=False
    ):
        s = ""
        for field, values in list_attrs.items():
            if isinstance(values, Iterable) and not isinstance(values, str):
                if not values:
                    continue
                s += "\n"
                s += self.serialize_list(
                    field,
                    values,
                    ident,
                    append=(field in existing_fields),
                    remove=remove,
                )
            elif values is not None:
                s += self.serialize_value(field, values, ident)
                s += "\n"
            existing_fields.append(field)
        return s

    def set_field(self, field, value, condition=None):
        if field not in self.value_fields:
            raise Exception(f"unknown value field {field}")
        if condition:
            item = self._condition_list_attrs.setdefault(condition, {})
            item[field] = value
        else:
            self._list_attrs[field] = value

    # TODO(wangjianliang): combine following 2 functions
    def add_to_field(self, field, value, condition=None):
        if field not in self.list_fields:
            raise Exception(f"unknown field {field}")

        if condition:
            item = self._condition_list_attrs.setdefault(condition, {})
            attrs = item.setdefault(field, set())
            if isinstance(value, list):
                value = [v for v in value if v not in self._list_attrs[field]]
            elif value in self._list_attrs[field]:
                return
            add_or_update_to_set(attrs, value)
        else:
            add_or_update_to_set(self._list_attrs[field], value)

    def remove_from_field(self, field, value, condition=None):
        if field not in self.list_fields:
            raise Exception(f"unknown field {field}")

        if condition:
            item = self._removed_condition_list_attrs.setdefault(condition, {})
            attrs = item.setdefault(field, set())
            if isinstance(value, list):
                value = [v for v in value if v not in self._removed_list_attrs[field]]
            elif value in self._removed_list_attrs[field]:
                return
            add_or_update_to_set(attrs, value)
        else:
            add_or_update_to_set(self._removed_list_attrs[field], value)

    def delete_from_field(self, field, value, condition=None):
        if field not in self.list_fields:
            raise Exception(f"unknown field {field}")

        if condition:
            item = self._condition_list_attrs.get(condition)
            attrs = item.get(field)
            if isinstance(value, list):
                for v in value:
                    attrs.remove(v)
            elif value in attrs:
                attrs.remove(value)
        else:
            self._list_attrs[field].remove(value)

    def __str__(self):
        ident = 0
        s = ""
        s += f'{self.type}("{self.name}") {{'

        serialized_fields = []
        serialized_removed_fields = []

        ident += TAB_WIDTH
        s += self.serialize_list_fields(self._list_attrs, ident, serialized_fields)
        s += self.serialize_list_fields(
            self._removed_list_attrs, ident, serialized_removed_fields, remove=True
        )

        ident -= TAB_WIDTH

        ident += TAB_WIDTH
        for condition, list_attrs in self._condition_list_attrs.items():
            # convert "osx" to "mac" to get compatible with the declared args in build framework
            if condition == "osx":
                condition = "is_mac"
            elif condition == "ios":
                condition = "is_ios"

            s += "\n\n"
            s += f'{" " * ident}if ({condition}) {{'
            ident += TAB_WIDTH
            s += self.serialize_list_fields(list_attrs, ident, serialized_fields)
            s += "\n"
            ident -= TAB_WIDTH
            s += f'{" " * ident}}}'
        ident -= TAB_WIDTH

        s += f'\n{" " * ident}}}\n\n'
        return s
