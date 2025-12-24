#!/usr/bin/env python3

# Copyright 2023 The Lynx Authors. All rights reserved.
# Licensed under the Apache License Version 2.0 that can be found in the
# LICENSE file in the root directory of this source tree.

import logging


def init(verbose=False, log_file=""):
    # Set up logging configuration
    if verbose:
        # Verbose mode
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s[%(levelname)s]%(message)s"
        )
    elif len(log_file) == 0:
        # Assuming that no file specified indicates local debug & non-verbose mode
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s[%(levelname)s]%(message)s"
        )
    else:
        # Saving to specified log file
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename=log_file,
            filemode="a",
        )


def d(message):
    logging.debug(message)


def i(message):
    logging.info(message)


def w(message):
    logging.warning(message)


def e(message):
    logging.error(message)


def exception(message):
    logging.exception(message)
