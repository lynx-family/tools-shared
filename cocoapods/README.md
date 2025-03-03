# Introduction

This directory contains a simple python library used to convert 
the podspec files of Cocoapods dependencies to GN build files.
The implement detail of the library refers to the open source
 code of the official Cocoapods project from 
https://github.com/CocoaPods/CocoaPods

For a common usage, the library takes a Podfile.lock file generated 
by the ```pod install``` command as input and generates BUILD.gn files
for each dependency appears in the Podfile.lock file.

# How to use

Steps to generate a BUILD.gn files from a Podfile.lock:

1. Create a PodfileLock instance
```python
import os
import tempfile
from cocoapods.podfile_lock import PodfileLock

cache_dir = os.path.join(tempfile.gettempdir(), 'pods_to_gn')
podfile_lock = PodfileLock.load_from_file("path/to/Podfile.lock", cache_dir)
```
2. Iterate all Pod objects creates by the PodfileLock instance 
and download the source files for each pod
```python
for name, pod in podfile_lock.pods.items():
    target_dir = os.path.join(sandbox, name, 'src')
    package_files = pod.download(target_dir, cache_dir, False)
```
3. Convert specs of each pod to BUILD.gn files
```python
root_dir = "root/directory/of/the/gn/build/system"

for spec in pod.spec.all_specs():
    gn_dir = os.path.dirname(spec.pod.target_dir)
    gn_file = os.path.join(gn_dir, 'BUILD.gn')

    targets = spec.convert_to("gn", root_dir=root_dir, rebase=gn_dir)
    with open(gn_file, 'a+') as f:
        targets = spec.convert_to("gn", root_dir=root_dir, rebase=gn_dir)
        for target in targets:
            f.write(str(target))

```

# Source Structure
```shell
cocoapods
├── README.md  # this file
├── __init__.py
├── attr_types.py  # classes of attribute types used to distinct
  # with the default string expression
├── downloaders  # downloaders are used for fetching source files of pods
│ ├── __init__.py
│ ├── downloader.py  # the base class of all downloaders
│ ├── external_downloader.py  # downloader to handle local source, it will
  # not actually download anything but only create symlinks for required
  # files
│ ├── git_downloader.py  # a downloader used to fetch source files from
  # remote git repository
│ └── http_downloader.py  # a downloader used to fetch source files
  # from CDN vie http protocol
├── files_accessor.py  # a helper class used to glob files for attributes
  # defined in podspec file
├── pod.py  # the data model used to store the information of pod
├── podfile_lock.py  # class for loading a Podfile.lock file
├── precompiled_header.py  # class used to generate precompiled header file
├── sources.py  # class for podspec source repository
├── specification.py  # the data model for specs defined in podspec files
├── targets
│ ├── __init__.py
│ └── gn
│     ├── __init__.py
│     ├── base_target.py  # base class of all GN target definitions, which
  # contains most of the serializing logic for GN
│     ├── config.py  # the config target for GN
│     ├── group.py  # the group target for GN
│     └── utils.py  # some util functions associated to GN serializing
└── utils.py  # common util functions
```
