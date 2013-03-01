"""
These tests all run against an actual Google Music account.

Destructive modifications are not made, but if things go terrible wrong,
an extra test playlist or song may result.
"""

from proboscis.asserts import (
    assert_raises, assert_true, assert_equal, assert_is_not_none,
    Check
)
from proboscis import test, before_class, after_class, SkipTest

from gmusicapi.exceptions import NotLoggedIn
from gmusicapi.utils.utils import retry
import gmusicapi.test.utils as test_utils

TEST_PLAYLIST_NAME = 'gmusicapi_test_playlist'


@test(groups=['server'])
class NoUpauthTests(object):

    @before_class
    def login(self):
        self.api = test_utils.init(perform_upload_auth=False)
        assert_true(self.api.is_authenticated())

    @after_class(always_run=True)
    def logout(self):
        assert_true(self.api.logout())

    @test
    def need_upauth_for_upload(self):
        assert_raises(NotLoggedIn, self.api.upload, 'fake filename')


@test(groups=['server'])
class UpauthTests(object):
    @before_class
    def login(self):
        self.api = test_utils.init()
        assert_true(self.api.is_authenticated())

    @after_class(always_run=True)
    def logout(self):
        assert_true(self.api.logout())

    # This next section is a bit odd: it nests playlist tests inside song tests.

    # The intuitition: starting from an empty library, you need to have
    #  a song before you can modify a playlist.

    # If x --> y means x runs before y, then the graph looks like:

    #     song_create <-- playlist_create
    #     song_delete --> playlist_delete
    #         |                   |
    #         v                   v
    #     <song test>     <playlist test>

    # Singleton groups are used to ease code ordering restraints.
    # Suggestions to improve any of this are welcome!

    @test
    def song_create(self):
        """Create a song."""
        self.song_id = None

        filepath = test_utils.mp3_filenames[0]

        uploaded, matched, not_uploaded = self.api.upload(filepath)
        assert_equal(not_uploaded, {})
        assert_equal(matched, {})
        assert_equal(uploaded.keys(), [filepath])

        self.song_id = uploaded[filepath]

        # we test get_all_songs here so that we can assume the existance
        # of the song for future tests (the servers take time to sync an upload)
        @retry
        def assert_song_exists(sid):
            songs = self.api.get_all_songs()

            found = [s for s in songs if s['id'] == sid] or None

            assert_is_not_none(found)
            assert_equal(len(found), 1)

        assert_song_exists(self.song_id)

    @test(depends_on=[song_create])
    def playlist_create(self):
        """Create a playlist."""
        self.playlist_id = None

        self.playlist_id = self.api.create_playlist(TEST_PLAYLIST_NAME)

        # same as song_create, retry until the song appears

        @retry
        def assert_playlist_exists(plid):
            playlists = self.api.get_all_playlist_ids(auto=False, user=True)

            found = playlists['user'].get(TEST_PLAYLIST_NAME, None)

            assert_is_not_none(found)
            assert_equal(found[-1], self.playlist_id)

        assert_playlist_exists(self.playlist_id)

    #TODO consider listing/searching if the id isn't there
    # to ensure cleanup.
    @test(depends_on_groups=['playlist'], always_run=True)
    def playlist_delete(self):
        """Delete the playlist."""
        if self.playlist_id is None:
            raise SkipTest('did not store self.playlist_id')

        res = self.api.delete_playlist(self.playlist_id)

        assert_equal(res, self.playlist_id)

    @test(depends_on=[playlist_delete], depends_on_groups=['song'], always_run=True)
    def song_delete(self):
        """Delete the song."""
        if self.song_id is None:
            raise SkipTest('did not store self.song_id')

        res = self.api.delete_songs(self.song_id)

        assert_equal(res, [self.song_id])

    # These decorators just prevent setting groups and depends_on over and over.
    # They won't work right with additional settings; if that's needed this
    #  pattern should be factored out.

    song_test = test(groups=['song'], depends_on=[song_create])
    playlist_test = test(groups=['playlist'], depends_on=[playlist_create])

    # Non-wonky tests resume down here.

    #-----------
    # Song tests
    #-----------

    #TODO album art, search, metadata

    @song_test
    def list_songs(self):
        songs = self.api.get_all_songs()

        found = [s for s in songs if s['id'] == self.song_id] or None

        assert_is_not_none(found)
        assert_equal(len(found), 1)

    @song_test
    def get_download_info(self):
        url, download_count = self.api.get_song_download_info(self.song_id)

        assert_is_not_none(url)

    #---------------
    # Playlist tests
    #---------------

    #TODO change, copy

    @playlist_test
    def change_name(self):
        new_name = TEST_PLAYLIST_NAME + '_mod'
        self.api.change_playlist_name(self.playlist_id, new_name)

        @retry  # change takes time to propogate
        def assert_name_equal(plid, name):
            playlists = self.api.get_all_playlist_ids()

            found = playlists['user'].get(name, None)

            assert_is_not_none(found)
            assert_equal(found[-1], self.playlist_id)

        assert_name_equal(self.playlist_id, new_name)

        # revert
        self.api.change_playlist_name(self.playlist_id, TEST_PLAYLIST_NAME)
        assert_name_equal(self.playlist_id, TEST_PLAYLIST_NAME)

    @playlist_test
    def add_remove(self):
        @retry
        def assert_song_order(plid, order):
            songs = self.api.get_playlist_songs(plid)
            server_order = [s['id'] for s in songs]

            assert_equal(server_order, order)

        # initially empty
        assert_song_order(self.playlist_id, [])

        # add two copies
        self.api.add_songs_to_playlist(self.playlist_id, [self.song_id] * 2)
        assert_song_order(self.playlist_id, [self.song_id] * 2)

        # remove all copies
        self.api.remove_songs_from_playlist(self.playlist_id, self.song_id)
        assert_song_order(self.playlist_id, [])
