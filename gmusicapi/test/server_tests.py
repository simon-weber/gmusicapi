"""
These tests all run against an actual Google Music account.

Destructive modifications are not made, but if things go terrible wrong,
an extra test playlist or song may result.
"""

from copy import copy
from collections import namedtuple

from proboscis.asserts import (
    assert_raises, assert_true, assert_equal, assert_is_not_none,
    assert_not_equal, Check
)
from proboscis import test, before_class, after_class, SkipTest

from gmusicapi.exceptions import NotLoggedIn
from gmusicapi.protocol.metadata import md_expectations
from gmusicapi.utils.utils import retry
import gmusicapi.test.utils as test_utils

TEST_PLAYLIST_NAME = 'gmusicapi_test_playlist'

# this is a little data class for the songs we upload
TestSong = namedtuple('TestSong', 'sid title artist album')


@test(groups=['server'])
class NoUpauthTests(object):

    @before_class
    def login(self):
        self.api = test_utils.new_test_api(perform_upload_auth=False)
        assert_true(self.api.is_authenticated())

    @after_class(always_run=True)
    def logout(self):
        assert_true(self.api.logout())

    @test
    def need_upauth_for_upload(self):
        assert_raises(NotLoggedIn, self.api.upload, 'fake filename')


@test(groups=['server'])
class UpauthTests(object):
    #These are set on the instance in create_song/playlist.
    song = None
    playlist_id = None

    @before_class
    def login(self):
        self.api = test_utils.new_test_api()
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
        uploaded, matched, not_uploaded = self.api.upload(test_utils.small_mp3)
        assert_equal(not_uploaded, {})
        assert_equal(matched, {})
        assert_equal(uploaded.keys(), [test_utils.small_mp3])

        sid = uploaded[test_utils.small_mp3]

        # we test get_all_songs here so that we can assume the existance
        # of the song for future tests (the servers take time to sync an upload)
        @retry
        def assert_song_exists(sid):
            songs = self.api.get_all_songs()

            found = [s for s in songs if s['id'] == sid] or None

            assert_is_not_none(found)
            assert_equal(len(found), 1)

            s = found[0]
            return TestSong(s['id'], s['title'], s['artist'], s['album'])

        self.song = assert_song_exists(sid)

    @test(depends_on=[song_create])
    def playlist_create(self):
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
        if self.playlist_id is None:
            raise SkipTest('did not store self.playlist_id')

        res = self.api.delete_playlist(self.playlist_id)

        assert_equal(res, self.playlist_id)

    @test(depends_on=[playlist_delete], depends_on_groups=['song'], always_run=True)
    def song_delete(self):
        if self.song is None:
            raise SkipTest('did not store self.song')

        res = self.api.delete_songs(self.song.sid)

        assert_equal(res, [self.song.sid])

    # These decorators just prevent setting groups and depends_on over and over.
    # They won't work right with additional settings; if that's needed this
    #  pattern should be factored out.

    song_test = test(groups=['song'], depends_on=[song_create])
    playlist_test = test(groups=['playlist'], depends_on=[playlist_create])

    # Non-wonky tests resume down here.

    #-----------
    # Song tests
    #-----------

    #TODO album art

    def _assert_get_song(self, sid):
        """Return the song dictionary with this sid.

        (GM has no native get ability for songs, just list)."""
        songs = self.api.get_all_songs()

        found = [s for s in songs if s['id'] == self.song.sid] or None

        assert_is_not_none(found)
        assert_equal(len(found), 1)

        return found[0]

    @song_test
    def list_songs(self):
        self._assert_get_song(self.song.sid)

    @song_test
    def change_metadata(self):
        orig_md = self._assert_get_song(self.song.sid)

        # Change all mutable entries.

        new_md = copy(orig_md)

        for name, expt in md_expectations.items():
            if name in orig_md and expt.mutable:
                old_val = orig_md[name]
                new_val = test_utils.modify_md(name, old_val)

                assert_not_equal(new_val, old_val)
                new_md[name] = new_val

        #TODO check into attempting to mutate non mutables
        self.api.change_song_metadata(new_md)

        #Recreate the dependent md to what they should be (based on how orig_md was changed)
        correct_dependent_md = {}
        for name, expt in md_expectations.items():
            if expt.depends_on and name in orig_md:
                master_name = expt.depends_on
                correct_dependent_md[name] = expt.dependent_transformation(new_md[master_name])

        @retry
        def assert_metadata_is(sid, orig_md, correct_dependent_md):
            result_md = self._assert_get_song(sid)

            with Check() as check:
                for name, expt in md_expectations.items():
                    if name in orig_md:
                        #TODO really need to factor out to test_utils?

                        #Check mutability if it's not volatile or dependent.
                        if not expt.volatile and expt.depends_on is None:
                            same, message = test_utils.md_entry_same(name, orig_md, result_md)
                            check.equal(not expt.mutable, same,
                                        "metadata mutability incorrect: " + message)

                        #Check dependent md.
                        if expt.depends_on is not None:
                            same, message = test_utils.md_entry_same(
                                name, correct_dependent_md, result_md
                            )
                            check.true(same, "dependent metadata incorrect: " + message)

        assert_metadata_is(self.song.sid, orig_md, correct_dependent_md)

        #Revert the metadata.
        self.api.change_song_metadata(orig_md)

        @retry
        def assert_metadata_reverted(sid, orig_md):
            result_md = self._assert_get_song(sid)

            with Check() as check:
                for name in orig_md:
                    #If it's not volatile, it should be back to what it was.
                    if not md_expectations[name].volatile:
                        same, message = test_utils.md_entry_same(name, orig_md, result_md)
                        check.true(same, "failed to revert: " + message)
        assert_metadata_reverted(self.song.sid, orig_md)

    #TODO verify these better?

    @song_test
    def get_download_info(self):
        url, download_count = self.api.get_song_download_info(self.song.sid)

        assert_is_not_none(url)

    @song_test
    def get_stream_url(self):
        url = self.api.get_stream_url(self.song.sid)

        assert_is_not_none(url)

    @song_test
    def upload_album_art(self):
        orig_md = self._assert_get_song(self.song.sid)

        self.api.upload_album_art(self.song.sid, test_utils.image_filename)

        self.api.change_song_metadata(orig_md)
        #TODO redownload and verify against original?

    @staticmethod
    def _assert_search_hit(res, hit_type, hit_key, val):
        """Assert that the result (returned from Api.search) has
        ``hit[hit_type][hit_key] == val`` for only one result in hit_type."""

        assert_equal(sorted(res.keys()), ['album_hits', 'artist_hits', 'song_hits'])
        assert_not_equal(res[hit_type], [])

        hitmap = (hit[hit_key] == val for hit in res[hit_type])
        assert_equal(sum(hitmap), 1)  # eg sum(True, False, True) == 2

    @song_test
    def search_title(self):
        res = self.api.search(self.song.title)

        self._assert_search_hit(res, 'song_hits', 'id', self.song.sid)

    @song_test
    def search_artist(self):
        res = self.api.search(self.song.artist)

        self._assert_search_hit(res, 'artist_hits', 'id', self.song.sid)

    @song_test
    def search_album(self):
        res = self.api.search(self.song.album)

        self._assert_search_hit(res, 'album_hits', 'albumName', self.song.album)

    #---------------
    # Playlist tests
    #---------------

    #TODO copy, change (need two songs?)

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
        self.api.add_songs_to_playlist(self.playlist_id, [self.song.sid] * 2)
        assert_song_order(self.playlist_id, [self.song.sid] * 2)

        # remove all copies
        self.api.remove_songs_from_playlist(self.playlist_id, self.song.sid)
        assert_song_order(self.playlist_id, [])
