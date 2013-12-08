from operator import itemgetter

from gmusicapi import session
from gmusicapi.clients.shared import _Base
from gmusicapi.protocol import mobileclient
from gmusicapi.utils import utils


class Mobileclient(_Base):
    """Allows library management and streaming by posing as the
    googleapis.com mobile clients.

    Uploading is not supported by this client (use the :class:`Musicmanager`
    to upload).
    """

    _session_class = session.Webclient  # ie mobileclient uses clientlogin, too

    def __init__(self, debug_logging=True, validate=True, verify_ssl=True):
        super(Mobileclient, self).__init__(self.__class__.__name__,
                                           debug_logging,
                                           validate,
                                           verify_ssl)

    def login(self, email, password):
        """Authenticates the Mobileclient.
        Returns ``True`` on success, ``False`` on failure.

        :param email: eg ``'test@gmail.com'`` or just ``'test'``.
        :param password: password or app-specific password for 2-factor users.
          This is not stored locally, and is sent securely over SSL.

        Users of two-factor authentication will need to set an application-specific password
        to log in.
        """

        if not self.session.login(email, password):
            self.logger.info("failed to authenticate")
            return False

        self.logger.info("authenticated")

        return True

    #TODO expose max/page-results, updated_after, etc for list operations

    def get_all_songs(self, incremental=False, include_deleted=False):
        """Returns a list of dictionaries that each represent a song.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 tracks
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.

        :param include_deleted: if True, include tracks that have been deleted
          in the past.

        Here is an example song dictionary::

            {
               'comment':'',
               'rating':'0',
               'albumArtRef':[
                 {
                   'url': 'http://lh6.ggpht.com/...'
                 }
               ],
               'artistId':[
                 'Aod62yyj3u3xsjtooghh2glwsdi'
               ],
               'composer':'',
               'year':2011,
               'creationTimestamp':'1330879409467830',
               'id':'5924d75a-931c-30ed-8790-f7fce8943c85',
               'album':'Heritage ',
               'totalDiscCount':0,
               'title':'Haxprocess',
               'recentTimestamp':'1372040508935000',
               'albumArtist':'',
               'trackNumber':6,
               'discNumber':0,
               'deleted':False,
               'storeId':'Txsffypukmmeg3iwl3w5a5s3vzy',
               'nid':'Txsffypukmmeg3iwl3w5a5s3vzy',
               'totalTrackCount':10,
               'estimatedSize':'17229205',
               'albumId':'Bdkf6ywxmrhflvtasnayxlkgpcm',
               'beatsPerMinute':0,
               'genre':'Progressive Metal',
               'playCount':7,
               'artistArtRef':[
                 {
                   'url': 'http://lh3.ggpht.com/...'
                 }
               ],
               'kind':'sj#track',
               'artist':'Opeth',
               'lastModifiedTimestamp':'1330881158830924',
               'clientId':'+eGFGTbiyMktbPuvB5MfsA',
               'durationMillis':'418000'
             }

        """

        tracks = self._get_all_items(mobileclient.ListTracks, incremental, include_deleted)

        return tracks

    @utils.accept_singleton(dict)
    @utils.empty_arg_shortcircuit
    def change_song_metadata(self, songs):
        """Changes the metadata of tracks.
        Returns a list of the song ids changed.

        :param songs: a list of song dictionaries
          or a single song dictionary.

        Not all keys can be changed.
        These keys are known to work:

        * ``rating``: this is a string!
                      set to '0' (no thumb), '1' (down thumb), or '5' (up thumb)
                      unless you're using the 5-star ratings lab
        * ``album``
        * ``albumArtist``
        * ``artist``
        * ``comment``
        * ``composer``
        * ``discNumber``
        * ``genre``
        * ``playCount``
        * ``title``
        * ``totalDiscCount``
        * ``totalTrackCount``
        * ``trackNumber``
        * ``year``

        You can also use this to rate All Access tracks
        that aren't in your library, eg::

            song = mc.get_track_info('<some store track id>')
            song['rating'] = '5'
            mc.change_song_metadata(song)

        """

        mutate_call = mobileclient.BatchMutateTracks
        mutations = [{'update': s} for s in songs]
        self._make_call(mutate_call, mutations)

        #TODO
        # store tracks don't send back their id, so we're
        # forced to spoof this
        return [utils.id_or_nid(d) for d in songs]

    @utils.enforce_id_param
    def add_aa_track(self, aa_song_id):
        """Adds an All Access track to the library,
        returning the library track id.

        :param aa_song_id: All Access song id
        """
        #TODO is there a way to do this on multiple tracks at once?
        # problem is with gathering aa track info

        aa_track_info = self.get_track_info(aa_song_id)

        mutate_call = mobileclient.BatchMutateTracks
        add_mutation = mutate_call.build_track_add(aa_track_info)
        res = self._make_call(mutate_call, [add_mutation])

        return res['mutate_response'][0]['id']

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    def delete_songs(self, library_song_ids):
        """Deletes songs from the library.
        Returns a list of deleted song ids.

        :param song_ids: a list of song ids, or a single song id.
        """

        mutate_call = mobileclient.BatchMutateTracks
        del_mutations = mutate_call.build_track_deletes(library_song_ids)
        res = self._make_call(mutate_call, del_mutations)

        return [d['id'] for d in res['mutate_response']]

    @utils.enforce_id_param
    def get_stream_url(self, song_id, device_id):
        """Returns a url that will point to an mp3 file.

        :param song_id: a single song id
        :param device_id: a registered Android device id, as a 16 digit string.
          If you have already used Google Music on a mobile device,
          :func:`Webclient.get_registered_devices
          <gmusicapi.clients.Webclient.get_registered_devices>` will provide
          at least one working id. Omit ``'0x'`` from the start of the string.

          Note that this id must be from a mobile device; a registered computer
          id (as a MAC address) will not be accepted.

          Providing an invalid id will result in an http 403.

        When handling the resulting url, keep in mind that:
            * you will likely need to handle redirects
            * the url expires after a minute
            * only one IP can be streaming music at once.
              This can result in an http 403 with
              ``X-Rejected-Reason: ANOTHER_STREAM_BEING_PLAYED``.

        The file will not contain metadata.
        Use :func:`Webclient.get_song_download_info
        <gmusicapi.clients.Webclient.get_song_download_info>`
        or :func:`Musicmanager.download_song
        <gmusicapi.clients.Musicmanager.download_song>`
        to download files with metadata.
        """

        return self._make_call(mobileclient.GetStreamUrl, song_id, device_id)

    def get_all_playlists(self, incremental=False, include_deleted=False):
        """Returns a list of dictionaries that each represent a playlist.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 playlists
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.
        :param include_deleted: if True, include playlists that have been deleted
          in the past.

        Here is an example playlist dictionary::

            {
                 # can also be SHARED (public/subscribed to), MAGIC or omitted
                'type': 'USER_GENERATED',

                'kind': 'sj#playlist',
                'name': 'Something Mix',
                'deleted': False,
                'lastModifiedTimestamp': '1325458766483033',
                'recentTimestamp': '1325458766479000',
                'shareToken': '<long string>',
                'ownerProfilePhotoUrl': 'http://lh3.googleusercontent.com/...',
                'ownerName': 'Simon Weber',
                'accessControlled': False,  # has to do with shared playlists
                'creationTimestamp': '1325285553626172',
                'id': '3d72c9b5-baad-4ff7-815d-cdef717e5d61'
            }
        """

        playlists = self._get_all_items(mobileclient.ListPlaylists, incremental, include_deleted)

        return playlists

    # these could trivially support multiple creation/deletion, but
    # I chose to match the old webclient interface (at least for now).
    def create_playlist(self, name):
        """Creates a new empty playlist and returns its id.

        :param name: the desired title.
          Creating multiple playlists with the same name is allowed.
        """

        mutate_call = mobileclient.BatchMutatePlaylists
        add_mutations = mutate_call.build_playlist_adds([name])
        res = self._make_call(mutate_call, add_mutations)

        return res['mutate_response'][0]['id']

    @utils.enforce_id_param
    def change_playlist_name(self, playlist_id, new_name):
        """Changes the name of a playlist and returns its id.

        :param playlist_id: the id of the playlist
        :param new_name: desired title
        """

        mutate_call = mobileclient.BatchMutatePlaylists
        update_mutations = mutate_call.build_playlist_updates([(playlist_id, new_name)])
        res = self._make_call(mutate_call, update_mutations)

        return res['mutate_response'][0]['id']

    @utils.enforce_id_param
    def delete_playlist(self, playlist_id):
        """Deletes a playlist and returns its id.

        :param playlist_id: the id to delete.
        """
        #TODO accept multiple?

        mutate_call = mobileclient.BatchMutatePlaylists
        del_mutations = mutate_call.build_playlist_deletes([playlist_id])
        res = self._make_call(mutate_call, del_mutations)

        return res['mutate_response'][0]['id']

    def get_all_user_playlist_contents(self):
        """
        Retrieves the contents of *all* user-created playlists
        -- the Mobileclient does not support retrieving
        only the contents of one
        playlist.

        This will not return results for public playlists
        that the user is subscribed to; use :func:`get_shared_playlist_contents`
        instead.

        The same structure as :func:`get_all_playlists`
        will be returned, but
        with the addition of a ``'tracks'`` key in each dict
        set to a list of properly-ordered playlist entry dicts.

        Here is an example playlist entry::

          {
              'kind': 'sj#playlistEntry',
              'deleted': False,
              'trackId': '2bb0ab1c-ce1a-3c0f-9217-a06da207b7a7',
              'lastModifiedTimestamp': '1325285553655027',
              'playlistId': '3d72c9b5-baad-4ff7-815d-cdef717e5d61',
              'absolutePosition': '01729382256910287871',  # denotes playlist ordering
              'source': '1',  # ??
              'creationTimestamp': '1325285553655027',
              'id': 'c9f1aff5-f93d-4b98-b13a-429cc7972fea'
          }
        """

        user_playlists = [p for p in self.get_all_playlists()
                          if (p.get('type') == 'USER_GENERATED' or
                              p.get('type') != 'SHARED' or
                              'type' not in p)]

        all_entries = self._get_all_items(mobileclient.ListPlaylistEntries,
                                          incremental=False, include_deleted=False,
                                          updated_after=None)

        for playlist in user_playlists:
            #TODO could use a dict to make this faster
            entries = [e for e in all_entries
                       if e['playlistId'] == playlist['id']]
            entries.sort(key=itemgetter('absolutePosition'))

            playlist['tracks'] = entries

        return user_playlists

    def get_shared_playlist_contents(self, share_token):
        """
        Retrieves the contents of a public All Access playlist.

        :param share_token: from ``playlist['shareToken']``, or a playlist share
          url (``https://play.google.com/music/playlist/<token>``).

          Note that tokens from urls will need to be url-decoded,
          eg ``AM...%3D%3D`` becomes ``AM...==``.

        For example, to retrieve the contents of a playlist that the user is
        subscribed to::
            subscribed_to = [p for p in mc.get_all_playlists() if p.get('type') == 'SHARED']
            share_tok = subscribed_to[0]['shareToken']
            tracks = mc.get_shared_playlist_contents(share_tok)

        The user need not be subscribed to a playlist to list its tracks.

        Returns a list of playlist entries
        with structure the same as those
        returned by :func:`get_all_user_playlist_contents`,
        but without the ``'clientId'`` or ``'playlistId'`` keys.
        """

        res = self._make_call(mobileclient.ListSharedPlaylistEntries,
                              updated_after=None, share_token=share_token)

        entries = res['entries'][0]['playlistEntry']
        entries.sort(key=itemgetter('absolutePosition'))

        return entries

    @utils.accept_singleton(basestring, 2)
    @utils.enforce_id_param
    @utils.enforce_ids_param(position=2)
    @utils.empty_arg_shortcircuit(position=2)
    def add_songs_to_playlist(self, playlist_id, song_ids):
        """Appends songs to the end of a playlist.
        Returns a list of playlist entry ids that were added.

        :param playlist_id: the id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """
        mutate_call = mobileclient.BatchMutatePlaylistEntries
        add_mutations = mutate_call.build_plentry_adds(playlist_id, song_ids)
        res = self._make_call(mutate_call, add_mutations)

        return [e['id'] for e in res['mutate_response']]

    @utils.accept_singleton(basestring, 1)
    @utils.enforce_ids_param(position=1)
    @utils.empty_arg_shortcircuit(position=1)
    def remove_entries_from_playlist(self, entry_ids):
        """Removes specific entries from a playlist.
        Returns a list of entry ids that were removed.

        :param entry_ids: a list of entry ids, or a single entry id.
        """
        mutate_call = mobileclient.BatchMutatePlaylistEntries
        del_mutations = mutate_call.build_plentry_deletes(entry_ids)
        res = self._make_call(mutate_call, del_mutations)

        return [e['id'] for e in res['mutate_response']]

    def reorder_playlist_entry(self, entry, to_follow_entry=None, to_precede_entry=None):
        """Reorders a single entry in a playlist and returns its id.

        Read ``reorder_playlist_entry(foo, bar, gaz)`` as
        "reorder playlist entry *foo* to follow entry *bar*
        and precede entry *gaz*."

        :param entry: the playlist entry to move.
        :param to_follow_entry: the playlist entry
          that will come before *entry* in the resulting playlist,
          or None if *entry* is to be the first entry in the playlist.
        :param to_precede_entry: the playlist entry
          that will come after *entry* in the resulting playlist
          or None if *entry* is to be the last entry in the playlist.

        ``reorder_playlist_entry(foo)`` is invalid and will raise ValueError;
        provide at least one of *to_follow_entry* or *to_precede_entry*.

        Leaving *to_follow_entry* or *to_precede_entry* as None when
        *entry* is not to be the first or last entry in the playlist
        is undefined.

        All params are dicts returned by
        :func:`get_all_user_playlist_contents` or
        :func:`get_shared_playlist_contents`.

        """

        if to_follow_entry is None and to_precede_entry is None:
            raise ValueError('either to_follow_entry or to_precede_entry must be provided')

        mutate_call = mobileclient.BatchMutatePlaylistEntries
        before = to_follow_entry['clientId'] if to_follow_entry else None
        after = to_precede_entry['clientId'] if to_precede_entry else None

        reorder_mutation = mutate_call.build_plentry_reorder(entry, before, after)
        res = self._make_call(mutate_call, [reorder_mutation])

        return [e['id'] for e in res['mutate_response']]

    # WIP, see issue #179
    #def reorder_playlist(self, reordered_playlist, orig_playlist=None):
    #    """TODO"""

    #    if not reordered_playlist['tracks']:
    #        #TODO what to return?
    #        return

    #    if orig_playlist is None:
    #        #TODO get pl from server
    #        pass

    #    if len(reordered_playlist['tracks']) != len(orig_playlist['tracks']):
    #        raise ValueError('the original playlist does not have the same number of'
    #                         ' tracks as the reordered playlist')

    #    # find the minimum number of mutations to match the orig playlist

    #    orig_tracks = orig_playlist['tracks']
    #    orig_tracks_id_to_idx = dict([(t['id'], i) for (i, t) in enumerate(orig_tracks)])

    #    re_tracks = reordered_playlist['tracks']
    #    re_tracks_id_to_idx = dict([(t['id'], i) for (i, t) in enumerate(re_tracks)])

    #    translated_re_tracks = [orig_tracks_id_to_idx[t['id']] for t in re_tracks]

    #    lis = utils.longest_increasing_subseq(translated_re_tracks)

    #    idx_to_move = set(range(len(orig_tracks))) - set(lis)

    #    idx_pos_pairs = [(i, re_tracks_id_to_idx[orig_tracks[i]['id']])
    #                     for i in idx_to_move]

    #    #TODO build out mutations

    #    return idx_pos_pairs

    #@staticmethod
    #def _create_ple_reorder_mutations(tracks, from_to_idx_pairs):
    #    """
    #    Return a list of mutations.

    #    :param tracks: orig_playlist['tracks']
    #    :param from_to_idx_pairs: [(from_index, to_index)]
    #    """
    #    for from_idx, to_idx in sorted(key=itemgetter(1)
    #    playlist_len = len(self.plentry_ids)
    #    for from_pos, to_pos in [pair for pair in
    #                             itertools.product(range(playlist_len), repeat=2)
    #                             if pair[0] < pair[1]]:
    #        pl = self.mc_get_playlist_songs(self.playlist_id)

    #        from_e = pl[from_pos]

    #        e_before_new_pos, e_after_new_pos = None, None

    #        if to_pos - 1 >= 0:
    #            e_before_new_pos = pl[to_pos]

    #        if to_pos + 1 < playlist_len:
    #            e_after_new_pos = pl[to_pos + 1]

    #        self.mc.reorder_playlist_entry(from_e,
    #                                       to_follow_entry=e_before_new_pos,
    #                                       to_precede_entry=e_after_new_pos)
    #        self._mc_assert_ple_position(from_e, to_pos)

    #        if e_before_new_pos:
    #            self._mc_assert_ple_position(e_before_new_pos, to_pos - 1)

    #        if e_after_new_pos:
    #            self._mc_assert_ple_position(e_after_new_pos, to_pos + 1)

    def create_station(self, name,
                       track_id=None, artist_id=None, album_id=None,
                       genre_id=None):
        """Creates an All Access radio station and returns its id.

        :param name: the name of the station to create
        :param \*_id: the id of an item to seed the station from.
          Exactly one of these params must be provided, or ValueError
          will be raised.
        """
        #TODO could expose include_tracks

        seed = {}
        if track_id is not None:
            if track_id[0] == 'T':
                seed['trackId'] = track_id
            else:
                seed['trackLockerId'] = track_id

        if artist_id is not None:
            seed['artistId'] = artist_id
        if album_id is not None:
            seed['albumId'] = album_id
        if genre_id is not None:
            seed['genreId'] = genre_id

        if len(seed) != 1:
            raise ValueError('exactly one {track,artist,album,genre}_id must be provided')

        mutate_call = mobileclient.BatchMutateStations
        add_mutation = mutate_call.build_add(name, seed, include_tracks=False, num_tracks=0)
        res = self._make_call(mutate_call, [add_mutation])

        return res['mutate_response'][0]['id']

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    def delete_stations(self, station_ids):
        """Deletes All Access radio stations and returns their ids.

        :param station_ids: a single id, or a list of ids to delete
        """

        mutate_call = mobileclient.BatchMutateStations
        delete_mutations = mutate_call.build_deletes(station_ids)
        res = self._make_call(mutate_call, delete_mutations)

        return [s['id'] for s in res['mutate_response']]

    def get_all_stations(self, incremental=False, include_deleted=False, updated_after=None):
        """Returns a list of dictionaries that each represent a radio station.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 stations
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.
        :param include_deleted: if True, include stations that have been deleted
          in the past.
        :param updated_after: a datetime.datetime; defaults to unix epoch

        Here is an example station dictionary::

            {
                'imageUrl': 'http://lh6.ggpht.com/...',
                'kind': 'sj#radioStation',
                'name': 'station',
                'deleted': False,
                'lastModifiedTimestamp': '1370796487455005',
                'recentTimestamp': '1370796487454000',
                'clientId': 'c2639bf4-af24-4e4f-ab37-855fc89d15a1',
                'seed':
                {
                    'kind': 'sj#radioSeed',
                    'trackLockerId': '7df3aadd-9a18-3dc1-b92e-a7cf7619da7e'
                    # possible keys:
                    #  albumId, artistId, genreId, trackId, trackLockerId
                },
                'id': '69f1bfce-308a-313e-9ed2-e50abe33a25d'
            },
        """
        return self._get_all_items(mobileclient.ListStations, incremental, include_deleted,
                                   updated_after=updated_after)

    @utils.enforce_id_param
    def get_station_tracks(self, station_id, num_tracks=25):
        """Returns a list of dictionaries that each represent a track.

        Each call performs a separate sampling (with replacement?)
        from all possible tracks for the station.

        :param station_id: the id of a radio station to retrieve tracks from
        :param num_tracks: the number of tracks to retrieve

        See :func:`get_all_songs` for the format of a track dictionary.
        """

        #TODO recently played?

        res = self._make_call(mobileclient.ListStationTracks,
                              station_id, num_tracks, recently_played=[])

        if not res['data']['items']:
            return []

        return res['data']['items'][0].get('tracks', [])

    def search_all_access(self, query, max_results=50):
        """Queries the server for All Access songs and albums.

        Using this method without an All Access subscription will always result in
        CallFailure being raised.

        :param query: a string keyword to search with. Capitalization and punctuation are ignored.
        :param max_results: Maximum number of items to be retrieved

        The results are returned in a dictionary, arranged by how they were found.
        Here are example results for a search on ``'Amorphis'``::

            {
               'album_hits':[
                  {
                     'album':{
                        'albumArtRef':'http://lh6.ggpht.com/...',
                        'albumId':'Bfr2onjv7g7tm4rzosewnnwxxyy',
                        'artist':'Amorphis',
                        'artistId':[
                           'Apoecs6off3y6k4h5nvqqos4b5e'
                        ],
                        'kind':'sj#album',
                        'name':'Circle',
                        'year':2013
                     },
                     'best_result':True,
                     'score':385.55609130859375,
                     'type':'3'
                  },
                  {
                     'album':{
                        'albumArtRef':'http://lh3.ggpht.com/...',
                        'albumArtist':'Amorphis',
                        'albumId':'Bqzxfykbqcqmjjtdom7ukegaf2u',
                        'artist':'Amorphis',
                        'artistId':[
                           'Apoecs6off3y6k4h5nvqqos4b5e'
                        ],
                        'kind':'sj#album',
                        'name':'Elegy',
                        'year':1996
                     },
                     'score':236.33485412597656,
                     'type':'3'
                  },
               ],
               'artist_hits':[
                  {
                     'artist':{
                        'artistArtRef':'http://lh6.ggpht.com/...',
                        'artistId':'Apoecs6off3y6k4h5nvqqos4b5e',
                        'kind':'sj#artist',
                        'name':'Amorphis'
                     },
                     'score':237.86375427246094,
                     'type':'2'
                  }
               ],
               'song_hits':[
                  {
                     'score':105.23198699951172,
                     'track':{
                        'album':'Skyforger',
                        'albumArtRef':[
                           {
                              'url':'http://lh4.ggpht.com/...'
                           }
                        ],
                        'albumArtist':'Amorphis',
                        'albumAvailableForPurchase':True,
                        'albumId':'B5nc22xlcmdwi3zn5htkohstg44',
                        'artist':'Amorphis',
                        'artistId':[
                           'Apoecs6off3y6k4h5nvqqos4b5e'
                        ],
                        'discNumber':1,
                        'durationMillis':'253000',
                        'estimatedSize':'10137633',
                        'kind':'sj#track',
                        'nid':'Tn2ugrgkeinrrb2a4ji7khungoy',
                        'playCount':1,
                        'storeId':'Tn2ugrgkeinrrb2a4ji7khungoy',
                        'title':'Silver Bride',
                        'trackAvailableForPurchase':True,
                        'trackNumber':2,
                        'trackType':'7'
                     },
                     'type':'1'
                  },
                  {
                     'score':96.23717498779297,
                     'track':{
                        'album':'Magic And Mayhem - Tales From The Early Years',
                        'albumArtRef':[
                           {
                              'url':'http://lh4.ggpht.com/...'
                           }
                        ],
                        'albumArtist':'Amorphis',
                        'albumAvailableForPurchase':True,
                        'albumId':'B7dplgr5h2jzzkcyrwhifgwl2v4',
                        'artist':'Amorphis',
                        'artistId':[
                           'Apoecs6off3y6k4h5nvqqos4b5e'
                        ],
                        'discNumber':1,
                        'durationMillis':'235000',
                        'estimatedSize':'9405159',
                        'kind':'sj#track',
                        'nid':'T4j5jxodzredqklxxhncsua5oba',
                        'storeId':'T4j5jxodzredqklxxhncsua5oba',
                        'title':'Black Winter Day',
                        'trackAvailableForPurchase':True,
                        'trackNumber':4,
                        'trackType':'7',
                        'year':2010
                     },
                     'type':'1'
                  },
               ]
            }
        """
        res = self._make_call(mobileclient.Search, query, max_results)

        hits = res.get('entries', [])

        return {'album_hits': [hit for hit in hits if hit['type'] == '3'],
                'artist_hits': [hit for hit in hits if hit['type'] == '2'],
                'song_hits': [hit for hit in hits if hit['type'] == '1']}

    @utils.enforce_id_param
    def get_artist_info(self, artist_id, include_albums=True, max_top_tracks=5, max_rel_artist=5):
        """Retrieves details on an artist.

        :param artist_id: an All Access artist id (hint: they always start with 'A')
        :param include_albums: when True, create the ``'albums'`` substructure
        :param max_top_tracks: maximum number of top tracks to retrieve
        :param max_rel_artist: maximum number of related artists to retrieve

        Using this method without an All Access subscription will always result in
        CallFailure being raised.

        Returns a dict, eg::

            {
              'albums':[  # only if include_albums is True
                {
                  'albumArtRef':'http://lh6.ggpht.com/...',
                  'albumArtist':'Amorphis',
                  'albumId':'Bfr2onjv7g7tm4rzosewnnwxxyy',
                  'artist':'Amorphis',
                  'artistId':[
                    'Apoecs6off3y6k4h5nvqqos4b5e'
                  ],
                  'kind':'sj#album',
                  'name':'Circle',
                  'year':2013
                },
              ],
              'artistArtRef':  'http://lh6.ggpht.com/...',
              'artistId':'Apoecs6off3y6k4h5nvqqos4b5e',
              'kind':'sj#artist',
              'name':'Amorphis',
              'related_artists':[  # only if max_rel_artists > 0
                {
                  'artistArtRef':      'http://lh5.ggpht.com/...',
                  'artistId':'Aheqc7kveljtq7rptd7cy5gvk2q',
                  'kind':'sj#artist',
                  'name':'Dark Tranquillity'
                }
              ],
              'topTracks':[  # only if max_top_tracks > 0
                {
                  'album':'Skyforger',
                  'albumArtRef':[
                    {
                      'url':          'http://lh4.ggpht.com/...'
                    }
                  ],
                  'albumArtist':'Amorphis',
                  'albumAvailableForPurchase':True,
                  'albumId':'B5nc22xlcmdwi3zn5htkohstg44',
                  'artist':'Amorphis',
                  'artistId':[
                    'Apoecs6off3y6k4h5nvqqos4b5e'
                  ],
                  'discNumber':1,
                  'durationMillis':'253000',
                  'estimatedSize':'10137633',
                  'kind':'sj#track',
                  'nid':'Tn2ugrgkeinrrb2a4ji7khungoy',
                  'playCount':1,
                  'storeId':'Tn2ugrgkeinrrb2a4ji7khungoy',
                  'title':'Silver Bride',
                  'trackAvailableForPurchase':True,
                  'trackNumber':2,
                  'trackType':'7'
                }
              ],
              'total_albums':21
            }
        """

        res = self._make_call(mobileclient.GetArtist,
                              artist_id, include_albums, max_top_tracks, max_rel_artist)
        return res

    def _get_all_items(self, call, incremental, include_deleted, **kwargs):
        """
        :param call: protocol.McCall
        :param incremental: bool
        :param include_deleted: bool

        kwargs are passed to the call.
        """
        if not incremental:
            # slight optimization: get more items in a page
            kwargs.setdefault('max_results', 20000)

        generator = self._get_all_items_incremental(call, include_deleted, **kwargs)
        if incremental:
            return generator

        return [s for chunk in generator for s in chunk]

    def _get_all_items_incremental(self, call, include_deleted, **kwargs):
        """Return a generator of lists of tracks.

        kwargs are passed to the call."""

        get_next_chunk = True
        lib_chunk = {'nextPageToken': None}

        while get_next_chunk:
            lib_chunk = self._make_call(call,
                                        start_token=lib_chunk['nextPageToken'],
                                        **kwargs)

            items = lib_chunk['data']['items']

            if not include_deleted:
                items = [item for item in items if not item['deleted']]

            yield items

            get_next_chunk = 'nextPageToken' in lib_chunk

    @utils.enforce_id_param
    def get_album_info(self, album_id, include_tracks=True):
        """Retrieves details on an album.

        :param album_id: an All Access album id (hint: they always start with 'B')
        :param include_tracks: when True, create the ``'tracks'`` substructure

        Using this method without an All Access subscription will always result in
        CallFailure being raised.

        Returns a dict, eg::

            {
                'kind': 'sj#album',
                'name': 'Circle',
                'artist': 'Amorphis',
                'albumArtRef': 'http://lh6.ggpht.com/...',
                'tracks': [  # if `include_tracks` is True
                {
                    'album': 'Circle',
                    'kind': 'sj#track',
                    'storeId': 'T5zb7luo2vkroozmj57g2nljdsy',  # can be used as a song id
                    'artist': 'Amorphis',
                    'albumArtRef': [
                    {
                        'url': 'http://lh6.ggpht.com/...'
                    }],
                    'title': 'Shades of Grey',
                    'nid': 'T5zb7luo2vkroozmj57g2nljdsy',
                    'estimatedSize': '13115591',
                    'albumId': 'Bfr2onjv7g7tm4rzosewnnwxxyy',
                    'artistId': ['Apoecs6off3y6k4h5nvqqos4b5e'],
                    'albumArtist': 'Amorphis',
                    'durationMillis': '327000',
                    'composer': '',
                    'genre': 'Metal',
                    'trackNumber': 1,
                    'discNumber': 1,
                    'trackAvailableForPurchase': True,
                    'trackType': '7',
                    'albumAvailableForPurchase': True
                }, # ...
                ],
                'albumId': 'Bfr2onjv7g7tm4rzosewnnwxxyy',
                'artistId': ['Apoecs6off3y6k4h5nvqqos4b5e'],
                'albumArtist': 'Amorphis',
                'year': 2013
            }

        """

        return self._make_call(mobileclient.GetAlbum, album_id, include_tracks)

    @utils.enforce_id_param
    def get_track_info(self, store_track_id):
        """Retrieves information about a store track.

        :param store_track_id: an All Access track id (hint: they always start with 'T')

        Using this method without an All Access subscription will always result in
        CallFailure being raised.

        Returns a dict, eg::

            {
                'album': 'Best Of',
                'kind': 'sj#track',
                'storeId': 'Te2qokfjmhqxw4bnkswbfphzs4m',
                'artist': 'Amorphis',
                'albumArtRef': [
                {
                    'url': 'http://lh5.ggpht.com/...'
                }],
                'title': 'Hopeless Days',
                'nid': 'Te2qokfjmhqxw4bnkswbfphzs4m',
                'estimatedSize': '12325643',
                'albumId': 'Bsbjjc24a5xutbutvbvg3h4y2k4',
                'artistId': ['Apoecs6off3y6k4h5nvqqos4b5e'],
                'albumArtist': 'Amorphis',
                'durationMillis': '308000',
                'composer': '',
                'genre': 'Metal',
                'trackNumber': 2,
                'discNumber': 1,
                'trackAvailableForPurchase': True,
                'trackType': '7',
                'albumAvailableForPurchase': True
            }

        """

        return self._make_call(mobileclient.GetStoreTrack, store_track_id)

    def get_genres(self):
        """Retrieves information on Google Music genres.

        Using this method without an All Access subscription will always result in
        CallFailure being raised.

        Returns a list of dicts of the form, eg::

            {
                'name': 'Alternative/Indie',
                'id': 'ALTERNATIVE_INDIE'
                'kind': 'sj#musicGenre',
                'children': [             # this key may not be present
                    'ALTERNATIVE_80S',    # these are ids
                    'ALT_COUNTRY',
                    # ...
                    ],
                'images': [
                    {
                        # these are album covers representative of the genre
                        'url': 'http://lh6.ggpht.com/...'
                    },
                    # ...
                ],
            }

        Note that the id can be used with :func:`create_station`
        to seed an All Access radio station.
        """

        return self._make_call(mobileclient.GetGenres)
