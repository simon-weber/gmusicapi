#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""`gmusicapi` enables interaction with Google Music.
This includes both web-client and Music Manager features.

This api is not supported nor endorsed by Google, and could break at any time.

**Respect Google in your use of the API.**
Use common sense: protocol compliance, reasonable load, etc.
"""

import copy
from socket import gethostname
import time
from urllib2 import HTTPCookieProcessor, Request, build_opener
from uuid import getnode as getmac

import requests

from gmusicapi.gmtools import tools
from gmusicapi.exceptions import (
    CallFailure, ParseException, ValidationException,
    AlreadyLoggedIn, NotLoggedIn
)
from gmusicapi.protocol import webclient, musicmanager, upload_pb2
from gmusicapi.utils import utils
from gmusicapi.utils.apilogging import UsesLog
from gmusicapi.utils.clientlogin import ClientLogin
from gmusicapi.utils.tokenauth import TokenAuth


class Api(UsesLog):
    def __init__(self):
        """Initializes an Api."""

        self.session = PlaySession()

        self.uploader_id = None
        self.uploader_name = None

        self.init_logger()

    #---
    #   Authentication:
    #---

    def is_authenticated(self):
        """Returns ``True`` if the Api can make an authenticated request."""
        return self.session.logged_in

    def login(self, email, password, perform_upload_auth=True,
              uploader_id=None, uploader_name=None):
        """Authenticates the api.
        Returns ``True`` on success, ``False`` on failure.

        :param email: eg ``'test@gmail.com'`` or just ``'test'``.
        :param password: password or app-specific password for 2-factor users.
          This is not stored locally, and is sent over SSL.

        :param perform_upload_auth: if ``True``, register/authenticate as an upload device.
          This is only required when this Api will be used with :func:`upload`.

        :param uploader_id: a unique id as a MAC address, eg ``'01:23:45:67:89:AB'``.
          This should only be provided in cases where the default
          (host MAC address incremented by 1) will not work.

          Upload behavior is undefined if a Music Manager uses the same id, especially when
          reporting bad matches.

          ``OSError`` will be raised if this is not provided and a stable MAC could not be
          determined (eg when running on a VPS).

          If provided, it's best to use the same id on all future runs for this machine,
          because of the upload device limit explained below.

        :param uploader_name: human-readable non-unique id; default is ``"<hostname> (gmusicapi)"``.

        Users of two-factor authentication will need to set an application-specific password
        to log in.

        There are strict limits on how many upload devices can be registered; refer to `Google's
        docs <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1230356>`__. There
        have been limits on deauthorizing devices in the past, so it's smart not to register
        more devices than necessary.
        """

        self.session.login(email, password)
        if not self.is_authenticated():
            self.log.info("failed to authenticate")
            return False

        self.log.info("authenticated")

        if perform_upload_auth:
            if uploader_id is None:
                mac = getmac()
                if (mac >> 40) % 2:
                    raise OSError('uploader_id not provided, and a valid MAC could not be found.')
                else:
                    #distinguish us from a Music Manager on this machine
                    mac = (mac + 1) % (1 << 48)

                mac = hex(mac)[2:-1]
                mac = ':'.join([mac[x:x + 2] for x in range(0, 10, 2)])
                uploader_id = mac.upper()

            if uploader_name is None:
                uploader_name = gethostname() + u" (gmusicapi)"

            try:
                #self._mm_pb_call("upload_auth")
                self._make_call(musicmanager.AuthenticateUploader,
                                uploader_id,
                                uploader_name)
                self.log.info("successful upload auth")
                self.uploader_id = uploader_id
                self.uploader_name = uploader_name

            except CallFailure:
                self.log.exception("could not authenticate for uploading")
                self.session.logout()
                return False

        return True

    def logout(self):
        """Forgets local authentication in this Api instance. Always returns ``True``."""
        self.session.logout()
        self.uploader_id = None
        self.uploader_name = None

        self.log.info("logged out")

        return True

    #---
    #   Api features supported by the web client interface:
    #---
    def change_playlist_name(self, playlist_id, new_name):
        """Changes the name of a playlist. Returns the changed id.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """

        self._make_call(webclient.ChangePlaylistName, playlist_id, new_name)

        return playlist_id  # the call actually doesn't return anything.

    @utils.accept_singleton(dict)
    @utils.empty_arg_shortcircuit()
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

        For up-to-date information on metadata, refer to `the code
        <https://github.com/simon-weber/Unofficial-Google-Music-API/
        blob/develop/gmusicapi/protocol/metadata.py>`__.
        Better docs are in the works; see issue `#73
        <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/73>`__.
        """

        res = self._make_call(webclient.ChangeSongMetadata, songs)

        return [s['id'] for s in res['songs']]

    def create_playlist(self, name):
        """Creates a new playlist. Returns the new playlist id.

        :param title: the title of the playlist to create.
        """

        return self._make_call(webclient.AddPlaylist, name)['id']

    def delete_playlist(self, playlist_id):
        """Deletes a playlist. Returns the deleted id.

        :param playlist_id: id of the playlist to delete.
        """

        res = self._make_call(webclient.DeletePlaylist, playlist_id)

        return res['deleteId']

    @utils.accept_singleton(basestring)
    @utils.empty_arg_shortcircuit()
    def delete_songs(self, song_ids):
        """Deletes songs from the entire library. Returns a list of deleted song ids.

        :param song_ids: a list of song ids, or a single song id.
        """

        res = self._make_call(webclient.DeleteSongs, song_ids)

        return res['deleteIds']

    def get_all_songs(self):
        #TODO support an iterator; see #88
        """Returns a list of :ref:`song dictionaries <songdict-format>`."""

        library = []

        lib_chunk = self._make_call(webclient.GetLibrarySongs)

        while 'continuationToken' in lib_chunk:
            library += lib_chunk['playlist']  # 'playlist' is misleading; this is the entire chunk

            lib_chunk = self._make_call(webclient.GetLibrarySongs, lib_chunk['continuationToken'])

        library += lib_chunk['playlist']

        return library

    def get_playlist_songs(self, playlist_id):
        """Returns a list of :ref:`song dictionaries <songdict-format>`,
        which include ``playlistEntryId`` keys for the given playlist.

        :param playlist_id: id of the playlist to load.
        """

        res = self._make_call(webclient.GetPlaylistSongs, playlist_id)
        return res['playlist']

    def get_all_playlist_ids(self, auto=True, user=True):
        """Returns a dictionary that maps playlist types to dictionaries.

        :param auto: create an ``'auto'`` subdictionary entry for autoplaylists like
          'Free and purchased' and 'Last added'.

        :param user: create a user ``'user'`` subdictionary entry for user-created playlists.

        User playlist names will be unicode strings.

        Google Music allows multiple user playlists with the same name, so the ``'user'`` dictionary
        will map onto lists of ids. Here's an example response::

            {
                'auto':{
                    'Free and purchased': 'auto-playlist-promo',
                    'Thumbs up': 'auto-playlist-thumbs-up',
                    'Last added': 'auto-playlist-recent'
                },

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
            playlists['auto'] = self._get_auto_playlists()
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

    def get_stream_url(self, song_id):
        """Returns a url that points to a streamable version of this song.

        :param song_id: a single song id.

        While this call requires authentication, retrieving the returned url does not.
        However, the url expires after about a minute.

        *This is only intended for streaming*. The streamed audio does not contain metadata.
        Use :func:`get_song_download_info` to download complete files with metadata.
        """

        res = self._make_call(webclient.GetStreamUrl, song_id)

        return res['url']

    def copy_playlist(self, playlist_id, copy_name):
        """Copies the contents of a playlist to a new playlist. Returns the id of the new playlist.

        :param playlist_id: id of the playlist to be copied.
        :param copy_name: the name of the new copied playlist.

        This is useful for making backups of playlists before modifications.
        """

        orig_tracks = self.get_playlist_songs(playlist_id)

        new_id = self.create_playlist(copy_name)
        self.add_songs_to_playlist(new_id, [t["id"] for t in orig_tracks])

        return new_id

    def change_playlist(self, playlist_id, desired_playlist, safe=True):
        """Changes the order and contents of an existing playlist.
        Returns the id of the playlist when finished -
        this may be the same as the argument in the case of a failure and recovery.

        :param playlist_id: the id of the playlist being modified.
        :param desired_playlist: the desired contents and order as a list of
          :ref:`song dictionaries <songdict-format>`, like is returned
          from :func:`get_playlist_songs`.

        :param safe: if ``True``, ensure playlists will not be lost if a problem occurs.
          This may slow down updates.

        The server only provides 3 basic playlist mutations: addition, deletion, and reordering.
        This function will use these to automagically apply the desired changes.

        However, this might involve multiple calls to the server, and if a call fails,
        the playlist will be left in an inconsistent state.
        The ``safe`` option makes a backup of the playlist before doing anything, so it can be
        rolled back if a problem occurs. This is enabled by default.
        This might slow down updates of very large playlists.

        There will always be a warning logged if a problem occurs, even if ``safe`` is ``False``.
        """

        #We'll be modifying the entries in the playlist, and need to copy it.
        #Copying ensures two things:
        # 1. the user won't see our changes
        # 2. changing a key for one entry won't change it for another - which would be the case
        #     if the user appended the same song twice, for example.
        desired_playlist = [copy.deepcopy(t) for t in desired_playlist]
        server_tracks = self.get_playlist_songs(playlist_id)

        if safe:
            #Make a backup.
            #The backup is stored on the server as a new playlist with "_gmusicapi_backup"
            # appended to the backed up name.
            names_to_ids = self.get_all_playlist_ids()['user']
            playlist_name = (ni_pair[0]
                             for ni_pair in names_to_ids.iteritems()
                             if playlist_id in ni_pair[1]).next()

            backup_id = self.copy_playlist(playlist_id, playlist_name + u"_gmusicapi_backup")

        try:
            #Counter, Counter, and set of id pairs to delete, add, and keep.
            to_del, to_add, to_keep = \
                tools.find_playlist_changes(server_tracks, desired_playlist)

            ##Delete unwanted entries.
            to_del_eids = [pair[1] for pair in to_del.elements()]
            if to_del_eids:
                self._remove_entries_from_playlist(playlist_id, to_del_eids)

            ##Add new entries.
            to_add_sids = [pair[0] for pair in to_add.elements()]
            if to_add_sids:
                new_pairs = self.add_songs_to_playlist(playlist_id, to_add_sids)

                ##Update desired tracks with added tracks server-given eids.
                #Map new sid -> [eids]
                new_sid_to_eids = {}
                for sid, eid in new_pairs:
                    if not sid in new_sid_to_eids:
                        new_sid_to_eids[sid] = []
                    new_sid_to_eids[sid].append(eid)

                for d_t in desired_playlist:
                    if d_t["id"] in new_sid_to_eids:
                        #Found a matching sid.
                        match = d_t
                        sid = match["id"]
                        eid = match.get("playlistEntryId")
                        pair = (sid, eid)

                        if pair in to_keep:
                            to_keep.remove(pair)  # only keep one of the to_keep eids.
                        else:
                            match["playlistEntryId"] = new_sid_to_eids[sid].pop()
                            if len(new_sid_to_eids[sid]) == 0:
                                del new_sid_to_eids[sid]

            ##Now, the right eids are in the playlist.
            ##Set the order of the tracks:

            #The web client has no way to dictate the order without block insertion,
            # but the api actually supports setting the order to a given list.
            #For whatever reason, though, it needs to be set backwards; might be
            # able to get around this by messing with afterEntry and beforeEntry parameters.
            if desired_playlist:
                #can't *-unpack an empty list
                sids, eids = zip(*tools.get_id_pairs(desired_playlist[::-1]))

                if sids:
                    self._make_call(webclient.ChangePlaylistOrder, playlist_id, sids, eids)

            ##Clean up the backup.
            if safe:
                self.delete_playlist(backup_id)

        except CallFailure:
            self.log.info("a subcall of change_playlist failed - "
                          "playlist %s is in an inconsistent state", playlist_id)

            if not safe:
                raise  # there's nothing we can do
            else:  # try to revert to the backup
                self.log.info("attempting to revert changes from playlist "
                              "'%s_gmusicapi_backup'", playlist_name)

                try:
                    self.delete_playlist(playlist_id)
                    self.change_playlist_name(backup_id, playlist_name)
                except CallFailure:
                    self.log.warning("failed to revert failed change_playlist call on '%s'",
                                     playlist_name)
                    raise
                else:
                    self.log.info("reverted changes safely; playlist id of '%s' is now '%s'",
                                  playlist_name, backup_id)
                    playlist_id = backup_id

        return playlist_id

    @utils.accept_singleton(basestring, 2)
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
    @utils.empty_arg_shortcircuit(position=2)
    def remove_songs_from_playlist(self, playlist_id, sids_to_match):
        """Removes all copies of the given song ids from a playlist.
        Returns a list of removed (sid, eid) pairs.

        :param playlist_id: id of the playlist to remove songs from.
        :param sids_to_match: a list of song ids to match, or a single song id.

        This does *not always* the inverse of a call to :func:`add_songs_to_playlist`,
        since multiple copies of the same song are removed. For more control in this case,
        get the playlist tracks with :func:`get_playlist_songs`, modify the list of tracks,
        then use :func:`change_playlist` to push changes to the server.
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
            self.log.warning("when removing, %d entry ids could not be found in playlist id %s",
                             num_not_found, playlist_id)

        #Unzip the pairs.
        sids, eids = zip(*e_s_id_pairs)

        res = self._make_call(webclient.DeleteSongs, sids, playlist_id, eids)

        return res['deleteIds']

    def search(self, query):
        """Queries the server for songs and albums.
        Generally, this isn't needed; just get all tracks and locally search over them.

        :param query: a string keyword to search with. Capitalization and punctuation are ignored.

        Search results are organized based on how they were found.

        The responses are returned in a dictionary, arranged by hit type.
        ``artist_hits`` and ``song_hits`` return a list of
        :ref:`song dictionaries <songdict-format>`, while ``album_hits`` entries
        have a different structure.

        For example, a search on ``'cat'`` could return::

            {
                "album_hits": [
                    {
                        "albumArtist": "The Cat Empire",
                        "albumName": "Cities: The Cat Empire Project",
                        "artistName": "The Cat Empire",
                        "imageUrl": "//ssl.gstatic.com/music/fe/[...].png"
                        # no more entries
                    },
                ],
                "artist_hits": [
                    {
                        "album": "Cinema",
                        "artist": "The Cat Empire",
                        "id": "c9214fc1-91fa-3bd2-b25d-693727a5f978",
                        "title": "Waiting"
                        # ... normal song dictionary
                    },
                ],
                "song_hits": [
                    {
                        "album": "Mandala",
                        "artist": "RX Bandits",
                        "id": "a7781438-8ec3-37ab-9c67-0ddb4115f60a",
                        "title": "Breakfast Cat",
                        # ... normal song dictionary
                    },
                ]
            }

        """

        res = self._make_call(webclient.Search, query)['results']

        return {"album_hits": res["albums"],
                "artist_hits": res["artists"],
                "song_hits": res["songs"]}

    @utils.accept_singleton(basestring)
    @utils.empty_arg_shortcircuit()
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

    #TODO
    #@utils.accept_singleton(basestring)
    #@utils.empty_arg_shortcircuit()
    #def change_album_art(self, song_ids, image_filepath):
    #    """Change the album art of songs.

    #    :param song_ids: a list of song ids, or a single song id.
    #    :param image_filepath: filepath of the art to use. jpg and png are known to work.

    #    Note that this always uploads the given art. If you already have the art uploaded and set
    #    for another song, you can just copy over the the 'albumArtUrl' key, then set the change
    #    with :func:`change_song_metadata`.
    #    """

    #    with open(image_filepath) as f:
    #        image = f.read()

    #    res = self._make_call(webclient.UploadImage, image)
    #    url = res['imageUrl']

    #    song_dicts = [{'id': id, 'albumArtUrl': url} for id in song_ids]

    #    return self.change_song_metadata(song_dicts)

    #---
    #   Api features supported by the Music Manager interface:
    #---

    # def get_quota(self):
    #     """Returns a tuple of (allowed number of tracks, total tracks, available tracks)."""
    #     quota = self._mm_pb_call("client_state").quota
    #     #protocol incorrect here...
    #     return (quota.maximumTracks, quota.totalTracks, quota.availableTracks)

    @utils.accept_singleton(basestring)
    @utils.empty_arg_shortcircuit(return_code='{}')
    def upload(self, filepaths, transcode_quality=3, enable_matching=False):
        """Uploads the given filepaths.
        Any non-mp3 files will be `transcoded with avconv
        <https://github.com/simon-weber/Unofficial-Google-Music-API/
        blob/develop/gmusicapi/utils/utils.py#L18>`__ before being uploaded.

        Return a 3-tuple ``(uploaded, matched, not_uploaded)`` of dictionaries, eg::

            (
                {'<filepath>': '<new server id>'},               # uploaded
                {'<filepath>': '<new server id>'},               # matched
                {'<filepath>': '<reason, eg ALREADY_UPLOADED>'}  # not uploaded
            )

        :param filepaths: a list of filepaths, or a single filepath.
        :param transcode_quality: if int, pass to avconv ``-qscale`` for libmp3lame
          (lower-better int, roughly corresponding to `hydrogenaudio -vX settings
          <http://wiki.hydrogenaudio.org/index.php?title=LAME#Recommended_encoder_settings>`__).
          If string, pass to avconv ``-ab`` (eg ``'128k'`` for an average bitrate of 128k). The
          default is ~175kbs vbr.

        :param enable_matching: if ``True``, attempt to use `scan and match
          <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=2920799&topic=2450455>`__
          to avoid uploading every song.
          **WARNING**: currently, mismatched songs can *not* be fixed with the 'Fix Incorrect Match'
          button or :func:`report_incorrect_match`. They would have to be deleted and reuploaded
          with the Music Manager.
          Fixing matches from gmusicapi will be supported in a future release; see issue `#89
          <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/89>`__.

        All Google-supported filetypes are supported; see `Google's documentation
        <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1100462>`__.

        Unlike Google's Music Manager, this function will currently allow the same song to
        be uploaded more than once if its tags are changed. This is subject to change in the future.

        If ``PERMANENT_ERROR`` is given as a not_uploaded reason, attempts to reupload will never
        succeed. The file will need to be changed before the server will reconsider it; the easiest
        way is to change metadata tags (it's not important that the tag be uploaded, just that the
        contents of the file change somehow).
        """

        if self.uploader_id is None or self.uploader_name is None:
            raise NotLoggedIn("Not authenticated as an upload device;"
                              " run Api.login(...perform_upload_auth=True...)"
                              " first.")

        #TODO there is way too much code in this function.

        #To return.
        uploaded = {}
        matched = {}
        not_uploaded = {}

        #Gather local information on the files.
        local_info = {}  # {clientid: (path, contents, Track)}
        for path in filepaths:
            try:
                with open(path, 'rb') as f:
                    contents = f.read()
                track = musicmanager.UploadMetadata.fill_track_info(path, contents)
            except (IOError, ValueError) as e:
                self.log.exception("problem gathering local info of '%s'" % path)
                not_uploaded[path] = str(e)
            else:
                local_info[track.client_id] = (path, contents, track)

        if not local_info:
            return uploaded, matched, not_uploaded

        #TODO allow metadata faking

        #Upload metadata; the server tells us what to do next.
        res = self._make_call(musicmanager.UploadMetadata,
                              [track for (path, contents, track) in local_info.values()],
                              self.uploader_id)

        #TODO checking for proper contents should be handled in verification
        md_res = res.metadata_response

        responses = [r for r in md_res.track_sample_response]
        sample_requests = [req for req in md_res.signed_challenge_info]

        #Send scan and match samples if requested.
        for sample_request in sample_requests:
            path, contents, track = local_info[sample_request.challenge_info.client_track_id]

            try:
                res = self._make_call(musicmanager.ProvideSample,
                                      contents, sample_request, track, self.uploader_id)
            except ValueError as e:
                self.log.warning("couldn't create scan and match sample for '%s': %s", path, str(e))
                not_uploaded[path] = str(e)
            else:
                responses.extend(res.sample_response.track_sample_response)

        #Read sample responses and prep upload requests.
        to_upload = {}  # {serverid: (path, contents, Track, do_not_rematch?)}
        for sample_res in responses:
            path, contents, track = local_info[sample_res.client_track_id]

            if sample_res.response_code == upload_pb2.TrackSampleResponse.MATCHED:
                self.log.info("matched '%s' to sid %s", path, sample_res.server_track_id)

                if enable_matching:
                    matched[path] = sample_res.server_track_id
                else:
                    #Immediately request a reupload session (ie, hit 'fix incorrect match').
                    try:
                        self._make_call(webclient.ReportBadSongMatch, [sample_res.server_track_id])

                        #Wait for server to register our request.
                        retries = 0
                        while retries < 5:
                            jobs = self._make_call(musicmanager.GetUploadJobs, self.uploader_id)
                            matching = [job for job in jobs.getjobs_response.tracks_to_upload
                                        if (job.client_id == sample_res.client_track_id and
                                            job.status == upload_pb2.TracksToUpload.FORCE_REUPLOAD)]
                            if matching:
                                reup_sid = matching[0].server_id
                                break

                            self.log.debug("wait for reup job (%s)", retries)
                            time.sleep(2)
                            retries += 1
                        else:
                            raise CallFailure(
                                "could not get reupload/rematch job for '%s'" % path,
                                'GetUploadJobs'
                            )

                    except CallFailure as e:
                        self.log.exception("'%s' was matched without matching enabled", path)
                        matched[path] = sample_res.server_track_id
                    else:
                        self.log.info("will reupload '%s'", path)

                        to_upload[reup_sid] = (path, contents, track, True)

            elif sample_res.response_code == upload_pb2.TrackSampleResponse.UPLOAD_REQUESTED:
                to_upload[sample_res.server_track_id] = (path, contents, track, False)
            else:
                #Report the symbolic name of the response code enum.
                enum_desc = upload_pb2._TRACKSAMPLERESPONSE.enum_types[0]
                res_name = enum_desc.values_by_number[sample_res.response_code].name

                err_msg = "TrackSampleResponse code %s: %s" % (sample_res.response_code, res_name)

                self.log.warning("upload of '%s' rejected: %s", path, err_msg)
                not_uploaded[path] = err_msg

        #Send upload requests.
        if to_upload:
            #TODO reordering requests could avoid wasting time waiting for reup sync
            self._make_call(musicmanager.UpdateUploadState, 'start', self.uploader_id)

            for server_id, (path, contents, track, do_not_rematch) in to_upload.items():
                #It can take a few tries to get an session.
                should_retry = True
                attempts = 0

                while should_retry and attempts < 10:
                    session = self._make_call(musicmanager.GetUploadSession,
                                              self.uploader_id, len(uploaded),
                                              track, path, server_id, do_not_rematch)
                    attempts += 1

                    got_session, error_details = \
                        musicmanager.GetUploadSession.process_session(session)

                    if got_session:
                        self.log.info("got an upload session for '%s'", path)
                        break

                    should_retry, reason, error_code = error_details
                    self.log.debug("problem getting upload session: %s\ncode=%s retrying=%s",
                                   reason, error_code, should_retry)

                    if error_code == 200 and do_not_rematch:
                        #reupload requests need to wait on a server sync
                        #200 == already uploaded, so force a retry in this case
                        should_retry = True

                    time.sleep(6)  # wait before retrying
                else:
                    err_msg = "GetUploadSession error %s: %s" % (error_code, reason)

                    self.log.warning("giving up on upload session for '%s': %s", path, err_msg)
                    not_uploaded[path] = err_msg

                    continue  # to next upload

                #got a session, do the upload
                #this terribly inconsistent naming isn't my fault: Google--
                session = session['sessionStatus']
                external = session['externalFieldTransfers'][0]

                session_url = external['putInfo']['url']
                content_type = external['content_type']

                try:
                    transcoded_audio = utils.transcode_to_mp3(contents, quality=transcode_quality)
                except (OSError, ValueError) as e:
                    self.log.warning("error transcoding %s: %s", path, e)
                    not_uploaded[path] = "transcoding error: %s" % e
                    continue

                upload_response = self._make_call(musicmanager.UploadFile,
                                                  session_url, content_type, transcoded_audio)

                success = upload_response.get('sessionStatus', {}).get('state')
                if success:
                    uploaded[path] = server_id
                else:
                    #404 == already uploaded? serverside check on clientid?
                    self.log.debug("could not finalize upload of '%s'. response: %s",
                                   path, upload_response)
                    not_uploaded[path] = 'could not finalize upload'

            self._make_call(musicmanager.UpdateUploadState, 'stopped', self.uploader_id)

        return uploaded, matched, not_uploaded

    def _make_call(self, protocol, *args, **kwargs):
        """Returns the response of a protocol.Call.
        Additional kw/args are passed to protocol.build_transaction."""
        #TODO link up these docs

        call_name = protocol.__name__

        self.log.debug("%s(args=%s, kwargs=%s)",
                       call_name,
                       [utils.truncate(a) for a in args],
                       {k: utils.truncate(v) for (k, v) in kwargs.items()})

        request = protocol.build_request(*args, **kwargs)

        response = self.session.send(request, protocol.get_auth(), protocol.session_options)

        #TODO check return code

        try:
            msg = protocol.parse_response(response)
        except ParseException:
            self.log.exception("couldn't parse %s response: %r", call_name, response.content)
            raise CallFailure("the server's response could not be understood."
                              " The call may still have succeeded, but it's unlikely.",
                              call_name)

        self.log.debug(protocol.filter_response(msg))

        try:
            #order is important; validate only has a schema for a successful response
            protocol.check_success(msg)
            protocol.validate(msg)
        except CallFailure:
            raise
        except ValidationException:
            #TODO link to some protocol for reporting this
            self.log.exception(
                "please report the following unknown response format for %s: %r",
                call_name, msg
            )

        return msg


