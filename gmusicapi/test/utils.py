#!/usr/bin/env python

# Copyright (c) 2012, Simon Weber
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of the contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Utilities used in testing."""

import numbers
import unittest
import random
import inspect
from getpass import getpass
import re

from ..api import Api, CallFailure
from ..protocol import WC_Protocol, Metadata_Expectations
from ..utils.apilogging import LogController
from ..utils import utils

md_expts = Metadata_Expectations.get_all_expectations()
log = LogController.get_logger("utils")

#A regex for the gm id format, eg:
#c293dd5a-9aa9-33c4-8b09-0c865b56ce46
hex_set = "[0-9a-f]"
gm_id_regex = re.compile(("{h}{{8}}-" +
                         ("{h}{{4}}-" * 3) +
                         "{h}{{12}}").format(h=hex_set))

def init():
    """Makes an instance of the unit-tested api and attempts to login with it.
    Returns the authenticated api.
    """

    api = UnitTestedApi()
    
    logged_in = False
    attempts = 0

    print "Warning: this test suite _might_ modify the library it is run on."

    while not logged_in and attempts < 3:
        email = raw_input("Email: ")
        password = getpass()

        logged_in = api.login(email, password)
        attempts += 1

    return api

def modify_md(md_name, val):
    """Returns a value of the same type as val that will not equal val."""

    #Check for metadata that must get specific values.
    if md_expts[md_name].allowed_values != None:
        #Assume old_val is a possible value, and return
        # the value one index after it.

        possible = md_expts[md_name].allowed_values
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
    a,b = zip(*lst)
    return is_id_list(a+b)

class enforced(object):
    """A callable that enforces the return of a function with a predicate."""
    def __init__(self, pred):
        self.pred = pred
    
    def __call__(self, f):
        def wrapped_f(*args, **kwargs):
            res = f(*args, **kwargs)
            if not self.pred(res): raise AssertionError #bad return format
            return res
        return wrapped_f

#Return information for most api member functions.
returns_id = ("change_playlist_name",
              "create_playlist",
              "delete_playlist",
              "copy_playlist",
              "change_playlist")

returns_id_list = ("change_song_metadata",
                   "delete_songs")

returns_songs = ("get_all_songs",
                 "get_playlist_songs")

returns_id_pairs = ("add_songs_to_playlist",
                    "remove_songs_from_playlist")
fname_to_pred = {}

for fnames, pred in ((returns_id, is_gm_id),
                     (returns_id_list, is_id_list),
                     (returns_songs, is_song_list),
                     (returns_id_pairs, is_id_pair_list)):
    for fname in fnames:
        fname_to_pred[fname] = pred

class UnitTestedApi(Api):
    """An Api, with most functions wrapped to assert a proper return."""



                         
    def __getattribute__(self, name):
        orig = object.__getattribute__(self, name)
        #Enforce any name in the lists above with the right pred.
        if name in fname_to_pred:
            return enforced(fname_to_pred[name])(orig)
        else:
            return orig
    

class BaseTest(unittest.TestCase):
    """Abstract class providing some useful features for testing the api."""

    @classmethod
    def setUpClass(cls):
        """Init and log in to an api, then get the library and playlists."""

        cls.api = init()
    
        if not cls.api.is_authenticated():
            raise session.NotLoggedIn
        
        #These are assumed to succeed, but errors here will prevent further testing.
        cls.library = cls.api.get_all_songs()

        #I can't think of a way to test auto playlists and instant mixes.
        cls.playlists = cls.api.get_all_playlist_ids(always_id_lists=True)['user']


    @classmethod
    def tearDownClass(cls):
        """Log out of the api."""

        cls.api.logout()


    def setUp(self):
        """Get a random song id."""

        #This will fail if we have no songs.
        self.r_song_id = random.choice(self.library)['id']

    #---
    #   Utility functions:
    #---

    def collect_steps(self, prefix):
        """Yields the steps of a monolithic test in name-sorted order."""

        methods = inspect.getmembers(self, predicate=inspect.ismethod)
        
        #Sort functions based on name.
        for name, func in sorted(methods, key=lambda m: m[0]):
            if name.startswith(prefix):
                yield name, func

    def run_steps(self, prefix):
        """Run the steps defined by this prefix in order."""

        for name, step in self.collect_steps(prefix):
            try:
                step()

            #Only catch exceptions raised from _our_ test code.
            #Other kinds of exceptions may be raised inside the code
            # being tested; those should be re-raised so we can trace them.
            except CallFailure as f:
                raise self.fail("test {} step {} call to {} failure: {}".format(prefix, step, f.name, f.res))
            except AssertionError as e:
                raise #it's actually easiest to just reraise this, so we can track down what went wrong
