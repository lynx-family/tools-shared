#!/bin/bash
# Copyright 2024 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.
# This is a template for the envsetup.sh file, used to download a specific version of lcm_tools
# in a specific repository. Any repository that needs to specify a specific lcm_tools version
# can copy this template to the repository, and then prompt developers to execute this script
# using the source command before using lcm_tools.

# Modify the variable below to select a specific version
LCM_TOOLS_REVISION=latest

LCM_TOOLS_REPO_URL=

# set default LCM_TOOLS_HOME 
if [[ -z "$LCM_TOOLS_HOME" ]]; then
    LCM_TOOLS_HOME=$HOME/.lcm_tools
fi

if [ ! -d "$LCM_TOOLS_HOME" ]; then
  git clone $LCM_TOOLS_REPO_URL "$LCM_TOOLS_HOME"
elif [ ! -d "$LCM_TOOLS_HOME/.git" ]; then
  echo "Error: LCM Tools directory $LCM_TOOLS_HOME not empty, Please delete it first."
  exit 1
else
  pushd "$LCM_TOOLS_HOME" > /dev/null || exit
  if ! git status -uno > /dev/null; then
    git reset --hard
    git clean -fdx
  fi
  
  if [[ $LCM_TOOLS_REVISION = "latest" ]]; then
    git checkout --quiet --force master > /dev/null && git pull > /dev/null
  else
    git fetch --force --progress --update-head-ok -- $LCM_TOOLS_REPO_URL $LCM_TOOLS_REVISION
    git checkout FETCH_HEAD --quiet
  fi
  popd > /dev/null || exit
fi

export LCM_AUTO_UPDATE=0
source "$LCM_TOOLS_HOME"/envsetup.sh "$@"
