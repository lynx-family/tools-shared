#!/usr/bin/env python3
# Copyright 2020 The Lynx Authors. All rights reserved.
"""
This script check whether android LynxExample demo can be built.
return 0 iff android demo can be built.
"""

import os
import subprocess
import sys


def CheckAndroidBuild():
    print("Starting checking if Android LynxExample can be built.")

    os.chdir(os.getcwd() + "/Android")
