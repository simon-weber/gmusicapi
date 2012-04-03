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

"""A test harness for checking that api calls mutate the server
in the expected fashion. Unit testing is also performed.

A successful test run should not appear to mutate the library
when it is finished, but no guarantees are made."""


import unittest
import os
import string
import copy
import time
import random

from ..protocol import WC_Protocol, Metadata_Expectations
from ..utils.apilogging import UsesLog
from ..test import utils as test_utils

#Expected to be in this directory.
test_filenames = ("test.mp3", "test.flac", "test.m4a", "test.ogg", "test.wma")

class TestWCApiCalls(test_utils.BaseTest, UsesLog):

    @classmethod
    def setUpClass(cls):
        super(TestWCApiCalls, cls).setUpClass()

        cls.init_class_logger()

        #Get the full path of the test files.
        #Can't use abspath since this is relative to where _this_ file is,
        # not necessarily the calling curdir.
        path = os.path.realpath(__file__)
        real_path = lambda lp: path[:string.rfind(path, os.sep)] + os.sep + lp
        cls.test_filenames = map(real_path, test_filenames)

    #---
    #   Monolithic tests: 
    #   (messy, but less likely to destructively modify the library)
    #   Modified from http://stackoverflow.com/questions/5387299/python-unittest-testcase-execution-order
    #---
        
    def pl_1_create(self):
        """Create a playlist."""
        self.api.create_playlist('test playlist')

        #Need to reload playlists so it appears.
        self.playlists = self.api.get_all_playlist_ids(always_id_lists=True)['user']


    def pl_2_add_song(self):
        """Add a random song to the playlist."""
        p_id = self.playlists['test playlist'][-1]

        self.api.add_songs_to_playlist(p_id, self.r_song_id)

        #Verify the playlist has it.
        tracks = self.api.get_playlist_songs(p_id)

        self.assertTrue(tracks[0]["id"] == self.r_song_id)
        

    def pl_2a_remove_song(self):
        """Remove a song from the playlist."""
        p_id = self.playlists['test playlist'][-1]

        sid = self.api.get_playlist_songs(p_id)[0]["id"]
        
        self.api.remove_songs_from_playlist(p_id, sid)

        #Verify.
        tracks = self.api.get_playlist_songs(p_id)

        self.assertTrue(len(tracks) == 0)

    def pl_3_change_name(self):
        """Change the playlist's name."""
        p_id = self.playlists['test playlist'][-1]

        self.api.change_playlist_name(p_id, 'modified playlist')

        self.playlists = self.api.get_all_playlist_ids(always_id_lists=True)['user']
            
    def pl_4_delete(self):
        """Delete the playlist."""
        self.api.delete_playlist(self.playlists['modified playlist'][-1])

        self.playlists = self.api.get_all_playlist_ids(always_id_lists=True)['user']


    def test_playlists(self):
        self.run_steps("pl")
        
    def cpl_1_create(self):
        """Create and populate a random playlist."""
        self.api.create_playlist('playlist to change')

        #Need to reload playlists so it appears.
        self.playlists = self.api.get_all_playlist_ids(always_id_lists=True)['user']

        p_id = self.playlists['playlist to change'][-1]

        self.api.add_songs_to_playlist(p_id, [s["id"] for s in random.sample(self.library, 10)])
                
    def cpl_2_change(self):
        """Change the playlist with random deletions, additions and reordering."""
        p_id = self.playlists['playlist to change'][-1]
        tracks = self.api.get_playlist_songs(p_id)

        #Apply random modifications.
        delete, add_dupe, add_blank, reorder = [random.choice([True, False]) for i in xrange(4)]

        if tracks and delete:
            self.log.debug("deleting tracks")
            track_is = range(len(tracks))
            #Select a random number of indices to delete.
            del_is = set(random.sample(track_is, random.choice(track_is)))
            tracks = [track for i, track in enumerate(tracks) if not i in del_is]

        if add_dupe:
            self.log.debug("adding dupe tracks from same playlist")
            tracks.extend(random.sample(tracks, random.randrange(len(tracks))))
            
        if add_blank:
            self.log.debug("adding random tracks with no eid")
            tracks.extend(random.sample(self.library, random.randrange(len(tracks))))

        if reorder:
            self.log.debug("shuffling tracks")
            random.shuffle(tracks)

        self.api.change_playlist(p_id, tracks)
        
        server_tracks = self.api.get_playlist_songs(p_id)

        self.assertTrue(len(tracks) == len(server_tracks))

        self.assertTrue(
            all((local_t["id"] == server_t["id"]
                 for local_t, server_t in zip(tracks, server_tracks))))

    def cpl_3_delete(self):
        """Delete the playlist."""
        self.api.delete_playlist(self.playlists['playlist to change'][-1])

        self.playlists = self.api.get_all_playlist_ids(always_id_lists=True)['user']
        
    def test_change_playlist(self):
        self.run_steps("cpl")


    def updel_1_upload(self):
        """Upload some test files."""

        some_files = random.sample(self.test_filenames, 
                                   random.randrange(len(self.test_filenames)))

        result = self.api.upload(some_files)
        self.assertTrue(len(some_files) == len(result))

        #A bit messy; need to pass the ids on to the next step.
        self.uploaded_ids = result.values()

    def updel_2_delete(self):
        """Delete the uploaded test files."""
        self.api.delete_songs(self.uploaded_ids)

        del self.uploaded_ids

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
        #Changing immutable ones voids the request (although we get back success:True and our expected values).
        new_md = copy.deepcopy(orig_md)
        expts = Metadata_Expectations.get_all_expectations()

        for name, expt in expts.items():
            if name in orig_md and expt.mutable:
                old_val = orig_md[name]
                new_val = test_utils.modify_md(name, old_val)

                self.log.debug("%s: %s modified to %s", name, repr(old_val), repr(new_val))
                self.assertTrue(new_val != old_val)
                new_md[name] = new_val

        #Make the call to change the metadata.
        #This should succeed, even though we _shouldn't_ be able to change some entries.
        #The call only fails if you give the wrong datatype.
        self.api.change_song_metadata(new_md)


        #Recreate the dependent md to what they should be (based on how orig_md was changed)
        correct_dependent_md = {}
        for name, expt in expts.items():
            if expt.depends_on and name in orig_md:
                master_name = expt.depends_on
                correct_dependent_md[name] = expt.dependent_transformation(new_md[master_name])

                # master_key, trans = dependent_md[name]
                # correct_dependent_md[dep_key] = trans(new_md[master_key])

                self.log.debug("dependents (%s): %s -> %s", name, new_md[master_name], correct_dependent_md[name])

        #The library needs to be refreshed to flush the changes.
        #This might not happen right away, so we allow a few retries.

        max_attempts = 3
        sleep_for = 3

        attempts = 0
        success = False

        #TODO: this is cludgey, and should be pulled out with the below retry logic.
        while not success and attempts < max_attempts:
            time.sleep(sleep_for)
            self.library = self.api.get_all_songs()

            attempts += 1

            result_md = [s for s in self.library if s["id"] == orig_md["id"]][0]
            self.log.debug("result md: %s", repr(result_md))


            try:
                #Verify everything went as expected:
                for name, expt in expts.items():
                    if name in orig_md:
                        #Check mutability if it's not a volatile key.
                        if not expt.volatile:
                            same, message = test_utils.md_entry_same(name, orig_md, result_md)
                            self.assertTrue(same == (not expt.mutable), "metadata mutability incorrect: " + message)

                        #Check dependent md.
                        if expt.depends_on:
                            same, message = test_utils.md_entry_same(name, correct_dependent_md, result_md)
                            self.assertTrue(same, "dependent metadata incorrect: " + message)

            except AssertionError:
                self.log.info("retrying server for changed metadata")
                if not attempts < max_attempts: raise
            else:
                success = True

            
        #Revert the metadata.
        self.api.change_song_metadata(orig_md)

        #Verify everything is as it was.

        attempts = 0
        success = False

        while not success and attempts < max_attempts:
            time.sleep(sleep_for)
            self.library = self.api.get_all_songs()

            attempts += 1

            result_md = [s for s in self.library if s["id"] == orig_md["id"]][0]
            self.log.debug("result md: %s", repr(result_md))

            try:
                for name in orig_md:
                    #If it's not volatile, it should be back to what it was.
                    if not expts[name].volatile:
                        same, message = test_utils.md_entry_same(name, orig_md, result_md)
                        self.assertTrue(same, "failed to revert: " + message)
                
            except AssertionError:
                self.log.info("retrying server for reverted metadata")
                if not attempts < max_attempts: raise
            else:
                success = True
        

    def test_search(self):
        self.api.search('e')

    def test_get_stream_url(self):
        #This should return a valid url.
        #This is not robust; it's assumed that invalid calls will raise an error before this point.
        url = self.api.get_stream_url(self.r_song_id)
        self.assertTrue(url[:4] == "http")
        

if __name__ == '__main__':
    unittest.main()