#---
#The session layer:
#---

class PlaySession(object):
    """
    A Google Play Music session.

    It allows for authentication and the making of authenticated
    requests through the MusicManager API (protocol buffers), Web client requests,
    and the Skyjam client API.
    """

    # The URL for authenticating against Google Play Music
    PLAY_URL = 'https://play.google.com/music/listen?u=0&hl=en'

    # Common User Agent used for web requests
    _user_agent = (
        "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.6) "
        "Gecko/20061201 Firefox/2.0.0.6 (Ubuntu-feisty)"
    )

    def __init__(self):
        """
        Initializes a default unauthenticated session.
        """
        self.client = None
        self.web_cookies = None
        self.logged_in = False

    def _get_cookies(self):
        """
        Gets cookies needed for web and media streaming access.
        Returns ``True`` if the necessary cookies are found, ``False`` otherwise.
        """
        if self.logged_in:
            raise AlreadyLoggedIn

        handler = build_opener(HTTPCookieProcessor(self.web_cookies))
        req = Request(self.PLAY_URL, None, {})  # header
        handler.open(req)  # TODO is this necessary?

        return (
            self.get_web_cookie('sjsaid') is not None and
            self.get_web_cookie('xt') is not None
        )

    def get_web_cookie(self, name):
        """
        Finds the value of a cookie by name, returning None on failure.

        :param name: The name of the cookie to find.
        """
        if self.web_cookies is None:
            return None

        for cookie in self.web_cookies:
            if cookie.name == name:
                return cookie.value

        return None

    def login(self, email, password):
        """
        Attempts to create an authenticated session using the email and
        password provided.
        Return ``True`` if the login was successful, ``False`` otherwise.
        Raises AlreadyLoggedIn if the session is already authenticated.

        :param email: The email address of the account to log in.
        :param password: The password of the account to log in.
        """
        if self.logged_in:
            raise AlreadyLoggedIn

        self.client = ClientLogin(email, password, 'sj')
        tokenauth = TokenAuth('sj', self.PLAY_URL, 'jumper')

        if self.client.get_auth_token() is None:
            return False

        tokenauth.authenticate(self.client)
        self.web_cookies = tokenauth.get_cookies()

        self.logged_in = self._get_cookies()

        return self.logged_in

    def logout(self):
        """
        Resets the session to an unauthenticated default state.
        """
        self.__init__()

    def send(self, request, auth, session_options):
        """Send a request from a Call.

        :param request: filled requests.Request.
        :param auth: result of Call.get_auth().
        :param session_options: dict of kwargs to pass to requests.Session.send.
        """

        if any(auth) and not self.logged_in:
            raise NotLoggedIn

        send_xt, send_clientlogin, send_sso = auth

        if request.cookies is None:
            request.cookies = {}

        #Attach auth.
        if send_xt:
            request.params['u'] = 0
            request.params['xt'] = self.get_web_cookie('xt')

        if send_clientlogin:
            request.cookies['SID'] = self.client.get_sid_token()

        if send_sso:
            #dict <- CookieJar
            web_cookies = {c.name: c.value for c in self.web_cookies}
            request.cookies.update(web_cookies)

        prepped = request.prepare()
        s = requests.Session()

        res = s.send(prepped, **session_options)
        return res
