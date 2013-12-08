# -*- coding: utf-8 -*-

from urlparse import urlparse, parse_qsl

import gmusicapi
from gmusicapi.clients.shared import _Base
from gmusicapi.protocol import webclient
from gmusicapi.utils import utils
import gmusicapi.session


class Webclient(_Base):
    """Allows library management and streaming by posing as the
    music.google.com webclient.

    Uploading is not supported by this client (use the :class:`Musicmanager`
    to upload).

    Any methods in this class that are duplicated by
    the :class:`Mobileclient` should be considered deprecated.
    The following methods are *not* deprecated:

        * :func:`get_registered_devices`
        * :func:`get_song_download_info`
        * :func:`get_stream_urls`
        * :func:`get_stream_audio`
        * :func:`report_incorrect_match`
        * :func:`upload_album_art`
    """

    _session_class = gmusicapi.session.Webclient

    def __init__(self, debug_logging=True, validate=True, verify_ssl=True):
        super(Webclient, self).__init__(self.__class__.__name__,
                                        debug_logging,
                                        validate,
                                        verify_ssl)

    def login(self, email, password):
        """Authenticates the webclient.
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

    def logout(self):
        return super(Webclient, self).logout()

    def get_registered_devices(self):
        """
        Returns a list of dictionaries representing devices associated with the account.

        Performing the :class:`Musicmanager` OAuth flow will register a device
        of type ``'DESKTOP_APP'``.

        Installing the Android Google Music app and logging into it will
        register a device of type ``'PHONE'``, which is required for streaming with
        the :class:`Mobileclient`.

        Here is an example response::

            [
              {
                u'date': 1367470393588,           # utc-millisecond
                u'id':   u'AA:BB:CC:11:22:33',
                u'name': u'my-hostname',
                u'type': u'DESKTOP_APP'
               },
               {
                u'carrier':      u'Google',
                u'date':         1344808742774,
                u'id':           u'0x00112233aabbccdd',
                u'manufacturer': u'Asus',
                u'model':        u'Nexus 7',
                u'name':         u'',
                u'type':         u'PHONE',
               }
            ]

        """

        #TODO sessionid stuff
        res = self._make_call(webclient.GetSettings, '')
        return res['settings']['devices']

    @utils.enforce_id_param
    def get_song_download_info(self, song_id):
        """Returns a tuple: ``('<url>', <download count>)``.

        :param song_id: a single song id.

        ``url`` will be ``None`` if the download limit is exceeded.

        GM allows 2 downloads per song. The download count may not always be accurate,
        and the 2 download limit seems to be loosely enforced.

        This call alone does not count towards a download -
        the count is incremented when ``url`` is retrieved.
        """

        #TODO the protocol expects a list of songs - could extend with accept_singleton
        info = self._make_call(webclient.GetDownloadInfo, [song_id])
        url = info.get('url')

        return (url, info["downloadCounts"][song_id])

    @utils.enforce_id_param
    def get_stream_urls(self, song_id):
        """Returns a list of urls that point to a streamable version of this song.

        If you just need the audio and are ok with gmusicapi doing the download,
        consider using :func:`get_stream_audio` instead.
        This abstracts away the differences between different kinds of tracks:

            * normal tracks return a single url
            * All Access tracks return multiple urls, which must be combined

        :param song_id: a single song id.

        While acquiring the urls requires authentication, retreiving the
        contents does not.

        However, there are limitations on how the stream urls can be used:

            * the urls expire after a minute
            * only one IP can be streaming music at once.
              Other attempts will get an http 403 with
              ``X-Rejected-Reason: ANOTHER_STREAM_BEING_PLAYED``.

        *This is only intended for streaming*. The streamed audio does not contain metadata.
        Use :func:`get_song_download_info` or :func:`Musicmanager.download_song
        <gmusicapi.clients.Musicmanager.download_song>`
        to download files with metadata.
        """

        res = self._make_call(webclient.GetStreamUrl, song_id)

        try:
            return [res['url']]
        except KeyError:
            return res['urls']

    @utils.enforce_id_param
    def get_stream_audio(self, song_id, use_range_header=None):
        """Returns a bytestring containing mp3 audio for this song.

        :param song_id: a single song id
        :param use_range_header: in some cases, an HTTP range header can be
          used to save some bandwidth.
          However, there's no guarantee that the server will respect it,
          meaning that the client may get back an unexpected response when
          using it.

          There are three possible values for this argument:
              * None: (default) send header; fix response locally on problems
              * True: send header; raise IOError on problems
              * False: do not send header
        """

        urls = self.get_stream_urls(song_id)

        #TODO shouldn't session.send be used throughout?

        if len(urls) == 1:
            return self.session._rsession.get(urls[0]).content

        # AA tracks are separated into multiple files.
        # the url contains the range of each file to be used.

        range_pairs = [[int(s) for s in val.split('-')]
                       for url in urls
                       for key, val in parse_qsl(urlparse(url)[4])
                       if key == 'range']

        stream_pieces = []
        prev_end = 0
        headers = None

        for url, (start, end) in zip(urls, range_pairs):
            if use_range_header or use_range_header is None:
                headers = {'Range': 'bytes=' + str(prev_end - start) + '-'}

            audio = self.session._rsession.get(url, headers=headers).content

            if end - prev_end != len(audio) - 1:
                #content length is not in the right range

                if use_range_header:
                    # the user didn't want automatic response fixup
                    raise IOError('use_range_header is True but the response'
                                  ' was not the correct content length.'
                                  ' This might be caused by a (poorly-written) http proxy.')

                # trim to the proper range
                audio = audio[prev_end - start:]

            stream_pieces.append(audio)

            prev_end = end + 1

        return ''.join(stream_pieces)

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    def report_incorrect_match(self, song_ids):
        """Equivalent to the 'Fix Incorrect Match' button, this requests re-uploading of songs.
        Returns the song_ids provided.

        :param song_ids: a list of song ids to report, or a single song id.

        Note that if you uploaded a song through gmusicapi, it won't be reuploaded
        automatically - this currently only works for songs uploaded with the Music Manager.
        See issue `#89 <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/89>`__.

        This should only be used on matched tracks (``song['type'] == 6``).
        """

        self._make_call(webclient.ReportBadSongMatch, song_ids)

        return song_ids

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    def upload_album_art(self, song_ids, image_filepath):
        """Uploads an image and sets it as the album art for songs.

        :param song_ids: a list of song ids, or a single song id.
        :param image_filepath: filepath of the art to use. jpg and png are known to work.

        This function will *always* upload the provided image, even if it's already uploaded.
        If the art is already uploaded and set for another song, copy over the
        value of the ``'albumArtUrl'`` key using :func:`change_song_metadata` instead.
        """

        res = self._make_call(webclient.UploadImage, image_filepath)
        url = res['imageUrl']

        song_dicts = [dict((('id', id), ('albumArtUrl', url))) for id in song_ids]

        return self.change_song_metadata(song_dicts)

    @utils.accept_singleton(dict)
    @utils.empty_arg_shortcircuit
    def change_song_metadata(self, songs):
        """Changes the metadata for some :ref:`song dictionaries <songdict-format>`.
        Returns a list of the song ids changed.

        :param songs: a list of :ref:`song dictionaries <songdict-format>`,
          or a single :ref:`song dictionary <songdict-format>`.

        Generally, stick to these metadata keys:

        * ``rating``: set to 0 (no thumb), 1 (down thumb), or 5 (up thumb)
        * ``name``: use this instead of ``title``
        * ``album``
        * ``albumArtist``
        * ``artist``
        * ``composer``
        * ``disc``
        * ``genre``
        * ``playCount``
        * ``totalDiscs``
        * ``totalTracks``
        * ``track``
        * ``year``
        """

        res = self._make_call(webclient.ChangeSongMetadata, songs)

        return [s['id'] for s in res['songs']]

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    def delete_songs(self, song_ids):
        """Deletes songs from the entire library. Returns a list of deleted song ids.

        :param song_ids: a list of song ids, or a single song id.
        """

        res = self._make_call(webclient.DeleteSongs, song_ids)

        return res['deleteIds']

    def get_all_songs(self, incremental=False):
        """Returns a list of :ref:`song dictionaries <songdict-format>`.

        :param incremental: if True, return a generator that yields lists
          of at most 2500 :ref:`song dictionaries <songdict-format>`
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.
        """

        to_return = self._get_all_songs()

        if not incremental:
            to_return = [song for chunk in to_return for song in chunk]

        return to_return

    def _get_all_songs(self):
        """Return a generator of song chunks."""

        get_next_chunk = True
        lib_chunk = {'continuationToken': None}

        while get_next_chunk:
            lib_chunk = self._make_call(webclient.GetLibrarySongs,
                                        lib_chunk['continuationToken'])

            yield lib_chunk['playlist']  # list of songs of the chunk

            get_next_chunk = 'continuationToken' in lib_chunk

    @utils.enforce_id_param
    def get_playlist_songs(self, playlist_id):
        """Returns a list of :ref:`song dictionaries <songdict-format>`,
        which include ``playlistEntryId`` keys for the given playlist.

        :param playlist_id: id of the playlist to load.

        This will return ``[]`` if the playlist id does not exist.
        """

        res = self._make_call(webclient.GetPlaylistSongs, playlist_id)
        return res['playlist']

    def get_all_playlist_ids(self, auto=True, user=True):
        """Returns a dictionary that maps playlist types to dictionaries.

        :param auto: create an ``'auto'`` subdictionary entry.
          Currently, this will just map to ``{}``; support for 'Shared with me' and
          'Google Play recommends' is on the way (
          `#102 <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/102>`__).

          Other auto playlists are not stored on the server, but calculated by the client.
          See `this gist <https://gist.github.com/simon-weber/5007769>`__ for sample code for
          'Thumbs Up', 'Last Added', and 'Free and Purchased'.

        :param user: create a user ``'user'`` subdictionary entry for user-created playlists.
          This includes anything that appears on the left side 'Playlists' bar (notably, saved
          instant mixes).

        User playlist names will be unicode strings.

        Google Music allows multiple user playlists with the same name, so the ``'user'`` dictionary
        will map onto lists of ids. Here's an example response::

            {
                'auto':{},

                'user':{
                    u'Some Song Mix':[
                        u'14814747-efbf-4500-93a1-53291e7a5919'
                    ],

                    u'Two playlists have this name':[
                        u'c89078a6-0c35-4f53-88fe-21afdc51a414',
                        u'86c69009-ea5b-4474-bd2e-c0fe34ff5484'
                    ]
                }
            }

        There is currently no support for retrieving automatically-created instant mixes
        (see issue `#67 <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/67>`__).

        """

        playlists = {}

        if auto:
            #playlists['auto'] = self._get_auto_playlists()
            playlists['auto'] = {}
        if user:
            res = self._make_call(webclient.GetPlaylistSongs, 'all')
            playlists['user'] = self._playlist_list_to_dict(res['playlists'])

        return playlists

    def _playlist_list_to_dict(self, pl_list):
        ret = {}

        for name, pid in ((p["title"], p["playlistId"]) for p in pl_list):
            if not name in ret:
                ret[name] = []
            ret[name].append(pid)

        return ret

    def _get_auto_playlists(self):
        """For auto playlists, returns a dictionary which maps autoplaylist name to id."""

        #Auto playlist ids are hardcoded in the wc javascript.
        #When testing, an incorrect name here will be caught.
        return {u'Thumbs up': u'auto-playlist-thumbs-up',
                u'Last added': u'auto-playlist-recent',
                u'Free and purchased': u'auto-playlist-promo'}

    @utils.accept_singleton(basestring, 2)
    @utils.enforce_ids_param(2)
    @utils.enforce_id_param
    @utils.empty_arg_shortcircuit(position=2)
    def add_songs_to_playlist(self, playlist_id, song_ids):
        """Appends songs to a playlist.
        Returns a list of (song id, playlistEntryId) tuples that were added.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """

        res = self._make_call(webclient.AddToPlaylist, playlist_id, song_ids)
        new_entries = res['songIds']

        return [(e['songId'], e['playlistEntryId']) for e in new_entries]

    @utils.accept_singleton(basestring, 2)
    @utils.enforce_ids_param(2)
    @utils.enforce_id_param
    @utils.empty_arg_shortcircuit(position=2)
    def remove_songs_from_playlist(self, playlist_id, sids_to_match):
        """Removes all copies of the given song ids from a playlist.
        Returns a list of removed (sid, eid) pairs.

        :param playlist_id: id of the playlist to remove songs from.
        :param sids_to_match: a list of song ids to match, or a single song id.

        This does *not always* the inverse of a call to :func:`add_songs_to_playlist`,
        since multiple copies of the same song are removed.
        """

        playlist_tracks = self.get_playlist_songs(playlist_id)
        sid_set = set(sids_to_match)

        matching_eids = [t["playlistEntryId"]
                         for t in playlist_tracks
                         if t["id"] in sid_set]

        if matching_eids:
            #Call returns "sid_eid" strings.
            sid_eids = self._remove_entries_from_playlist(playlist_id,
                                                          matching_eids)
            return [s.split("_") for s in sid_eids]
        else:
            return []

    @utils.accept_singleton(basestring, 2)
    @utils.empty_arg_shortcircuit(position=2)
    def _remove_entries_from_playlist(self, playlist_id, entry_ids_to_remove):
        """Removes entries from a playlist. Returns a list of removed "sid_eid" strings.

        :param playlist_id: the playlist to be modified.
        :param entry_ids: a list of entry ids, or a single entry id.
        """

        #GM requires the song ids in the call as well; find them.
        playlist_tracks = self.get_playlist_songs(playlist_id)
        remove_eid_set = set(entry_ids_to_remove)

        e_s_id_pairs = [(t["id"], t["playlistEntryId"])
                        for t in playlist_tracks
                        if t["playlistEntryId"] in remove_eid_set]

        num_not_found = len(entry_ids_to_remove) - len(e_s_id_pairs)
        if num_not_found > 0:
            self.logger.warning("when removing, %d entry ids could not be found in playlist id %s",
                                num_not_found, playlist_id)

        #Unzip the pairs.
        sids, eids = zip(*e_s_id_pairs)

        res = self._make_call(webclient.DeleteSongs, sids, playlist_id, eids)

        return res['deleteIds']
