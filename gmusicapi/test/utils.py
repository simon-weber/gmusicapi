#!/usr/bin/env python

#Copyright 2012 Simon Weber.

#This file is part of gmusicapi - the Unofficial Google Music API.

#Gmapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmapi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with gmusicapi.  If not, see <http://www.gnu.org/licenses/>.

"""Utilities used in testing."""

import numbers
import unittest
import random
import inspect
from getpass import getpass

from gmusicapi.api import Api
from gmusicapi.protocol import WC_Protocol


#Metadata expectations:
limited_md = WC_Protocol.modifyentries.limited_md #should refactor this
mutable_md = WC_Protocol.modifyentries.mutable_md
frozen_md = WC_Protocol.modifyentries.frozen_md
dependent_md = WC_Protocol.modifyentries.dependent_md
server_md = WC_Protocol.modifyentries.server_md

def init():
    """Makes an instance of the api and attempts to login with it.
    Returns the authenticated api.
    """

    api = Api()
    
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
    if md_name in limited_md:
        #Assume old_val is a possible value, and return
        # the value one index after it.

        possible = limited_md[md_name]
        val_i = possible.index(val)
        return possible[(val_i + 1) % len(possible)]

    #Generic handlers for other data types.
    if isinstance(val, basestring):
        return val + "_mod"

    #Need to check for bool first, bools are instances of Number
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
    

def call_succeeded(response):
    """Returns True if the call succeeded, False otherwise."""
    
    #Failed responses always have a success=False key.
    #Some successful responses do not have a success=True key, however.

    #print response

    if 'success' in response.keys():
        return response['success']
    else:
        return True


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
        cls.playlists = cls.api.get_playlists()['user']


    @classmethod
    def tearDownClass(cls):
        """Log out of the api."""

        cls.api.logout()


    def setUp(self):
        """Get a random song id."""

        #This will fail is we have no songs.
        self.r_song_id = random.choice(self.library)['id']

    #---
    #   Utility functions:
    #---

    def assert_success(self, response):
        """Asserts the success of a call's response.
        Returns the calls response."""

        self.assertTrue(call_succeeded(response))
        return response

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
            except Exception as e:
                self.fail("{} failed ({}: {})".format(step, type(e), e))
