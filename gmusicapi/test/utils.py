# -*- coding: utf-8 -*-

"""Utilities used in testing."""

import logging
import numbers
import os
import re


# from gmusicapi.api import Api
from gmusicapi.protocol.metadata import md_expectations
from gmusicapi.utils import utils

log = utils.DynamicClientLogger(__name__)


# A regex for the gm id format, eg:
# c293dd5a-9aa9-33c4-8b09-0c865b56ce46
hex_set = "[0-9a-f]"
gm_id_regex = re.compile(("{h}{{8}}-" +
                         ("{h}{{4}}-" * 3) +
                         "{h}{{12}}").format(h=hex_set))

# Get the absolute paths of the test files, which are located in the same
# directory as this file.
test_file_dir = os.path.dirname(os.path.abspath(__file__))

small_mp3 = os.path.join(test_file_dir, u'audiotest_small.mp3')
image_filename = os.path.join(test_file_dir, u'imagetest_10x10_check.png')

# that dumb intro track on conspiracy of one
aa_song_id = 'Tqqufr34tuqojlvkolsrwdwx7pe'


class NoticeLogging(logging.Handler):
    """A log handler that, if asked to emit, will set
    ``self.seen_message`` to True.
    """

    def __init__(self):
        logging.Handler.__init__(self)  # cannot use super in py 2.6; logging is still old-style
        self.seen_message = False

    def emit(self, record):
        self.seen_message = True


def new_test_client(cls, **kwargs):
    """Make an instance of a client, login, and return it.

    kwargs are passed through to cls.login().
    """

    client = cls(debug_logging=True)
    client.login(**kwargs)

    return client


def modify_md(md_name, val):
    """Returns a value of the same type as val that will not equal val."""

    # Check for metadata that must get specific values.
    if md_expectations[md_name].allowed_values is not None:
        # Assume old_val is a possible value, and return
        # the value one modulus index after it.

        possible = md_expectations[md_name].allowed_values
        val_i = 0
        try:
            val_i = possible.index(val)
        except ValueError:
            log.warning("non-allowed metadata value '%s' for key %s", val, md_name)

        return possible[(val_i + 1) % len(possible)]

    # Generic handlers for other data types.
    if isinstance(val, basestring):
        return val + "_mod"

    # Need to check for bool first, bools are instances of Number for some reason.
    elif isinstance(val, bool):
        return not val
    elif isinstance(val, numbers.Number):
        return val + 1
    else:
        raise TypeError("modify expects only strings, numbers, and bools")


def md_entry_same(entry_name, s1, s2):
    """Returns (s1 and s2 have the same value for entry_name?, message)."""

    s1_val = s1[entry_name]
    s2_val = s2[entry_name]

    return (s1_val == s2_val, "(" + entry_name + ") " + repr(s1_val) + ", " + repr(s2_val))


def is_gm_id(s):
    """Returns True if the given string is in Google Music id form."""
    return re.match(gm_id_regex, s) is not None


def is_song(d):
    """Returns True is the given dict is a GM song dict."""
    # Not really precise, but should be good enough.
    return is_gm_id(d["id"])


def is_song_list(lst):
    return all(map(is_song, lst))


def is_id_list(lst):
    """Returns True if the given list is made up of all strings in GM id form."""
    return all(map(is_gm_id, lst))


def is_id_pair_list(lst):
    """Returns True if the given list is made up of all (id, id) pairs."""
    a, b = zip(*lst)
    return is_id_list(a + b)
