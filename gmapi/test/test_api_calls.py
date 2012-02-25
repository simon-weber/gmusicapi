#!/usr/bin/env python

"""A test harness for api features."""


import unittest
import random
import inspect
import os
import string
import numbers
import copy
import time
from getpass import getpass

from gmapi.api import Api
from gmapi.protocol import WC_Protocol
from gmapi import session
from gmapi.utils.apilogging import LogController


#Expected to be in this directory.
test_filename = "test.mp3"

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
    

class TestWCApiCalls(unittest.TestCase):
    """Runs integration tests for api calls.
    Tests are intended not to modify the library, but no guarantees are made.
    """

    @classmethod
    def setUpClass(cls):
        """Init and log in to an api, then get the library and playlists."""

        cls.log = LogController().get_logger("gmapi.test.TestWcApiCalls")

        #Get the full path of the test file.
        path = os.path.realpath(__file__)
        cls.test_filename = path[:string.rfind(path, r'/')] + r'/' + test_filename

        cls.api = init()
    
        if not cls.api.is_authenticated():
            raise session.NotLoggedIn
        
        #These are assumed to succeed, but errors here will prevent further testing.
        cls.library = cls.api.get_all_songs()
        cls.playlists = cls.api.get_playlists()


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


    #---
    #   Monolithic tests: 
    #   (messy, but less likely to destructively modify the library)
    #   Modified from http://stackoverflow.com/questions/5387299/python-unittest-testcase-execution-order
    #---
        
    def pl_1_create(self):
        """Create a playlist."""
        self.assert_success(
            self.api.create_playlist('test playlist'))

        #Need to reload playlists so it appears.
        self.playlists = self.api.get_playlists()


    def pl_2_add_song(self):
        """Add a random song to the playlist."""
        self.assert_success(
            self.api.add_songs_to_playlist(self.playlists['test playlist'], self.r_song_id))

        #Verify the playlist has it.
        tracks = self.api.get_playlist_songs(self.playlists['test playlist'])

        self.assertTrue(tracks[0]["id"] == self.r_song_id)
        

    def pl_2a_remove_song(self):
        """Remove a song from the playlist."""

        sid = self.api.get_playlist_songs(self.playlists['test playlist'])[0]["id"]
        
        self.assert_success(
            self.api.remove_song_from_playlist(sid, self.playlists['test playlist']))

        #Verify.
        tracks = self.api.get_playlist_songs(self.playlists['test playlist'])

        self.assertTrue(len(tracks) == 0)

    def pl_3_change_name(self):
        """Change the playlist's name."""
        self.assert_success(
            self.api.change_playlist_name(self.playlists['test playlist'], 'modified playlist'))

        self.playlists = self.api.get_playlists()
            
    def pl_4_delete(self):
        """Delete the playlist."""
        self.assert_success(
            self.api.delete_playlist(self.playlists['modified playlist']))

        self.playlists = self.api.get_playlists()


    def test_playlists(self):
        self.run_steps("pl")


    def updel_1_upload(self):
        """Upload the test file."""
        self.uploaded_id = self.api.upload(self.test_filename)[self.test_filename]

    def updel_2_delete(self):
        """Delete the uploaded test file."""
        self.assert_success(
            self.api.delete_song(self.uploaded_id))

        del self.uploaded_id

    def test_up_deletion(self):
        self.run_steps("updel_")

        

    #---
    #   Non-monolithic tests:
    #---

    #Works, but the protocol isn't mature enough to support the call (yet).
    # def test_get_song_download_info(self):
    #     #The api doesn't expose the actual response here,
    #     # instead we expect a tuple with 2 entries.
    #     res = self.api.get_song_download_info(self.r_song_id)
    #     self.assertTrue(len(res) == 2 and isinstance(res, tuple))
            

    def test_change_song_metadata(self):
        """Change a song's metadata, then restore it."""
        #Get a random song's metadata.
        orig_md = [s for s in self.library if s["id"] == self.r_song_id][0]
        self.log.debug("original md: %s", repr(orig_md))

        #Generate noticably changed metadata for ones we can change.
        new_md = copy.deepcopy(orig_md)
        for key in mutable_md:
            if key in orig_md:
                old_val = orig_md[key]
                new_val = modify_md(key, old_val)

                self.log.debug("%s: %s modified to %s", key, repr(old_val), repr(new_val))
                self.assertTrue(new_val != old_val)
                new_md[key] = new_val
                            
        
        #Make the call to change the metadata.
        #This should succeed, even though we _shouldn't_ be able to change some entries.
        #The call only fails if you give the wrong datatype.
        self.assert_success(
            self.api.change_song_metadata(new_md))

        #Refresh the library to flush the changes, then find the song.
        #Assume the id won't change (testing has shown this to be true).
        time.sleep(3)
        self.library = self.api.get_all_songs()
        server_md = [s for s in self.library if s["id"] == orig_md["id"]][0]
        
        self.log.debug("server md: %s", repr(server_md))

        #Verify everything went as expected:
        # things that should change did
        for md_name in mutable_md:
            if md_name in orig_md: #some songs are missing entries (eg albumArtUrl)
                truth, message = md_entry_same(md_name, orig_md, server_md)
                self.assertTrue(not truth, "should not equal " + message)

        # things that shouldn't change didn't
        for md_name in frozen_md:
            if md_name in orig_md:
                truth, message = md_entry_same(md_name, orig_md, server_md)
                self.assertTrue(truth, "should equal " + message)

        #Recreate the dependent md to what they should be (based on how orig_md was changed)
        correct_dependent_md = {}
        for dep_key in dependent_md:
            if dep_key in orig_md:
                master_key, trans = dependent_md[dep_key]
                correct_dependent_md[dep_key] = trans(new_md[master_key])
                self.log.debug("dependents (%s): %s -> %s", dep_key, new_md[master_key], correct_dependent_md[dep_key])

        #Make sure dependent md is correct.
        for dep_key in correct_dependent_md:
            truth, message = md_entry_same(dep_key, correct_dependent_md, server_md)
            self.assertTrue(truth, "should equal: " + message)

            
        #Revert the metadata.
        self.assert_success(
            self.api.change_song_metadata(orig_md))

        #Verify everything is as it was.
        time.sleep(3)
        self.library = self.api.get_all_songs()
        server_md = [s for s in self.library if s["id"] == orig_md["id"]][0]

        self.log.debug("server md: %s", repr(server_md))

        for md_name in orig_md:
            if md_name not in server_md: #server md _can_ change
                truth, message = md_entry_same(md_name, orig_md, server_md)
                self.assertTrue(truth, "should equal: " + message)
        

    def test_search(self):
        self.assert_success(
            self.api.search('e'))

    def test_get_stream_url(self):
        #This should return a valid url.
        #This is not robust; it's assumed that invalid calls will raise an error before this point.
        url = self.api.get_stream_url(self.r_song_id)
        self.assertTrue(url[:4] == "http")
        

if __name__ == '__main__':
    unittest.main()
