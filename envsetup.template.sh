#!/bin/bash
# Copyright 2025 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

# This is a template for the envsetup.sh file, used to download a specific version of tools_shared
# in a specific repository. Any repository that needs to specify a specific tools_shared version
# can copy this template to the repository, and then prompt developers to execute this script
# using the source command before using tools_shared.

# Modify the variable below to select a specific version
TOOLS_SHARED_REVISION=latest

TOOLS_SHARED_REPO_URL=git@github.com:lynx-family/tools-shared.git

# set default TOOLS_SHARED_HOME 
if [[ -z "$TOOLS_SHARED_HOME" ]]; then
    TOOLS_SHARED_HOME=$HOME/.tools_shared
fi

if [ ! -d "$TOOLS_SHARED_HOME" ]; then
  git clone $TOOLS_SHARED_REPO_URL "$TOOLS_SHARED_HOME"
elif [ ! -d "$TOOLS_SHARED_HOME/.git" ]; then
  echo "Error: Tools Shared directory $TOOLS_SHARED_HOME not empty, Please delete it first."
  exit 1
else
  pushd "$TOOLS_SHARED_HOME" > /dev/null || exit
  if ! git status -uno > /dev/null; then
    git reset --hard
    git clean -fdx
  fi
  
  if [[ $TOOLS_SHARED_REVISION = "latest" ]]; then
    git checkout --quiet --force master > /dev/null && git pull > /dev/null
  else
    git fetch --force --progress --update-head-ok -- $TOOLS_SHARED_REPO_URL $TOOLS_SHARED_REVISION
    git checkout FETCH_HEAD --quiet
  fi
  popd > /dev/null || exit
fi

source "$TOOLS_SHARED_HOME"/envsetup.sh "$@"
