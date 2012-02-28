#!/usr/bin/env python

"""Utility functions used across api code."""

import string
import re

try:
    from decorator import decorator
except ImportError:
    # No decorator package available. Create a no-op "decorator".
    def decorator(f):
        return f


def to_camel_case(s):
    """Given a sring in underscore form, returns a copy of it in camel case.
    eg, camel_case('test_string') => 'TestString'. """

    ret = string.upper(s[0]) + s[1:]

    ul = re.findall("(_.)", s[1:]) #underscore, then letter

    for to_rep in ul:
        #replace _j with J
        ret = ret.replace(to_rep, string.upper(to_rep[1]))

    return ret

def accept_singleton(expected_type, position=1):
    """Allows a function expecting a list to accept a single item as well.
    The item will be wrapped in a list.
    Will not work for nested lists.

    :param expected_type: the type of the items in the list
    :param position: (optional) the position of the expected list - defaults to 1.
    """

    @decorator
    def wrapper(function, *args, **kw):
        
        if isinstance(args[position], expected_type):
            #args are a tuple, can't assign into them
            args = list(args)
            args[position] = [args[position]]
            args = tuple(args)

        return function(*args, **kw)

    return wrapper
