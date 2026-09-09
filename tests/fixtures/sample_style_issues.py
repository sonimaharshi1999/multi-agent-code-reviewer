# Multi-Agent Code Review System -- Test Fixture
# Author: Maharshi Soni | License: MIT
"""Synthetic code with style and convention issues."""

import os
import json
import sys  # unused


class my_class:
    """lowercase class name (should be PascalCase)."""
    pass


class AnotherClass:
    pass


def MyFunction(x, y):
    """CamelCase function name (should be snake_case)."""
    return x + y


def undocumented_public_function(data):
    return data


def function_without_return_type(x):
    """Has a docstring but no return type hint."""
    return x * 2


def bare_except_example():
    """Uses a bare except clause."""
    try:
        result = 1 / 0
    except:
        result = None
    return result


# TODO: Fix this function later
# FIXME: This is broken
# HACK: Temporary workaround
def hacky_function():
    return 42


def a_very_long_line_function():
    this_is_a_really_long_variable_name = "and this is a really long string value that makes this line exceed any reasonable line length limit for code readability"
    return this_is_a_really_long_variable_name
