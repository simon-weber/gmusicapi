# -*- coding: utf-8 -*-

"""
These tests all run against an actual Google Music account.

Destructive modifications are not made, but if things go terrible wrong,
an extra test playlist or song may result.
"""

from collections import namedtuple
import os
import re
import types

from decorator import decorator
from proboscis.asserts import (
    assert_true, assert_equal, assert_is_not_none,
    Check
)
from proboscis import test, before_class, after_class, SkipTest

from gmusicapi import Webclient, Musicmanager, Mobileclient
from gmusicapi.utils.utils import retry
import gmusicapi.test.utils as test_utils

TEST_PLAYLIST_NAME = 'gmusicapi_test_playlist'
TEST_STATION_NAME = 'gmusicapi_test_station'
TEST_AA_SONG_ID = 'Tqqufr34tuqojlvkolsrwdwx7pe'

# this is a little data class for the songs we upload
TestSong = namedtuple('TestSong', 'sid title artist album')


def test_all_access_features():
    return 'GM_A' in os.environ


@decorator
def all_access(f, *args, **kwargs):
    """Declare a test to only be run if All Access testing is enabled."""
    if test_all_access_features():
        return f(*args, **kwargs)
    else:
        raise SkipTest('All Access testing disabled')


@test(groups=['server'])
class UpauthTests(object):
    # set on the instance in login
    wc = None  # webclient
    mm = None  # musicmanager
    mc = None  # mobileclient

    #These are set on the instance in create_song/playlist.
    songs = None  # [TestSong]
    playlist_id = None
    plentry_ids = None
    station_id = None

    def mc_get_playlist_songs(self, plid):
        """For convenience, since mc can only get all playlists at once."""
        all_contents = self.mc.get_all_playlist_contents()
        found = [p for p in all_contents if p['id'] == plid]

        assert_true(len(found), 1)

        return found[0]['tracks']

    @before_class
    def login(self):
        self.wc = test_utils.new_test_client(Webclient)
        assert_true(self.wc.is_authenticated())

        self.mm = test_utils.new_test_client(Musicmanager)
        assert_true(self.mm.is_authenticated())

        self.mc = test_utils.new_test_client(Mobileclient)
        assert_true(self.mc.is_authenticated())

    @after_class(always_run=True)
    def logout(self):
        if self.wc is None:
            raise SkipTest('did not create wc')
        assert_true(self.wc.logout())

        if self.mm is None:
            raise SkipTest('did not create mm')
        assert_true(self.mm.logout())

        if self.mc is None:
            raise SkipTest('did not create mc')
        assert_true(self.mc.logout())

    # This next section is a bit odd: it orders tests that create
    # required resources.

    # The intuitition: starting from an empty library, you need to create
    #  a song before you can eg add it to a playlist.

    # The dependencies end up with an ordering that might look like:
    #
    # with song
    #   with playlist
    #     with plentry
    #
    # with station
    #
    # Suggestions to improve any of this are welcome!

    @staticmethod
    @retry
    def assert_songs_state(method, sids, present):
        """
        Assert presence/absence of sids and return a list of
        TestSongs found.

        :param method: eg self.mc.get_all_songs
        :param sids: list of song ids
        :param present: if True verify songs are present; False the opposite
        """

        library = method()

        found = [s for s in library if s['id'] in sids]

        expected_len = len(sids)
        if not present:
            expected_len = 0

        assert_equal(len(found), expected_len)

        return [TestSong(s['id'], s['title'], s['artist'], s['album'])
                for s in found]

    @staticmethod
    @retry
    def assert_list_inc_equivalence(method, **kwargs):
        """
        Assert that some listing method returns the same
        contents for incremental=True/False.

        :param method: eg self.mc.get_all_songs, must support `incremental` kwarg
        :param **kwargs: passed to method
        """

        lib_chunk_gen = method(incremental=True, **kwargs)
        assert_true(isinstance(lib_chunk_gen, types.GeneratorType))

        assert_equal([e for chunk in lib_chunk_gen for e in chunk],
                     method(incremental=False, **kwargs))

    @staticmethod
    @retry
    def assert_list_with_deleted(method):
        """
        Assert that some listing method includes deleted tracks.

        :param method: eg self.mc.get_all_songs
        """
        lib = method(incremental=False, include_deleted=True)

        # how long do deleted tracks get returned for?
        # will this return tracks I've deleted since...ever?

        num_deleted = [t for t in lib if t['deleted']]
        assert_true(num_deleted > 0)

    @test
    def song_create(self):
        # This can create more than one song: one through uploading, one through
        # adding an AA track to the library.

        fname = test_utils.small_mp3

        uploaded, matched, not_uploaded = self.mm.upload(fname)

        sids = []

        if len(not_uploaded) == 1 and 'ALREADY_EXISTS' in not_uploaded[fname]:
            # If a previous test went wrong, the track might be there already.
            #TODO This build will fail because of the warning - is that what we want?
            assert_equal(matched, {})
            assert_equal(uploaded, {})

            sids.append(re.search(r'\(.*\)', not_uploaded[fname]).group().strip('()'))
        else:
            # Otherwise, it should have been uploaded normally.
            assert_equal(not_uploaded, {})
            assert_equal(matched, {})
            assert_equal(uploaded.keys(), [fname])

            sids.append(uploaded[fname])

        if test_all_access_features():
            sids.append(self.mc.add_aa_track(test_utils.aa_song_id))

        # we test get_all_songs here so that we can assume the existance
        # of the song for future tests (the servers take time to sync an upload)

        self.songs = self.assert_songs_state(self.mc.get_all_songs, sids, present=True)

    @test
    def playlist_create(self):
        playlist_id = self.mc.create_playlist(TEST_PLAYLIST_NAME)

        # like song_create, retry until the playlist appears
        @retry
        def assert_playlist_exists(plid):
            found = [p for p in self.mc.get_all_playlists()
                     if p['id'] == plid]

            assert_equal(len(found), 1)

        assert_playlist_exists(playlist_id)
        self.playlist_id = playlist_id

    @test(depends_on=[playlist_create, song_create],
          runs_after_groups=['playlist.exists', 'song.exists'])
    def plentry_create(self):

        song_ids = [self.songs[0].sid]

        # create 3 entries
        # 3 songs is the minimum to fully test reordering, and also includes the
        # duplicate song_id case
        double_id = self.songs[0].sid
        if test_all_access_features():
            double_id = test_utils.aa_song_id

        song_ids += [double_id] * 2

        plentry_ids = self.mc.add_songs_to_playlist(self.playlist_id, song_ids)

        @retry
        def assert_plentries_exist(plid, plentry_ids):
            songs = self.mc_get_playlist_songs(plid)
            found = [e for e in songs
                     if e['id'] in plentry_ids]

            assert_equal(len(found), len(plentry_ids))

        assert_plentries_exist(self.playlist_id, plentry_ids)
        self.plentry_ids = plentry_ids

    @test(groups=['plentry'], depends_on=[plentry_create],
          runs_after_groups=['plentry.exists'],
          always_run=True)
    def plentry_delete(self):
        if self.plentry_ids is None:
            raise SkipTest('did not store self.plentry_ids')

        res = self.mc.remove_entries_from_playlist(self.plentry_ids)
        assert_equal(res, self.plentry_ids)

        @retry
        def assert_plentries_removed(plid, entry_ids):
            found = [e for e in self.mc_get_playlist_songs(plid)
                     if e['id'] in entry_ids]

            assert_equal(len(found), 0)

        assert_plentries_removed(self.playlist_id, self.plentry_ids)
        #self.assert_list_with_deleted(self.mc_get_playlist_songs)

    @test(groups=['playlist'], depends_on=[playlist_create],
          runs_after=[plentry_delete],
          runs_after_groups=['playlist.exists'],
          always_run=True)
    def playlist_delete(self):
        if self.playlist_id is None:
            raise SkipTest('did not store self.playlist_id')

        res = self.mc.delete_playlist(self.playlist_id)
        assert_equal(res, self.playlist_id)

        @retry
        def assert_playlist_does_not_exist(plid):
            found = [p for p in self.mc.get_all_playlists(include_deleted=False)
                     if p['id'] == plid]

            assert_equal(len(found), 0)

        assert_playlist_does_not_exist(self.playlist_id)
        self.assert_list_with_deleted(self.mc.get_all_playlists)

    @test(groups=['song'], depends_on=[song_create],
          runs_after=[plentry_delete],
          runs_after_groups=["song.exists"],
          always_run=True)
    def song_delete(self):
        if self.songs is None:
            raise SkipTest('did not store self.songs')

        # split deletion between wc and mc
        # mc is the only to run if AA testing not enabled
        with Check() as check:
            for i, testsong in enumerate(self.songs):
                if i % 2 == 0:
                    res = self.mc.delete_songs(testsong.sid)
                else:
                    res = self.wc.delete_songs(testsong.sid)
                check.equal(res, [testsong.sid])

        self.assert_songs_state(self.mc.get_all_songs, [s.sid for s in self.songs], present=False)
        self.assert_list_with_deleted(self.mc.get_all_songs)

    @test
    def station_create(self):
        if not test_all_access_features():
            raise SkipTest('AA testing not enabled')

        # seed from Amorphis
        station_id = self.mc.create_station(TEST_STATION_NAME,
                                            artist_id='Apoecs6off3y6k4h5nvqqos4b5e')

        @retry
        def assert_station_exists(station_id):
            stations = self.mc.get_all_stations()

            found = [s for s in stations
                     if s['id'] == station_id]

            assert_equal(len(found), 1)

        assert_station_exists(station_id)
        self.station_id = station_id

    @test(groups=['station'], depends_on=[station_create],
          runs_after_groups=['station.exists'],
          always_run=True)
    def station_delete(self):
        if self.station_id is None:
            raise SkipTest('did not store self.station_id')

        res = self.mc.delete_stations([self.station_id])
        assert_equal(res, [self.station_id])

        @retry
        def assert_station_deleted(station_id):
            stations = self.mc.get_all_stations()

            found = [s for s in stations
                     if s['id'] == station_id]

            assert_equal(len(found), 0)

        assert_station_deleted(self.station_id)
        self.assert_list_with_deleted(self.mc.get_all_stations)

    ## These decorators just prevent setting groups and depends_on over and over.
    ## They won't work right with additional settings; if that's needed this
    ##  pattern should be factored out.

    ##TODO it'd be nice to have per-client test groups
    song_test = test(groups=['song', 'song.exists'], depends_on=[song_create])
    playlist_test = test(groups=['playlist', 'playlist.exists'],
                         depends_on=[playlist_create])
    plentry_test = test(groups=['plentry', 'plentry.exists'],
                        depends_on=[plentry_create])
    station_test = test(groups=['station', 'station.exists'], depends_on=[station_create])

    ## Non-wonky tests resume down here.

    ##---------
    ## MM tests
    ##---------

    @song_test
    def mm_list_new_songs(self):
        self.assert_songs_state(self.mm.get_all_songs, [s.sid for s in self.songs], present=True)

    @test
    def mm_list_songs_inc_equal(self):
        self.assert_list_inc_equivalence(self.mm.get_all_songs)

    ##---------
    ## WC tests
    ##---------

    @song_test
    def wc_list_new_songs(self):
        self.assert_songs_state(self.wc.get_all_songs, [s.sid for s in self.songs], present=True)

    @test
    def wc_list_songs_inc_equal(self):
        self.assert_list_inc_equivalence(self.wc.get_all_songs)

    @test
    def wc_get_registered_devices(self):
        # no logic; just checking schema
        self.wc.get_registered_devices()

    @test
    @all_access
    def wc_get_aa_stream_urls(self):
        # that dumb little intro track on Conspiracy of One
        urls = self.wc.get_stream_urls(TEST_AA_SONG_ID)

        assert_true(len(urls) > 1)

    @test
    @all_access
    def wc_stream_aa_track(self):
        # that dumb little intro track on Conspiracy of One
        audio = self.wc.get_stream_audio(TEST_AA_SONG_ID)
        assert_is_not_none(audio)

    ##---------
    ## MC tests
    ##---------

    @test
    def mc_list_stations_inc_equal(self):
        self.assert_list_inc_equivalence(self.mc.get_all_stations)

    @test
    def mc_list_stations_inc_equal_with_deleted(self):
        self.assert_list_inc_equivalence(self.mc.get_all_stations, include_deleted=True)

    @song_test
    def mc_list_songs_inc_equal(self):
        self.assert_list_inc_equivalence(self.mc.get_all_songs)

    @song_test
    def mc_list_songs_inc_equal_with_deleted(self):
        self.assert_list_inc_equivalence(self.mc.get_all_songs, include_deleted=True)

    @playlist_test
    def mc_list_playlists_inc_equal(self):
        self.assert_list_inc_equivalence(self.mc.get_all_playlists)

    @playlist_test
    def mc_list_playlists_inc_equal_with_deleted(self):
        self.assert_list_inc_equivalence(self.mc.get_all_playlists, include_deleted=True)

    @playlist_test
    def mc_change_playlist_name(self):
        new_name = TEST_PLAYLIST_NAME + '_mod'
        plid = self.mc.change_playlist_name(self.playlist_id, new_name)
        assert_equal(self.playlist_id, plid)

        @retry  # change takes time to propogate
        def assert_name_equal(plid, name):
            playlists = self.mc.get_all_playlists()

            found = [p for p in playlists if p['id'] == plid]

            assert_equal(len(found), 1)
            assert_equal(found[0]['name'], name)

        assert_name_equal(self.playlist_id, new_name)

        # revert
        self.mc.change_playlist_name(self.playlist_id, TEST_PLAYLIST_NAME)
        assert_name_equal(self.playlist_id, TEST_PLAYLIST_NAME)

    @plentry_test
    def pt(self):
        raise SkipTest('plentry placeholder')

    @station_test
    @all_access
    def mc_list_station_tracks(self):
        res = self.mc.get_station_tracks(self.station_id, num_tracks=1)
        assert_equal(len(res), 1)

    @test
    @all_access
    def mc_search_aa(self):
        res = self.mc.search_all_access('amorphis')
        with Check() as check:
            for hits in res.values():
                check.true(len(hits) > 0)

    @test
    @all_access
    def mc_artist_info(self):
        aid = 'Apoecs6off3y6k4h5nvqqos4b5e'  # amorphis
        optional_keys = set(('albums', 'topTracks', 'related_artists'))

        include_all_res = self.mc.get_artist_info(aid, include_albums=True,
                                                  max_top_tracks=1, max_rel_artist=1)

        no_albums_res = self.mc.get_artist_info(aid, include_albums=False)
        no_rel_res = self.mc.get_artist_info(aid, max_rel_artist=0)
        no_tracks_res = self.mc.get_artist_info(aid, max_top_tracks=0)

        with Check() as check:
            check.true(set(include_all_res.keys()) & optional_keys == optional_keys)

            check.true(set(no_albums_res.keys()) & optional_keys ==
                       optional_keys - set(['albums']))
            check.true(set(no_rel_res.keys()) & optional_keys ==
                       optional_keys - set(['related_artists']))
            check.true(set(no_tracks_res.keys()) & optional_keys ==
                       optional_keys - set(['topTracks']))
    ##TODO album art

    #@song_test
    #def change_metadata(self):
    #    orig_md = self._assert_get_song(self.song.sid)

    #    # Change all mutable entries.

    #    new_md = copy(orig_md)

    #    for name, expt in md_expectations.items():
    #        if name in orig_md and expt.mutable:
    #            old_val = orig_md[name]
    #            new_val = test_utils.modify_md(name, old_val)

    #            assert_not_equal(new_val, old_val)
    #            new_md[name] = new_val

    #    #TODO check into attempting to mutate non mutables
    #    self.wc.change_song_metadata(new_md)

    #    #Recreate the dependent md to what they should be (based on how orig_md was changed)
    #    correct_dependent_md = {}
    #    for name, expt in md_expectations.items():
    #        if expt.depends_on and name in orig_md:
    #            master_name = expt.depends_on
    #            correct_dependent_md[name] = expt.dependent_transformation(new_md[master_name])

    #    @retry
    #    def assert_metadata_is(sid, orig_md, correct_dependent_md):
    #        result_md = self._assert_get_song(sid)

    #        with Check() as check:
    #            for name, expt in md_expectations.items():
    #                if name in orig_md:
    #                    #TODO really need to factor out to test_utils?

    #                    #Check mutability if it's not volatile or dependent.
    #                    if not expt.volatile and expt.depends_on is None:
    #                        same, message = test_utils.md_entry_same(name, orig_md, result_md)
    #                        check.equal(not expt.mutable, same,
    #                                    "metadata mutability incorrect: " + message)

    #                    #Check dependent md.
    #                    if expt.depends_on is not None:
    #                        same, message = test_utils.md_entry_same(
    #                            name, correct_dependent_md, result_md
    #                        )
    #                        check.true(same, "dependent metadata incorrect: " + message)

    #    assert_metadata_is(self.song.sid, orig_md, correct_dependent_md)

    #    #Revert the metadata.
    #    self.wc.change_song_metadata(orig_md)

    #    @retry
    #    def assert_metadata_reverted(sid, orig_md):
    #        result_md = self._assert_get_song(sid)

    #        with Check() as check:
    #            for name in orig_md:
    #                #If it's not volatile, it should be back to what it was.
    #                if not md_expectations[name].volatile:
    #                    same, message = test_utils.md_entry_same(name, orig_md, result_md)
    #                    check.true(same, "failed to revert: " + message)
    #    assert_metadata_reverted(self.song.sid, orig_md)

    ##TODO verify these better?

    #@song_test
    #def get_download_info(self):
    #    url, download_count = self.wc.get_song_download_info(self.song.sid)

    #    assert_is_not_none(url)

    #@song_test
    #def download_song_mm(self):

    #    @retry
    #    def assert_download(sid=self.song.sid):
    #        filename, audio = self.mm.download_song(sid)

    #        # there's some kind of a weird race happening here with CI;
    #        # usually one will succeed and one will fail

    #        #TODO could use original filename to verify this
    #        # but, when manually checking, got modified title occasionally
    #        assert_true(filename.endswith('.mp3'))  # depends on specific file
    #        assert_is_not_none(audio)
    #    assert_download()

    #@song_test
    #def get_uploaded_stream_urls(self):
    #    urls = self.wc.get_stream_urls(self.song.sid)

    #    assert_equal(len(urls), 1)

    #    url = urls[0]

    #    assert_is_not_none(url)
    #    assert_equal(url[:7], 'http://')

    #@song_test
    #def upload_album_art(self):
    #    orig_md = self._assert_get_song(self.song.sid)

    #    self.wc.upload_album_art(self.song.sid, test_utils.image_filename)

    #    self.wc.change_song_metadata(orig_md)
    #    #TODO redownload and verify against original?

    ## these search tests are all skipped: see
    ## https://github.com/simon-weber/Unofficial-Google-Music-API/issues/114

    #@staticmethod
    #def _assert_search_hit(res, hit_type, hit_key, val):
    #    """Assert that the result (returned from wc.search) has
    #    ``hit[hit_type][hit_key] == val`` for only one result in hit_type."""

    #    raise SkipTest('search is unpredictable (#114)')

    #    #assert_equal(sorted(res.keys()), ['album_hits', 'artist_hits', 'song_hits'])
    #    #assert_not_equal(res[hit_type], [])

    #    #hitmap = (hit[hit_key] == val for hit in res[hit_type])
    #    #assert_equal(sum(hitmap), 1)  # eg sum(True, False, True) == 2

    ##@song_test
    ##def search_title(self):
    ##    res = self.wc.search(self.song.title)

    ##    self._assert_search_hit(res, 'song_hits', 'id', self.song.sid)

    ##@song_test
    ##def search_artist(self):
    ##    res = self.wc.search(self.song.artist)

    ##    self._assert_search_hit(res, 'artist_hits', 'id', self.song.sid)

    ##@song_test
    ##def search_album(self):
    ##    res = self.wc.search(self.song.album)

    ##    self._assert_search_hit(res, 'album_hits', 'albumName', self.song.album)

    ##---------------
    ## Playlist tests
    ##---------------

    ##TODO copy, change (need two songs?)

    #@playlist_test
    #def change_name(self):
    #    new_name = TEST_PLAYLIST_NAME + '_mod'
    #    self.wc.change_playlist_name(self.playlist_id, new_name)

    #    @retry  # change takes time to propogate
    #    def assert_name_equal(plid, name):
    #        playlists = self.wc.get_all_playlist_ids()

    #        found = playlists['user'].get(name, None)

    #        assert_is_not_none(found)
    #        assert_equal(found[-1], self.playlist_id)

    #    assert_name_equal(self.playlist_id, new_name)

    #    # revert
    #    self.wc.change_playlist_name(self.playlist_id, TEST_PLAYLIST_NAME)
    #    assert_name_equal(self.playlist_id, TEST_PLAYLIST_NAME)

    #@playlist_test
    #def add_remove(self):
    #    @retry
    #    def assert_song_order(plid, order):
    #        songs = self.wc.get_playlist_songs(plid)
    #        server_order = [s['id'] for s in songs]

    #        assert_equal(server_order, order)

    #    # initially empty
    #    assert_song_order(self.playlist_id, [])

    #    # add two copies
    #    self.wc.add_songs_to_playlist(self.playlist_id, [self.song.sid] * 2)
    #    assert_song_order(self.playlist_id, [self.song.sid] * 2)

    #    # remove all copies
    #    self.wc.remove_songs_from_playlist(self.playlist_id, self.song.sid)
    #    assert_song_order(self.playlist_id, [])
