#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utilities used in testing."""

from glob import glob
import logging
import numbers
import os
import re
import string
import sys

from gmusicapi.api import Api
from gmusicapi.protocol.metadata import md_expectations

log = logging.getLogger(__name__)

#A regex for the gm id format, eg:
#c293dd5a-9aa9-33c4-8b09-0c865b56ce46
hex_set = "[0-9a-f]"
gm_id_regex = re.compile(("{h}{{8}}-" +
                         ("{h}{{4}}-" * 3) +
                         "{h}{{12}}").format(h=hex_set))

#Test files are located in the same directory as this file.
cwd = os.getcwd()
os.chdir(os.path.dirname(sys.argv[0]))

audio_filenames = glob(u'audiotest*')
mp3_filenames = [fn for fn in audio_filenames if fn.endswith('.mp3')]
small_mp3 = u'audiotest_small.mp3'
image_filename = 'imagetest_10x10_check.png'

os.chdir(cwd)

#Get the full path of the test files.
#Can't use abspath since this is relative to where _this_ file is,
# not necessarily the calling curdir.
path = os.path.realpath(__file__)
real_path = lambda lp: path[:string.rfind(path, os.sep)] + os.sep + lp

mp3_filenames = map(real_path, mp3_filenames)
audio_filenames = map(real_path, audio_filenames)
image_filename = real_path(image_filename)
small_mp3 = real_path(small_mp3)


class NoticeLogging(logging.Handler):
    """A log handler that, if asked to emit, will set
    ``self.seen_message`` to True.
    """

    def __init__(self):
        logging.Handler.__init__(self)  # cannot use super in py 2.6; logging is still old-style
        self.seen_message = False

    def emit(self, record):
        self.seen_message = True


def new_test_api(**kwargs):
    """Make an instance of an Api, login and return it.

    kwargs are passed through to api.login().
    """

    api = Api(debug_logging=True)
    api.login(**kwargs)

    return api


def modify_md(md_name, val):
    """Returns a value of the same type as val that will not equal val."""

    #Check for metadata that must get specific values.
    if md_expectations[md_name].allowed_values is not None:
        #Assume old_val is a possible value, and return
        # the value one modulus index after it.

        possible = md_expectations[md_name].allowed_values
        val_i = 0
        try:
            val_i = possible.index(val)
        except ValueError:
            log.warning("non-allowed metadata value '%s' for key %s", val, md_name)

        return possible[(val_i + 1) % len(possible)]

    #Generic handlers for other data types.
    if isinstance(val, basestring):
        return val + "_mod"

    #Need to check for bool first, bools are instances of Number for some reason.
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
    #Not really precise, but should be good enough.
    return is_gm_id(d["id"])


def is_song_list(lst):
    return all(map(is_song, lst))


def is_id_list(lst):
    """Returns True if the given list is made up of all strings in GM id form."""
    return all(map(is_gm_id, lst))


def is_id_pair_list(lst):
    """Returns True if the given list is made up of all (id, id) pairs."""
    a, b = zip(*lst)
    return is_id_list(a+b)
