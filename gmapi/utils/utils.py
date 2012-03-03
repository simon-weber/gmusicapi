#!/usr/bin/env python

#Copyright 2012 Simon Weber.

#This file is part of gmapi - the Unofficial Google Music API.

#Gmapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmapi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with gmapi.  If not, see <http://www.gnu.org/licenses/>.

"""Utility functions used across api code."""

import string
import re
from htmlentitydefs import name2codepoint

#From https://github.com/six8/python-clom/blob/97e20517886e595cce7d498136e8a1242d6adcad/src/clom/command.py
try:
    from decorator import decorator
except ImportError:
    # No decorator package available, copy docstrings manually.
    def decorator(f):
        def decorate(_func):
            def inner(*args, **kwargs):
                return f(_func, *args, **kwargs)
            
            inner.__doc__ = _func.__doc__
            inner.__repr__ = _func.__repr__

            return inner
        
        return decorate

def to_camel_case(s):
    """Given a sring in underscore form, returns a copy of it in camel case.
    eg, camel_case('test_string') => 'TestString'. """
    return ''.join(map(lambda x: x.title(), s.split('_')))

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


#From http://stackoverflow.com/questions/275174/how-do-i-perform-html-decoding-encoding-using-python-django

name2codepoint['#39'] = 39
def unescape_html(s):
    "unescape HTML code refs; c.f. http://wiki.python.org/moin/EscapingHtml"
    return re.sub('&(%s);' % '|'.join(name2codepoint),
              lambda m: unichr(name2codepoint[m.group(1)]), s)
