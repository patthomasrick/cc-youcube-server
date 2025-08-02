#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Colors using ANSI escape codes
https://en.wikipedia.org/wiki/ANSI_escape_code
"""


class Foreground:
    """
    [3-bit and 4-bit](https://en.wikipedia.org/wiki/ANSI_escape_code#3-bit_and_4-bit)
    """

    BLACK: str = "\033[30m"
    RED: str = "\033[31m"
    GREEN: str = "\033[32m"
    YELLOW: str = "\033[33m"
    BLUE: str = "\033[34m"
    MAGENTA: str = "\033[35m"
    CYAN: str = "\033[36m"
    WHITE: str = "\033[37m"

    BRIGHT_BLACK: str = "\033[90m"
    BRIGHT_RED: str = "\033[91m"
    BRIGHT_GREEN: str = "\033[92m"
    BRIGHT_YELLOW: str = "\033[93m"
    BRIGHT_BLUE: str = "\033[94m"
    BRIGHT_MAGENTA: str = "\033[95m"
    BRIGHT_CYAN: str = "\033[96m"
    BRIGHT_WHITE: str = "\033[97m"

    DEFAULT: str = "\033[39m"


RESET: str = "\033[m"
