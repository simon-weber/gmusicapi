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
    def __init__(self, debug_logging=True, validate=True):
        self.session = session.Webclient()

        super(Mobileclient, self).__init__(self.__class__.__name__, debug_logging, validate)
        self.logout()

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

    #TODO expose max-results, updated_after, etc for list operations

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
               u'comment':u'',
               u'rating':u'0',
               u'albumArtRef':[
                 {
                   u'url': u'http://lh6.ggpht.com/...'
                 }
               ],
               u'artistId':[
                 u'Aod62yyj3u3xsjtooghh2glwsdi'
               ],
               u'composer':u'',
               u'year':2011,
               u'creationTimestamp':u'1330879409467830',
               u'id':u'5924d75a-931c-30ed-8790-f7fce8943c85',
               u'album':u'Heritage ',
               u'totalDiscCount':0,
               u'title':u'Haxprocess',
               u'recentTimestamp':u'1372040508935000',
               u'albumArtist':u'',
               u'trackNumber':6,
               u'discNumber':0,
               u'deleted':False,
               u'storeId':u'Txsffypukmmeg3iwl3w5a5s3vzy',
               u'nid':u'Txsffypukmmeg3iwl3w5a5s3vzy',
               u'totalTrackCount':10,
               u'estimatedSize':u'17229205',
               u'albumId':u'Bdkf6ywxmrhflvtasnayxlkgpcm',
               u'beatsPerMinute':0,
               u'genre':u'Progressive Metal',
               u'playCount':7,
               u'artistArtRef':[
                 {
                   u'url': u'http://lh3.ggpht.com/...'
                 }
               ],
               u'kind':u'sj#track',
               u'artist':u'Opeth',
               u'lastModifiedTimestamp':u'1330881158830924',
               u'clientId':u'+eGFGTbiyMktbPuvB5MfsA',
               u'durationMillis':u'418000'
             }
        """

        tracks = self._get_all_items(mobileclient.ListTracks, incremental, include_deleted)

        return tracks

    def add_aa_track(self, aa_song_id):
        """Adds an All Access track to the library,
        returning the library track id.

        :param aa_song_id: All Access song id
        """
        #TODO is there a way to do this on multiple tracks at once?
        # problem is with gathering aa track info

        aa_track_info = self.get_track(aa_song_id)

        mutate_call = mobileclient.BatchMutateTracks
        add_mutation = mutate_call.build_track_add(aa_track_info)
        res = self._make_call(mutate_call, [add_mutation])

        return res['mutate_response'][0]['id']

    @utils.accept_singleton(basestring)
    @utils.empty_arg_shortcircuit
    @utils.enforce_ids_param
    def delete_songs(self, library_song_ids):
        """Deletes songs from the library.
        Returns a list of deleted song ids.

        :param song_ids: a list of song ids, or a single song id.
        """

        mutate_call = mobileclient.BatchMutateTracks
        del_mutations = mutate_call.build_track_deletes(library_song_ids)
        res = self._make_call(mutate_call, del_mutations)

        return [d['id'] for d in res['mutate_response']]

    def get_stream_url(self, song_id, device_id):
        """Returns a url that will point to an mp3 file.

        :param song_id: a single song id
        :param device_id: a registered Android device id, as a string.
          If you have already used Google Music on a mobile device,
          :func:`Webclient.get_registered_devices
          <gmusicapi.clients.Webclient.get_registered_devices>` will provide
          at least one working id.

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
                u 'kind': u 'sj#playlist',
                u 'name': u 'Something Mix',
                u 'deleted': False,
                u 'type': u 'MAGIC',  # if not present, playlist is user-created
                u 'lastModifiedTimestamp': u '1325458766483033',
                u 'recentTimestamp': u '1325458766479000',
                u 'shareToken': u '<long string>',
                u 'ownerProfilePhotoUrl': u 'http://lh3.googleusercontent.com/...',
                u 'ownerName': u 'Simon Weber',
                u 'accessControlled': False,  # something to do with shared playlists?
                u 'creationTimestamp': u '1325285553626172',
                u 'id': u '3d72c9b5-baad-4ff7-815d-cdef717e5d61'
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

    def delete_playlist(self, playlist_id):
        """Deletes a playlist and returns its id.

        :param playlist_id: the id to delete.
        """

        mutate_call = mobileclient.BatchMutatePlaylists
        del_mutations = mutate_call.build_playlist_deletes([playlist_id])
        res = self._make_call(mutate_call, del_mutations)

        return res['mutate_response'][0]['id']

    def get_all_stations(self, incremental=False, include_deleted=False, updated_after=None):
        """Returns a list of dictionaries that each represent a radio station.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 stations
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.
        :param include_deleted: if True, include stations that have been deleted
          in the past.
        :param updated_after: a datetime.datetime; defaults to epoch

        Here is an example station dictionary::
            {
                u 'imageUrl': u 'http://lh6.ggpht.com/...',
                u 'kind': u 'sj#radioStation',
                u 'name': u 'station',
                u 'deleted': False,
                u 'lastModifiedTimestamp': u '1370796487455005',
                u 'recentTimestamp': u '1370796487454000',
                u 'clientId': u 'c2639bf4-af24-4e4f-ab37-855fc89d15a1',
                u 'seed':
                {
                    u 'kind': u 'sj#radioSeed',
                    u 'trackLockerId': u '7df3aadd-9a18-3dc1-b92e-a7cf7619da7e'
                    # possible keys:
                    #  albumId, artistId, genreId, trackId, trackLockerId
                },
                u 'id': u '69f1bfce-308a-313e-9ed2-e50abe33a25d'
            },
        """
        return self._get_all_items(mobileclient.ListStations, incremental, include_deleted,
                                   updated_after=updated_after)

    def search_all_access(self, query, max_results=50):
        """Queries the server for All Access songs and albums.

        Using this method without an All Access subscription will always result in
        CallFailure being raised.

        :param query: a string keyword to search with. Capitalization and punctuation are ignored.
        :param max_results: Maximum number of items to be retrieved

        The results are returned in a dictionary, arranged by how they were found, eg::
            {
               'album_hits':[
                  {
                     u'album':{
                        u'albumArtRef':u'http://lh6.ggpht.com/...',
                        u'albumId':u'Bfr2onjv7g7tm4rzosewnnwxxyy',
                        u'artist':u'Amorphis',
                        u'artistId':[
                           u'Apoecs6off3y6k4h5nvqqos4b5e'
                        ],
                        u'kind':u'sj#album',
                        u'name':u'Circle',
                        u'year':2013
                     },
                     u'best_result':True,
                     u'score':385.55609130859375,
                     u'type':u'3'
                  },
                  {
                     u'album':{
                        u'albumArtRef':u'http://lh3.ggpht.com/...',
                        u'albumArtist':u'Amorphis',
                        u'albumId':u'Bqzxfykbqcqmjjtdom7ukegaf2u',
                        u'artist':u'Amorphis',
                        u'artistId':[
                           u'Apoecs6off3y6k4h5nvqqos4b5e'
                        ],
                        u'kind':u'sj#album',
                        u'name':u'Elegy',
                        u'year':1996
                     },
                     u'score':236.33485412597656,
                     u'type':u'3'
                  },
               ],
               'artist_hits':[
                  {
                     u'artist':{
                        u'artistArtRef':u'http://lh6.ggpht.com/...',
                        u'artistId':u'Apoecs6off3y6k4h5nvqqos4b5e',
                        u'kind':u'sj#artist',
                        u'name':u'Amorphis'
                     },
                     u'score':237.86375427246094,
                     u'type':u'2'
                  }
               ],
               'song_hits':[
                  {
                     u'score':105.23198699951172,
                     u'track':{
                        u'album':u'Skyforger',
                        u'albumArtRef':[
                           {
                              u'url':u'http://lh4.ggpht.com/...'
                           }
                        ],
                        u'albumArtist':u'Amorphis',
                        u'albumAvailableForPurchase':True,
                        u'albumId':u'B5nc22xlcmdwi3zn5htkohstg44',
                        u'artist':u'Amorphis',
                        u'artistId':[
                           u'Apoecs6off3y6k4h5nvqqos4b5e'
                        ],
                        u'discNumber':1,
                        u'durationMillis':u'253000',
                        u'estimatedSize':u'10137633',
                        u'kind':u'sj#track',
                        u'nid':u'Tn2ugrgkeinrrb2a4ji7khungoy',
                        u'playCount':1,
                        u'storeId':u'Tn2ugrgkeinrrb2a4ji7khungoy',
                        u'title':u'Silver Bride',
                        u'trackAvailableForPurchase':True,
                        u'trackNumber':2,
                        u'trackType':u'7'
                     },
                     u'type':u'1'
                  },
                  {
                     u'score':96.23717498779297,
                     u'track':{
                        u'album':u'Magic And Mayhem - Tales From The Early Years',
                        u'albumArtRef':[
                           {
                              u'url':u'http://lh4.ggpht.com/...'
                           }
                        ],
                        u'albumArtist':u'Amorphis',
                        u'albumAvailableForPurchase':True,
                        u'albumId':u'B7dplgr5h2jzzkcyrwhifgwl2v4',
                        u'artist':u'Amorphis',
                        u'artistId':[
                           u'Apoecs6off3y6k4h5nvqqos4b5e'
                        ],
                        u'discNumber':1,
                        u'durationMillis':u'235000',
                        u'estimatedSize':u'9405159',
                        u'kind':u'sj#track',
                        u'nid':u'T4j5jxodzredqklxxhncsua5oba',
                        u'storeId':u'T4j5jxodzredqklxxhncsua5oba',
                        u'title':u'Black Winter Day',
                        u'trackAvailableForPurchase':True,
                        u'trackNumber':4,
                        u'trackType':u'7',
                        u'year':2010
                     },
                     u'type':u'1'
                  },
               ]
            }
        """
        res = self._make_call(mobileclient.Search, query, max_results)['entries']

        return {'album_hits': [hit for hit in res if hit['type'] == '3'],
                'artist_hits': [hit for hit in res if hit['type'] == '2'],
                'song_hits': [hit for hit in res if hit['type'] == '1']}

    def get_artist_info(self, artist_id, include_albums=True, max_top_tracks=5, max_rel_artist=5):
        """Retrieve details on an artist.

        Using this method without an All Access subscription will always result in
        CallFailure being raised.

        Returns a dict, eg::
            {
              u'albums':[  # only if include_albums is True
                {
                  u'albumArtRef':u'http://lh6.ggpht.com/...',
                  u'albumArtist':u'Amorphis',
                  u'albumId':u'Bfr2onjv7g7tm4rzosewnnwxxyy',
                  u'artist':u'Amorphis',
                  u'artistId':[
                    u'Apoecs6off3y6k4h5nvqqos4b5e'
                  ],
                  u'kind':u'sj#album',
                  u'name':u'Circle',
                  u'year':2013
                },
              ],
              u'artistArtRef':  u'http://lh6.ggpht.com/...',
              u'artistId':u'Apoecs6off3y6k4h5nvqqos4b5e',
              u'kind':u'sj#artist',
              u'name':u'Amorphis',
              u'related_artists':[  # only if max_rel_artists > 0
                {
                  u'artistArtRef':      u'http://lh5.ggpht.com/...',
                  u'artistId':u'Aheqc7kveljtq7rptd7cy5gvk2q',
                  u'kind':u'sj#artist',
                  u'name':u'Dark Tranquillity'
                }
              ],
              u'topTracks':[  # only if max_top_tracks > 0
                {
                  u'album':u'Skyforger',
                  u'albumArtRef':[
                    {
                      u'url':          u'http://lh4.ggpht.com/...'
                    }
                  ],
                  u'albumArtist':u'Amorphis',
                  u'albumAvailableForPurchase':True,
                  u'albumId':u'B5nc22xlcmdwi3zn5htkohstg44',
                  u'artist':u'Amorphis',
                  u'artistId':[
                    u'Apoecs6off3y6k4h5nvqqos4b5e'
                  ],
                  u'discNumber':1,
                  u'durationMillis':u'253000',
                  u'estimatedSize':u'10137633',
                  u'kind':u'sj#track',
                  u'nid':u'Tn2ugrgkeinrrb2a4ji7khungoy',
                  u'playCount':1,
                  u'storeId':u'Tn2ugrgkeinrrb2a4ji7khungoy',
                  u'title':u'Silver Bride',
                  u'trackAvailableForPurchase':True,
                  u'trackNumber':2,
                  u'trackType':u'7'
                }
              ],
              u'total_albums':21
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
            # slight optimization; can get all items at once
            res = self._make_call(call, max_results=20000, **kwargs)

            items = res['data']['items']

            if not include_deleted:
                items = [t for t in items if not t['deleted']]

            return items

        # otherwise, return a generator
        return self._get_all_items_incremental(call, include_deleted, **kwargs)

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

    #TODO below here
    def get_album(self, albumid, tracks=True):
        """Retrieve artist data"""
        res = self._make_call(mobileclient.GetAlbum, albumid, tracks)
        return res

    def get_track(self, trackid):
        """Retrieve information about a store track.

        TODO does this work on library tracks?
        """
        res = self._make_call(mobileclient.GetStoreTrack, trackid)
        return res
