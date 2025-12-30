#!/usr/bin/env python3

import logging


def init(verbose=False, log_file=""):
    # Set up logging configuration
    if verbose:
        # Verbose mode
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s[%(levelname)s]%(message)s"
        )
