"""A test harness for api features.
Currently, it _will_ modify the library it is tested on.
"""


import unittest

from ..api import Api
from .. import session

import random
import inspect
from getpass import getpass



def init():
    """Makes an instance of the api and attempts to login with it.
    Returns the authenticated api.
    """

    api = Api()
    
    logged_in = False
    attempts = 0

    print "Warning: this test suite _will_ modify the library it is run on."

    while not logged_in and attempts < 3:
        email = raw_input("Email: ")
        password = getpass()

        logged_in = api.login(email, password)
        attempts += 1

    return api


def call_succeeded(response):
    """Returns true if the call succeeded, false otherwise."""
    
    #Failed responses always have a success=False key.
    #Some successful responses do not have a success=True key, however.
    if 'success' in response.keys():
        return response['success']
    else:
        return True
    

class TestWCApiCalls(unittest.TestCase):
    """Runs integration tests for the calls made through wc_communicator.
    Tests are intended not to modify the library when finished, but no guarantees are made.
    """

    @classmethod
    def setUpClass(cls):
        """Init and log in to an api, then get the library and playlists."""
        cls.api = init()
    
        if not cls.api.is_authenticated():
            raise session.NotLoggedIn
        
        #These are assumed to succeed, but errors here will prevent further testing.
        cls.library = cls.api.get_library_track_metadata()
        cls.playlists = cls.api.get_playlist_ids()


    @classmethod
    def tearDownClass(cls):
        """Log out of the api."""

        cls.api.logout()


    def setUp(self):
        """Get a random playlist and song id."""

        self.r_pl_id = self.playlists[random.choice(list(self.playlists.keys()))]
        self.r_song_id = random.choice(self.library)['id']


    def assert_success(self, response):
        """Assert the success of a call's response."""

        self.assertTrue(call_succeeded(response))


    #Test playlist functions in a monolithic fasion.
    #Messy, but is more likely not to mess with the library.
    #Can not declare other pl_* methods by doing this.
    #Modified from http://stackoverflow.com/questions/5387299/python-unittest-testcase-execution-order
        
    #Create a playlist.
    def pl_1_create(self):
        self.assert_success(
            self.api.add_playlist('test playlist'))

        #Need to reload playlists so it appears.
        self.playlists = self.api.get_playlist_ids()

    #Add a random song to it.
    def pl_2_add_song(self):
        self.assert_success(
            self.api.add_to_playlist(self.playlists['test playlist'], self.r_song_id))

    #Change its name.
    def pl_3_change_name(self):
        self.assert_success(
            self.api.change_playlist_name(self.playlists['test playlist'], 'modified playlist'))

        self.playlists = self.api.get_playlist_ids()
            
    #Delete it.
    def pl_4_delete(self):
        self.assert_success(
            self.api.delete_playlist(self.playlists['modified playlist']))

        self.playlists = self.api.get_playlist_ids()


    def playlist_steps(self):
        methods = inspect.getmembers(self, predicate=inspect.ismethod)
        
        #Sort functions based on name.
        for name, func in sorted(methods, key=lambda m: m[0]):
            if name.startswith("pl_"):
                yield name, func



    def test_playlists(self):
        for name, step in self.playlist_steps():
            try:
                step()
            except Exception as e:
                self.fail("{} failed ({}: {})".format(step, type(e), e))


    #Until uploading is implemented, there's no way to test this non-destructively.
    def test_deletesong(self):
        self.assert_success(
            self.api.delete_song(self.r_song_id))


    def test_get_track_download_info(self):
        #Need to go a layer deeper than the user-facing api to get the actual response.
        self.assert_success(
            self.api.wc_call("multidownload", self.r_song_id))
        

    def test_search(self):
        self.assert_success(
            self.api.search('e'))

if __name__ == '__main__':
    unittest.main()
