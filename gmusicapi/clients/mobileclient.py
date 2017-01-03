# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals
from past.builtins import basestring
from builtins import *  # noqa
from collections import defaultdict
import datetime
from operator import itemgetter
import re
from uuid import getnode as getmac

from gmusicapi import session
from gmusicapi.clients.shared import _Base
from gmusicapi.exceptions import CallFailure, NotSubscribed
from gmusicapi.protocol import mobileclient
from gmusicapi.utils import utils


class Mobileclient(_Base):
    """Allows library management and streaming by posing as the
    googleapis.com mobile clients.

    Uploading is not supported by this client (use the :class:`Musicmanager`
    to upload).
    """

    _session_class = session.Mobileclient
    FROM_MAC_ADDRESS = object()

    def __init__(self, debug_logging=True, validate=True, verify_ssl=True):
        super(Mobileclient, self).__init__(self.__class__.__name__,
                                           debug_logging,
                                           validate,
                                           verify_ssl)

    def _ensure_device_id(self, device_id=None):
        if device_id is None:
            device_id = self.android_id

        if len(device_id) == 16 and re.match('^[a-z0-9]*$', device_id):
            # android device ids are now sent in base 10
            device_id = str(int(device_id, 16))

        return device_id

    @property
    def locale(self):
        """The locale of the Mobileclient session used to localize some responses.

        Should be an `ICU <http://www.localeplanet.com/icu/>`__ locale supported by Android.

        Set on authentication with :func:`login` but can be changed at any time.
        """

        return self.session._locale

    @locale.setter
    def locale(self, locale):
        self.session._locale = locale

    @utils.cached_property(ttl=600)
    def is_subscribed(self):
        """Returns the subscription status of the Google Music account.

        Result is cached with a TTL of 10 minutes. To get live status before the TTL
        is up, delete the ``is_subscribed`` property of the Mobileclient instance.

            >>> mc = Mobileclient()
            >>> mc.is_subscribed  # Live status.
            >>> mc.is_subscribed  # Cached status.
            >>> del mc.is_subscribed  # Delete is_subscribed property.
            >>> mc.is_subscribed  # Live status.
        """

        res = self._make_call(mobileclient.Config)

        for item in res['data']['entries']:
            if item['key'] == 'isNautilusUser' and item['value'] == 'true':
                self.session._is_subscribed = True
                break
        else:
            self.session._is_subscribed = False

        return self.session._is_subscribed

    def login(self, email, password, android_id, locale='en_US'):
        """Authenticates the Mobileclient.
        Returns ``True`` on success, ``False`` on failure.

        :param email: eg ``'test@gmail.com'`` or just ``'test'``.
        :param password: password or app-specific password for 2-factor users.
          This is not stored locally, and is sent securely over SSL.
        :param android_id: 16 hex digits, eg ``'1234567890abcdef'``.

          Pass Mobileclient.FROM_MAC_ADDRESS instead to attempt to use
          this machine's MAC address as an android id.
          **Use this at your own risk**:
          the id will be a non-standard 12 characters,
          but appears to work fine in testing.
          If a valid MAC address cannot be determined on this machine
          (which is often the case when running on a VPS), raise OSError.

        :param locale: `ICU <http://www.localeplanet.com/icu/>`__ locale
          used to localize certain responses. This must be a locale supported
          by Android. Defaults to ``'en_US'``.
        """
        # TODO 2fa

        if android_id is None:
            raise ValueError("android_id cannot be None.")

        if android_id is self.FROM_MAC_ADDRESS:
            mac_int = getmac()
            if (mac_int >> 40) % 2:
                raise OSError("a valid MAC could not be determined."
                              " Provide an android_id (and be"
                              " sure to provide the same one on future runs).")

            android_id = utils.create_mac_string(mac_int)
            android_id = android_id.replace(':', '')

        if not self.session.login(email, password, android_id):
            self.logger.info("failed to authenticate")
            return False

        self.android_id = android_id
        self.logger.info("authenticated")

        self.locale = locale

        if self.is_subscribed:
            self.logger.info("subscribed")

        return True

    # TODO expose max/page-results, updated_after, etc for list operations

    def get_all_songs(self, incremental=False, include_deleted=None):
        """Returns a list of dictionaries that each represent a song.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 tracks
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.

        :param include_deleted: ignored. Will be removed in a future release.

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

        tracks = self._get_all_items(mobileclient.ListTracks, incremental)

        return tracks

    @utils.accept_singleton(dict)
    @utils.empty_arg_shortcircuit
    def rate_songs(self, songs, rating):
        """Rate library or store songs.

        Returns rated song ids.

        :param songs: a list of song dictionaries
          or a single song dictionary.
          required keys: 'id' for library songs or 'nid' and 'trackType' for store songs.
        :param rating: set to ``'0'`` (no thumb), ``'1'`` (down thumb), or ``'5'`` (up thumb).
        """

        mutate_call = mobileclient.BatchMutateTracks
        mutations = []
        for song in songs:
            song['rating'] = rating
            mutations.append({'update': song})
        self._make_call(mutate_call, mutations)

        # TODO
        # store tracks don't send back their id, so we're
        # forced to spoof this
        return [utils.id_or_nid(song) for song in songs]

    @utils.accept_singleton(dict)
    @utils.empty_arg_shortcircuit
    @utils.deprecated('prefer Mobileclient.rate_songs')
    def change_song_metadata(self, songs):
        """Changes the metadata of tracks.
        Returns a list of the song ids changed.

        :param songs: a list of song dictionaries
          or a single song dictionary.

        Currently, only the ``rating`` key can be changed.
        Set it to ``'0'`` (no thumb), ``'1'`` (down thumb), or ``'5'`` (up thumb).

        You can also use this to rate store tracks
        that aren't in your library, eg::

            song = mc.get_track_info('<some store track id>')
            song['rating'] = '5'
            mc.change_song_metadata(song)

        """

        mutate_call = mobileclient.BatchMutateTracks
        mutations = [{'update': s} for s in songs]
        self._make_call(mutate_call, mutations)

        # TODO
        # store tracks don't send back their id, so we're
        # forced to spoof this
        return [utils.id_or_nid(d) for d in songs]

    def increment_song_playcount(self, song_id, plays=1, playtime=None):
        """Increments a song's playcount and returns its song id.

        :params song_id: a song id. Providing the id of a store track
          that has been added to the library will *not* increment the
          corresponding library song's playcount. To do this, use the
          'id' field (which looks like a uuid and doesn't begin with 'T'),
          not the 'nid' field.
        :params plays: (optional) positive number of plays to increment by.
          The default is 1.
        :params playtime: (optional) a datetime.datetime of the
          time the song was played.
          It will default to the time of the call.
         """

        if playtime is None:
            playtime = datetime.datetime.now()

        self._make_call(mobileclient.IncrementPlayCount, song_id, plays, playtime)

        return song_id

    @utils.require_subscription
    @utils.enforce_id_param
    @utils.deprecated('prefer Mobileclient.add_store_tracks')
    def add_store_track(self, store_song_id):
        """Adds a store track to the library

        Returns the library track id of added store track.

        :param store_song_id: store song id
        """

        return self.add_store_tracks(store_song_id)[0]

    @utils.require_subscription
    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    def add_store_tracks(self, store_song_ids):
        """Add store tracks to the library

        Returns a list of the library track ids of added store tracks.

        :param store_song_ids: a list of store song ids or a single store song id
        """

        mutate_call = mobileclient.BatchMutateTracks
        add_mutations = [mutate_call.build_track_add(self.get_track_info(store_song_id))
                         for store_song_id in store_song_ids]

        res = self._make_call(mutate_call, add_mutations)

        return [r['id'] for r in res['mutate_response']]

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
    def get_stream_url(self, song_id, device_id=None, quality='hi'):
        """Returns a url that will point to an mp3 file.

        :param song_id: a single song id
        :param device_id: (optional) defaults to ``android_id`` from login.

          Otherwise, provide a mobile device id as a string.
          Android device ids are 16 characters, while iOS ids
          are uuids with 'ios:' prepended.

          If you have already used Google Music on a mobile device,
          :func:`Mobileclient.get_registered_devices
          <gmusicapi.clients.Mobileclient.get_registered_devices>` will provide
          at least one working id. Omit ``'0x'`` from the start of the string if present.

          Registered computer ids (a MAC address) will not be accepted and will 403.

          Providing an unregistered mobile device id will register it to your account,
          subject to Google's `device limits
          <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1230356>`__.
          **Registering a device id that you do not own is likely a violation of the TOS.**
        :param quality: (optional) stream bits per second quality
          One of three possible values, hi: 320kbps, med: 160kbps, low: 128kbps.
          The default is hi

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

        if song_id.startswith('T') and not self.is_subscribed:
            raise NotSubscribed("Store tracks require a subscription to stream.")

        device_id = self._ensure_device_id(device_id)

        return self._make_call(mobileclient.GetStreamUrl, song_id, device_id, quality)

    def get_all_playlists(self, incremental=False, include_deleted=None):
        """Returns a list of dictionaries that each represent a playlist.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 playlists
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.
        :param include_deleted: ignored. Will be removed in a future release.

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

        playlists = self._get_all_items(mobileclient.ListPlaylists, incremental)

        return playlists

    # these could trivially support multiple creation/edits/deletion, but
    # I chose to match the old webclient interface (at least for now).
    def create_playlist(self, name, description=None, public=False):
        """Creates a new empty playlist and returns its id.

        :param name: the desired title.
          Creating multiple playlists with the same name is allowed.
        :param description: (optional) the desired description
        :param public: (optional) if True and the user has a subscription, share playlist.
        """

        share_state = 'PUBLIC' if public else 'PRIVATE'

        mutate_call = mobileclient.BatchMutatePlaylists
        add_mutations = mutate_call.build_playlist_adds([{'name': name,
                                                          'description': description,
                                                          'public': share_state}])
        res = self._make_call(mutate_call, add_mutations)

        return res['mutate_response'][0]['id']

    @utils.enforce_id_param
    def edit_playlist(self, playlist_id, new_name=None, new_description=None, public=None):
        """Changes the name of a playlist and returns its id.

        :param playlist_id: the id of the playlist
        :param new_name: (optional) desired title
        :param new_description: (optional) desired description
        :param public: (optional) if True and the user has a subscription, share playlist.
        """

        if all(value is None for value in (new_name, new_description, public)):
            raise ValueError('new_name, new_description, or public must be provided')

        if public is None:
            share_state = public
        else:
            share_state = 'PUBLIC' if public else 'PRIVATE'

        mutate_call = mobileclient.BatchMutatePlaylists
        update_mutations = mutate_call.build_playlist_updates([
            {'id': playlist_id, 'name': new_name,
             'description': new_description, 'public': share_state}
        ])
        res = self._make_call(mutate_call, update_mutations)

        return res['mutate_response'][0]['id']

    @utils.enforce_id_param
    def delete_playlist(self, playlist_id):
        """Deletes a playlist and returns its id.

        :param playlist_id: the id to delete.
        """
        # TODO accept multiple?

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

        Here is an example playlist entry for an individual track::

          {
              'kind': 'sj#playlistEntry',
              'deleted': False,
              'trackId': '2bb0ab1c-ce1a-3c0f-9217-a06da207b7a7',
              'lastModifiedTimestamp': '1325285553655027',
              'playlistId': '3d72c9b5-baad-4ff7-815d-cdef717e5d61',
              'absolutePosition': '01729382256910287871',  # denotes playlist ordering
              'source': '1',  # '2' if hosted on Google Music, '1' otherwise (see below)
              'creationTimestamp': '1325285553655027',
              'id': 'c9f1aff5-f93d-4b98-b13a-429cc7972fea' ## see below
          }

        If a user uploads local music to Google Music using the Music Manager,
        Google will attempt to match each uploaded track to a track already
        hosted on its servers. If a match is found for a track, the playlist
        entry key ``'source'`` has the value ``'2'``, and the entry will have a
        key ``'track'`` with a value that is a dict of track metadata (title,
        artist, etc).

        If a track is not hosted on Google Music, then the playlist entry key
        ``'source'`` has the value ``'1'``, and may not have a ``'track'``
        key (e.g., for an MP3 without ID3 tags). In this case, the key ``'trackId'``
        corresponds to the column ``ServerId`` in the table ``XFILES`` in Music
        Manager's local SQLite database (stored, e.g., at
        ~/Library/Application\ Support/Google/MusicManager/ServerDatabase.db
        on OS X). Among other things, the SQLite database exposes the track's
        local file path, and Music Manager's imputed metadata.

        (Note that the above behavior is documented for the Music Manager set to
        sync from local Folders, and may differ if it instead syncs from iTunes.)
        """

        user_playlists = [p for p in self.get_all_playlists()
                          if (p.get('type') == 'USER_GENERATED' or
                              p.get('type') != 'SHARED' or
                              'type' not in p)]

        all_entries = self._get_all_items(mobileclient.ListPlaylistEntries,
                                          incremental=False,
                                          updated_after=None)

        for playlist in user_playlists:
            # TODO could use a dict to make this faster
            entries = [e for e in all_entries
                       if e['playlistId'] == playlist['id']]
            entries.sort(key=itemgetter('absolutePosition'))

            playlist['tracks'] = entries

        return user_playlists

    def get_shared_playlist_contents(self, share_token):
        """
        Retrieves the contents of a public playlist.

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

        Playlists have a maximum size of 1000 songs.
        Calls may fail before that point (presumably) due to
        an error on Google's end (see `#239
        <https://github.com/simon-weber/gmusicapi/issues/239>`__).
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
    # def reorder_playlist(self, reordered_playlist, orig_playlist=None):
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

    # @staticmethod
    # def _create_ple_reorder_mutations(tracks, from_to_idx_pairs):
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

    def get_registered_devices(self):
        """
        Returns a list of dictionaries representing devices associated with the account.

        Performing the :class:`Musicmanager` OAuth flow will register a device
        of type ``'DESKTOP_APP'``.

        Installing the Android or iOS Google Music app and logging into it will
        register a device of type ``'ANDROID'`` or ``'IOS'`` respectively, which is
        required for streaming with the :class:`Mobileclient`.

        Here is an example response::

            [
              {
                u'kind':               u'sj#devicemanagementinfo',
                u'friendlyName':       u'my-hostname',
                u'id':                 u'AA:BB:CC:11:22:33',
                u'lastAccessedTimeMs': u'1394138679694',
                u'type':               u'DESKTOP_APP'
              },
              {
                u"kind":               u"sj#devicemanagementinfo",
                u'friendlyName':       u'Nexus 7',
                u'id':                 u'0x00112233aabbccdd',  # remove 0x when streaming
                u'lastAccessedTimeMs': u'1344808742774',
                u'type':               u'ANDROID'
                u'smartPhone':         True
              },
              {
                u"kind":               u"sj#devicemanagementinfo",
                u'friendlyName':       u'iPhone 6',
                u'id':                 u'ios:01234567-0123-0123-0123-0123456789AB',
                u'lastAccessedTimeMs': 1394138679694,
                u'type':               u'IOS'
                u'smartPhone':         True
              }
              {
                u'kind':               u'sj#devicemanagementinfo',
                u'friendlyName':       u'Google Play Music for Chrome on Windows',
                u'id':                 u'rt2qfkh0qjhos4bxrgc0oae...',  # 64 characters, alphanumeric
                u'lastAccessedTimeMs': u'1425602805052',
                u'type':               u'DESKTOP_APP'
              },
            ]

        """

        res = self._make_call(mobileclient.GetDeviceManagementInfo)

        return res['data']['items'] if 'data' in res else []

    def deauthorize_device(self, device_id):
        """Deauthorize a registered device.

        Returns ``True`` on success, ``False`` on failure.

        :param device_id: A mobile device id as a string.
          Android ids are 16 characters with '0x' prepended,
          iOS ids are uuids with 'ios:' prepended,
          while desktop ids are in the form of a MAC address.

          Providing an invalid or unregistered device id will result in a 400 HTTP error.

        Google limits the number of device deauthorizations to 4 per year.
        Attempts to deauthorize a device when that limit is reached results in
        a 403 HTTP error with: ``X-Rejected-Reason: TOO_MANY_DEAUTHORIZATIONS``.
        """

        try:
            self._make_call(mobileclient.DeauthDevice, device_id)
        except CallFailure:
            self.logger.exception("Deauthorization failure.")
            return False

        return True

    def get_promoted_songs(self):
        """Returns a list of dictionaries that each represent a track.

        Only store tracks will be returned.

        Promoted tracks are determined in an unknown fashion,
        but positively-rated library tracks are common.

        See :func:`get_track_info` for the format of a track dictionary.
        """

        return self._get_all_items(mobileclient.ListPromotedTracks,
                                   incremental=False,
                                   updated_after=None)

    def get_listen_now_items(self):
        """Returns a list of dictionaries of Listen Now albums and stations.

        See :func:`get_listen_now_situations` for Listen Now situations.

        Here is an example Listen Now album::

            {
              'album': {
                'artist_metajam_id': 'A2mfgoustq7iqjdbvlenw7pnap4',
                'artist_name': 'Justin Bieber',
                'artist_profile_image': {
                  'url': 'http://lh3.googleusercontent.com/XgktDR74DWE9xD...'',
                },
                'description': 'Purpose is the fourth studio album by Canadian...',
                'description_attribution': {
                  'kind': 'sj#attribution',
                  'license_title': 'Creative Commons Attribution CC-BY-SA 4.0',
                  'license_url': 'http://creativecommons.org/licenses/by-sa/4.0/legalcode',
                  'source_title': 'Wikipedia',
                  'source_url': 'http://en.wikipedia.org/wiki/Purpose_(Justin_Bieber_album)',
                },
                'id': {
                  'artist': 'Justin Bieber',
                  'metajamCompactKey': 'Bqpez5cimsze2fh6w7j2rcf55xa',
                  'title': 'Purpose (Deluxe)',
                },
                'title': 'Purpose (Deluxe)'
                'images': [
                  {
                    'kind': 'sj#imageRef',
                    'url': 'http://lh3.googleusercontent.com/m66cbl4Jl3VNz...',
                  },
                ],
              }
              'kind': 'sj#listennowitem',
              'suggestion_reason': '9',
              'suggestion_text': 'Popular album on Google Play Music',
              'type': '1'
            }

        Here is an example Listen Now station::

            {
              'radio_station': {
                'id': {
                  'seeds': [
                    {
                      'artistId': 'Ax6ociylvowozcz2iepfqsar54i',
                      'kind': 'sj#radioSeed',
                      'metadataSeed': {
                        'artist': {
                          'artistArtRef': 'http://lh3.googleusercontent.com/x9qukAx...',
                          'artistArtRefs': [
                            {
                              'aspectRatio': '2',
                              'autogen': False,
                              'kind': 'sj#imageRef',
                              'url': 'http://lh3.googleusercontent.com/x9qukAx...',
                            },
                          ],
                          'artistId': 'Ax6ociylvowozcz2iepfqsar54i',
                          'artist_bio_attribution': {
                          'kind': 'sj#attribution',
                          'source_title': 'artist representative',
                          },
                          'kind': 'sj#artist',
                          'name': 'Drake',
                        },
                        'kind': 'sj#radioSeedMetadata',
                      },
                     'seedType': '3',
                    },
                  ]
                },
                'title': 'Drake',
              },
              'compositeArtRefs': [
                {
                  'aspectRatio': '2',
                  'kind': 'sj#imageRef',
                  'url': 'http://lh3.googleusercontent.com/rE39ky1yZN...',
                },
                {
                  'aspectRatio': '1',
                  'kind': 'sj#imageRef',
                  'url': 'http://lh3.googleusercontent.com/Pcwg_HngBr...',
                },
              ],
              'images': [
                {
                  'aspectRatio': '2',
                  'autogen': False,
                  'kind': 'sj#imageRef',
                  'url': 'http://lh3.googleusercontent.com/x9qukAx_TMam...',
                },
              ],
              'suggestion_reason': '9',
              'suggestion_text': 'Popular artist on Google Play Music',
              'type': '3'
            }
        """

        res = self._make_call(mobileclient.ListListenNowItems)

        return res['listennow_items']

    def get_listen_now_situations(self):
        """Returns a list of dictionaries that each represent a Listen Now situation.

        See :func:`get_listen_now_items` for Listen Now albums and stations.

        A situation contains a list of related stations or other situations.

        Here is an example situation::

            {
                'description': 'Select a station of today's most popular songs.',
                'id': 'Ntiiwllegkw73p27o236mfsj674',
                'imageUrl': 'http://lh3.googleusercontent.com/egm4NgIK-Cmh84GjVgH...',
                'stations': [
                    {
                        'compositeArtRefs': [
                            {
                                'aspectRatio': '2',
                                'kind': 'sj#imageRef',
                                'url': 'http://lh3.googleusercontent.com/ffDI377y...',
                            },
                        ],
                        'contentTypes': ['1'],
                        'description': "This playlist features today's biggest pop songs...",
                        'imageUrls': [
                            {
                                'aspectRatio': '1',
                                'autogen': False,
                                'kind': 'sj#imageRef',
                                'url': 'http://lh3.googleusercontent.com/B4iKX23Z...',
                            },
                        ],
                        'kind': 'sj#radioStation',
                        'name': "Today's Pop Hits",
                        'seed': {
                            'curatedStationId': 'Lgen6kdn43tz5b3edimqd5e4ckq',
                            'kind': 'sj#radioSeed',
                            'seedType': '9',
                        },
                        'skipEventHistory': [],
                        'stationSeeds': [
                            {
                                'curatedStationId': 'Lgen6kdn43tz5b3edimqd5e4ckq',
                                'kind': 'sj#radioSeed',
                                'seedType': '9',
                            },
                        ],
                    }
                ],
                'title': "Today's Biggest Hits",
                'wideImageUrl': 'http://lh3.googleusercontent.com/13W-bm3sNmSfOjUkEqY...'
            }
        """

        return self._make_call(mobileclient.ListListenNowSituations)['situations']

    def get_browse_podcast_hierarchy(self):
        """Retrieve the hierarchy of podcast browse genres.

        Returns a list of podcast genres and subgenres::

            {
                "groups": [
                    {
                        "id": "JZCpodcasttopchart",
                        "displayName": "Top Charts",
                        "subgroups": [
                            {
                             "id": "JZCpodcasttopchartall",
                             "displayName": "All categories"
                            },
                            {
                             "id": "JZCpodcasttopchartarts",
                             "displayName": "Arts"
                            },
                            {
                             "id": "JZCpodcasttopchartbusiness",
                             "displayName": "Business"
                            },
                            {
                             "id": "JZCpodcasttopchartcomedy",
                             "displayName": "Comedy"
                            },
                            {
                             "id": "JZCpodcasttopcharteducation",
                             "displayName": "Education"
                            },
                            {
                             "id": "JZCpodcasttopchartgames",
                             "displayName": "Games & hobbies"
                            },
                            {
                             "id": "JZCpodcasttopchartgovernment",
                             "displayName": "Government & organizations"
                            },
                            {
                             "id": "JZCpodcasttopcharthealth",
                             "displayName": "Health"
                            },
                            {
                             "id": "JZCpodcasttopchartkids",
                             "displayName": "Kids & families"
                            },
                            {
                             "id": "JZCpodcasttopchartmusic",
                             "displayName": "Music"
                            },
                            {
                             "id": "JZCpodcasttopchartnews",
                             "displayName": "News & politics"
                            },
                            {
                             "id": "JZCpodcasttopchartreligion",
                             "displayName": "Religion & spirituality"
                            },
                            {
                             "id": "JZCpodcasttopchartscience",
                             "displayName": "Science & medicine"
                            },
                            {
                             "id": "JZCpodcasttopchartsociety",
                             "displayName": "Society & culture"
                            },
                            {
                             "id": "JZCpodcasttopchartsports",
                             "displayName": "Sports & recreation"
                            },
                            {
                             "id": "JZCpodcasttopcharttechnology",
                             "displayName": "Technology"
                            },
                            {
                             "id": "JZCpodcasttopcharttv",
                             "displayName": "TV & film"
                            }
                        ]
                    }
                ]
            }
        """

        res = self._make_call(mobileclient.GetBrowsePodcastHierarchy)

        return res.get('groups', [])

    def get_browse_podcast_series(self, genre_id='JZCpodcasttopchartall'):
        """Retrieve podcast series from browse podcasts by genre.

        :param genre_id: A podcast genre id as returned by :func:`get_podcast_browse_hierarchy`.
          Defaults to Top Chart 'All categories'.

        Returns a list of podcast series dicts.

        Here is an example podcast series dict::

            {
                'art': [
                    {
                        'aspectRatio': '1',
                        'autogen': False,
                        'kind': 'sj#imageRef',
                        'url': 'http://lh3.googleusercontent.com/liR-Pm7EhB58wrAa4uo9Y33LcJJ8keU...'
                    }
                ],
                'author': 'NBC Sports Radio',
                'continuationToken': '',
                'description': 'Mike Florio talks about the biggest NFL topics with the '
                              'people who are most passionate about the game: League execs, '
                              'players, coaches and the journalists who cover pro football.',
                'explicitType': '2',
                'link': 'https://audioboom.com/channel/pro-football-talk-live-with-mike-florio',
                'seriesId': 'I3iad5heqorm3nck6yp7giruc5i',
                'title': 'Pro Football Talk Live with Mike Florio',
                'totalNumEpisodes': 0
            }

        """

        res = self._make_call(mobileclient.ListBrowsePodcastSeries, id=genre_id)

        return res.get('series', [])

    def get_all_podcast_series(self, device_id=None, incremental=False,
                               include_deleted=None, updated_after=None):
        """Retrieve list of user-subscribed podcast series.

        :param device_id: (optional) defaults to ``android_id`` from login.

          Otherwise, provide a mobile device id as a string.
          Android device ids are 16 characters, while iOS ids
          are uuids with 'ios:' prepended.

          If you have already used Google Music on a mobile device,
          :func:`Mobileclient.get_registered_devices
          <gmusicapi.clients.Mobileclient.get_registered_devices>` will provide
          at least one working id. Omit ``'0x'`` from the start of the string if present.

          Registered computer ids (a MAC address) will not be accepted and will 403.

          Providing an unregistered mobile device id will register it to your account,
          subject to Google's `device limits
          <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1230356>`__.
          **Registering a device id that you do not own is likely a violation of the TOS.**

        :param incremental: if True, return a generator that yields lists
          of at most 1000 podcast series
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.

        :param include_deleted: ignored. Will be removed in a future release.

        :param updated_after: a datetime.datetime; defaults to unix epoch

        Returns a list of podcast series dicts.

        Here is an example podcast series dict::

            {
                'art': [
                    {
                        'aspectRatio': '1',
                        'autogen': False,
                        'kind': 'sj#imageRef',
                        'url': 'http://lh3.googleusercontent.com/bNoyxoGTwCGkUscMjHsvKe5W80uMOfq...'
                    }
                ],
                'author': 'Chris Hardwick',
                'continuationToken': '',
                'description': 'I am Chris Hardwick. I am on TV a lot and have a blog at '
                               'nerdist.com. This podcast is basically just me talking about '
                               'stuff and things with my two nerdy friends Jonah Ray and Matt '
                               'Mira, and usually someone more famous than all of us. '
                               'Occasionally we swear because that is fun. I hope you like '
                               "it, but if you don't I'm sure you will not hesitate to unfurl "
                               "your rage in the 'reviews' section because that's how the "
                               'Internet works.',
                'explicitType': '1',
                'link': 'http://nerdist.com/',
                'seriesId': 'Iliyrhelw74vdqrro77kq2vrdhy',
                'title': 'The Nerdist',
                'totalNumEpisodes': 829,
                'userPreferences': {
                    'autoDownload': False,
                    'notifyOnNewEpisode': False,
                    'subscribed': True
                }
            }

        """

        device_id = self._ensure_device_id(device_id)

        return self._get_all_items(mobileclient.ListPodcastSeries, incremental=incremental,
                                   updated_after=updated_after,
                                   device_id=device_id)

    def get_all_podcast_episodes(self, device_id=None, incremental=False,
                                 include_deleted=None, updated_after=None):
        """Retrieve list of episodes from user-subscribed podcast series.

        :param device_id: (optional) defaults to ``android_id`` from login.

          Otherwise, provide a mobile device id as a string.
          Android device ids are 16 characters, while iOS ids
          are uuids with 'ios:' prepended.

          If you have already used Google Music on a mobile device,
          :func:`Mobileclient.get_registered_devices
          <gmusicapi.clients.Mobileclient.get_registered_devices>` will provide
          at least one working id. Omit ``'0x'`` from the start of the string if present.

          Registered computer ids (a MAC address) will not be accepted and will 403.

          Providing an unregistered mobile device id will register it to your account,
          subject to Google's `device limits
          <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1230356>`__.
          **Registering a device id that you do not own is likely a violation of the TOS.**

        :param incremental: if True, return a generator that yields lists
          of at most 1000 podcast episodes
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.

        :param include_deleted: ignored. Will be removed in a future release.

        :param updated_after: a datetime.datetime; defaults to unix epoch

        Returns a list of podcast episode dicts.

        Here is an example podcast episode dict::

            {
                'art': [
                    {
                        'aspectRatio': '1',
                        'autogen': False,
                        'kind': 'sj#imageRef',
                        'url': 'http://lh3.googleusercontent.com/bNoyxoGTwCGkUscMjHsvKe5W80uMOfq...'
                    }
                ],
                'deleted': False,
                'description': 'Comedian Bill Burr yelled at Philadelphia, Chris vaguely '
                               'understands hockey, Jonah understands it even less, and Matt '
                               'is weirdly not tired of the running "Matt loves the Dave '
                               'Matthews Band" joke, though I\'m sure all of you are.',
                'durationMillis': '4310000',
                'episodeId': 'D6i26frpxu53t2ws3lpbjtpovum',
                'explicitType': '2',
                'fileSize': '69064793',
                'publicationTimestampMillis': '1277791500000',
                'seriesId': 'Iliyrhelw74vdqrro77kq2vrdhy',
                'seriesTitle': 'The Nerdist',
                'title': 'Bill Burr'
            }

        """
        device_id = self._ensure_device_id(device_id)

        return self._get_all_items(mobileclient.ListPodcastEpisodes, incremental=incremental,
                                   updated_after=updated_after,
                                   device_id=device_id)

    # TODO: Support multiple.
    @utils.enforce_id_param
    def add_podcast_series(self, podcast_id, notify_on_new_episode=False):
        """Subscribe to a podcast series.

        :param podcast_id: A podcast series id (hint: they always start with 'I').
        :param notify_on_new_episode: Get device notifications on new episodes.

        Returns podcast series id of added podcast series
        """

        mutate_call = mobileclient.BatchMutatePodcastSeries
        update_mutations = mutate_call.build_podcast_updates([
            {
                'seriesId': podcast_id,
                'subscribed': True,
                'userPreferences': {
                    'subscribed': True,
                    'notifyOnNewEpisode': notify_on_new_episode
                }
            }
        ])

        res = self._make_call(mutate_call, update_mutations)

        return res['mutate_response'][0]['id']

    # TODO: Support multiple.
    @utils.enforce_id_param
    def delete_podcast_series(self, podcast_id):
        """Unsubscribe to a podcast series.

        :param podcast_id: A podcast series id (hint: they always start with 'I').

        Returns podcast series id of removed podcast series
        """

        mutate_call = mobileclient.BatchMutatePodcastSeries
        update_mutations = mutate_call.build_podcast_updates([
            {
                'seriesId': podcast_id,
                'subscribed': False,
                'userPreferences': {
                    'subscribed': False,
                    'notifyOnNewEpisode': False
                }
            }
        ])

        res = self._make_call(mutate_call, update_mutations)

        return res['mutate_response'][0]['id']

    # TODO: Support multiple.
    @utils.enforce_id_param
    def edit_podcast_series(self, podcast_id, subscribe=True, notify_on_new_episode=False):
        """Edit a podcast series subscription.

        :param podcast_id: A podcast series id (hint: they always start with 'I').
        :param subscribe: Subscribe to podcast.
        :param notify_on_new_episode: Get device notifications on new episodes.

        Returns podcast series id of edited podcast series
        """

        mutate_call = mobileclient.BatchMutatePodcastSeries
        update_mutations = mutate_call.build_podcast_updates([
            {
                'seriesId': podcast_id,
                'subscribed': subscribe,
                'userPreferences': {
                    'subscribed': subscribe,
                    'notifyOnNewEpisode': notify_on_new_episode
                }
            }
        ])

        res = self._make_call(mutate_call, update_mutations)

        return res['mutate_response'][0]['id']

    @utils.enforce_id_param
    def get_podcast_episode_stream_url(self, podcast_episode_id, device_id=None, quality='hi'):
        """Returns a url that will point to an mp3 file.

        :param podcast_episde_id: a single podcast episode id (hint: they always start with 'D').

        :param device_id: (optional) defaults to ``android_id`` from login.

          Otherwise, provide a mobile device id as a string.
          Android device ids are 16 characters, while iOS ids
          are uuids with 'ios:' prepended.

          If you have already used Google Music on a mobile device,
          :func:`Mobileclient.get_registered_devices
          <gmusicapi.clients.Mobileclient.get_registered_devices>` will provide
          at least one working id. Omit ``'0x'`` from the start of the string if present.

          Registered computer ids (a MAC address) will not be accepted and will 403.

          Providing an unregistered mobile device id will register it to your account,
          subject to Google's `device limits
          <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1230356>`__.
          **Registering a device id that you do not own is likely a violation of the TOS.**

        :param quality: (optional) stream bits per second quality
          One of three possible values, hi: 320kbps, med: 160kbps, low: 128kbps.
          The default is hi

        When handling the resulting url, keep in mind that:
            * you will likely need to handle redirects
            * the url expires after a minute
            * only one IP can be streaming music at once.
              This can result in an http 403 with
              ``X-Rejected-Reason: ANOTHER_STREAM_BEING_PLAYED``.

        The file will not contain metadata.
        """

        device_id = self._ensure_device_id(device_id)

        return self._make_call(
            mobileclient.GetPodcastEpisodeStreamUrl, podcast_episode_id, device_id, quality)

    def get_podcast_series_info(self, podcast_series_id, max_episodes=50):
        """Retrieves information about a podcast series.

        :param podcast_series_id: A podcast series id (hint: they always start with 'I').
        :param max_episodes: Maximum number of episodes to retrieve

        Returns a dict, eg::

            {
                'art': [
                    {
                        'aspectRatio': '1',
                        'autogen': False,
                        'kind': 'sj#imageRef',
                        'url': 'http://lh3.googleusercontent.com/bNoyxoGTwCGkUscMjHsvKe5W80uMOfq...'
                    }
                ],
                'author': 'Chris Hardwick',
                'continuationToken': '',
                'description': 'I am Chris Hardwick. I am on TV a lot and have a blog at '
                               'nerdist.com. This podcast is basically just me talking about '
                               'stuff and things with my two nerdy friends Jonah Ray and Matt '
                               'Mira, and usually someone more famous than all of us. '
                               'Occasionally we swear because that is fun. I hope you like '
                               "it, but if you don't I'm sure you will not hesitate to unfurl "
                               "your rage in the 'reviews' section because that's how the "
                               'Internet works.',
                'episodes': [
                    {
                        'art': [
                            {
                                'aspectRatio': '1',
                                'autogen': False,
                                'kind': 'sj#imageRef',
                                'url': 'http://lh3.googleusercontent.com/bNoyxoGTwCGkUscMjHsvKe5...'
                            }
                        ],
                        'description': 'Sarah Jessica Parker (Sex and the City) '
                                       'chats with Chris about growing up without '
                                       'television, her time on Square Pegs and '
                                       'her character in L.A. Story. Sarah Jessica '
                                       'then talks about how she felt when she first '
                                       'got the part of Carrie on Sex and the '
                                       'City, how she dealt with her sudden '
                                       'celebrity of being Carrie Bradshaw and they '
                                       'come up with a crazy theory about the show! '
                                       'They also talk about Sarah Jessica’s new '
                                       'show Divorce on HBO!',
                        'durationMillis': '5101000',
                        'episodeId': 'Dcz67vtkhrerzh4hptfqpadt5vm',
                        'explicitType': '1',
                        'fileSize': '40995252',
                        'publicationTimestampMillis': '1475640000000',
                        'seriesId': 'Iliyrhelw74vdqrro77kq2vrdhy',
                        'seriesTitle': 'The Nerdist',
                        'title': 'Sarah Jessica Parker'
                    },
                ]
                'explicitType': '1',
                'link': 'http://nerdist.com/',
                'seriesId': 'Iliyrhelw74vdqrro77kq2vrdhy',
                'title': 'The Nerdist',
                'totalNumEpisodes': 829,
                'userPreferences': {
                    'autoDownload': False,
                    'notifyOnNewEpisode': False,
                    'subscribed': True
                }
            }

        """

        return self._make_call(mobileclient.GetPodcastSeries, podcast_series_id, max_episodes)

    def get_podcast_episode_info(self, podcast_episode_id):
        """Retrieves information about a podcast episode.

        :param podcast_episode_id: A podcast episode id (hint: they always start with 'D').

        Returns a dict, eg::

            {
                'art': [
                    {
                        'aspectRatio': '1',
                        'autogen': False,
                        'kind': 'sj#imageRef',
                        'url': 'http://lh3.googleusercontent.com/bNoyxoGTwCGkUscMjHsvKe5...'
                    }
                ],
                'description': 'Sarah Jessica Parker (Sex and the City) '
                               'chats with Chris about growing up without '
                               'television, her time on Square Pegs and '
                               'her character in L.A. Story. Sarah Jessica '
                               'then talks about how she felt when she first '
                               'got the part of Carrie on Sex and the '
                               'City, how she dealt with her sudden '
                               'celebrity of being Carrie Bradshaw and they '
                               'come up with a crazy theory about the show! '
                               'They also talk about Sarah Jessica’s new '
                               'show Divorce on HBO!',
                'durationMillis': '5101000',
                'episodeId': 'Dcz67vtkhrerzh4hptfqpadt5vm',
                'explicitType': '1',
                'fileSize': '40995252',
                'publicationTimestampMillis': '1475640000000',
                'seriesId': 'Iliyrhelw74vdqrro77kq2vrdhy',
                'seriesTitle': 'The Nerdist',
                'title': 'Sarah Jessica Parker'
            }

        """

        return self._make_call(mobileclient.GetPodcastEpisode, podcast_episode_id)

    def create_station(self, name,
                       track_id=None, artist_id=None, album_id=None,
                       genre_id=None, playlist_token=None, curated_station_id=None):
        """Creates a radio station and returns its id.

        :param name: the name of the station to create
        :param \*_id: the id of an item to seed the station from.
        :param playlist_token: The shareToken of a playlist to seed the station from.

        Exactly one of the id/token params must be provided, or ValueError
        will be raised.
        """
        # TODO could expose include_tracks

        seed = {}
        if track_id is not None:
            if track_id[0] == 'T':
                seed['trackId'] = track_id
                seed['seedType'] = 2
            else:
                seed['trackLockerId'] = track_id
                seed['seedType'] = 1

        if artist_id is not None:
            seed['artistId'] = artist_id
            seed['seedType'] = 3
        if album_id is not None:
            seed['albumId'] = album_id
            seed['seedType'] = 4
        if genre_id is not None:
            seed['genreId'] = genre_id
            seed['seedType'] = 5
        if playlist_token is not None:
            seed['playlistShareToken'] = playlist_token
            seed['seedType'] = 8
        if curated_station_id is not None:
            seed['curatedStationId'] = curated_station_id
            seed['seedType'] = 9

        if len(seed) > 2:
            raise ValueError('exactly one {track,artist,album,genre}_id must be provided')

        mutate_call = mobileclient.BatchMutateStations
        add_mutation = mutate_call.build_add(name, seed, include_tracks=False, num_tracks=0)
        res = self._make_call(mutate_call, [add_mutation])

        return res['mutate_response'][0]['id']

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    def delete_stations(self, station_ids):
        """Deletes radio stations and returns their ids.

        :param station_ids: a single id, or a list of ids to delete
        """

        mutate_call = mobileclient.BatchMutateStations
        delete_mutations = mutate_call.build_deletes(station_ids)
        res = self._make_call(mutate_call, delete_mutations)

        return [s['id'] for s in res['mutate_response']]

    def get_all_stations(self, incremental=False, include_deleted=None, updated_after=None):
        """Retrieve all library stations.

        Returns a list of dictionaries that each represent a radio station.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 stations
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.
        :param include_deleted: ignored. Will be removed in a future release.
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
        return self._get_all_items(mobileclient.ListStations, incremental,
                                   updated_after=updated_after)

    def get_station_tracks(self, station_id, num_tracks=25, recently_played_ids=None):
        """Returns a list of dictionaries that each represent a track.

        Each call performs a separate sampling (with replacement?)
        from all possible tracks for the station.

        Nonexistent stations will return an empty list.

        :param station_id: the id of a radio station to retrieve tracks from.
          Use the special id ``'IFL'`` for the "I'm Feeling Lucky" station.
        :param num_tracks: the number of tracks to retrieve
        :param recently_played_ids: a list of recently played track
          ids retrieved from this station. This avoids playing
          duplicates.

        See :func:`get_all_songs` for the format of a track dictionary.
        """

        if recently_played_ids is None:
            recently_played_ids = []

        def add_track_type(track_id):
            if track_id[0] == 'T':
                return {'id': track_id, 'type': 1}
            else:
                return {'id': track_id, 'type': 0}

        recently_played = [add_track_type(track_id) for track_id in recently_played_ids]

        res = self._make_call(mobileclient.ListStationTracks,
                              station_id, num_tracks, recently_played=recently_played)

        stations = res.get('data', {}).get('stations')
        if not stations:
            return []

        return stations[0].get('tracks', [])

    def search(self, query, max_results=50):
        """Queries Google Music for content.

        :param query: a string keyword to search with. Capitalization and punctuation are ignored.
        :param max_results: Maximum number of items to be retrieved.
          The maximum accepted value is 100. If set higher, results are limited to 10.

        The results are returned in a dictionary with keys:
        ``album_hits, artist_hits, playlist_hits, podcast_hits,
          situation_hits, song_hits, station_hits, video_hits``
        containing lists of results of that type.

        Free account search is restricted so may not contain hits for all result types.

        Here is a sample of results for a search of ``'workout'``::

            {
                'album_hits': [{
                    'album': {
                        'albumArtRef': 'http://lh5.ggpht.com/DVIg4GiD6msHfgPs_Vu_2eRxCyAoz0fF...',
                        'albumArtist': 'J.Cole',
                        'albumId': 'Bfp2tuhynyqppnp6zennhmf6w3y',
                        'artist': 'J.Cole',
                        'artistId': ['Ajgnxme45wcqqv44vykrleifpji'],
                        'description_attribution': {
                            'kind': 'sj#attribution',
                            'license_title': 'Creative Commons Attribution CC-BY',
                            'license_url': 'http://creativecommons.org/licenses/by/4.0/legalcode',
                            'source_title': 'Freebase',
                            'source_url': ''
                        },
                        'explicitType': '1',
                        'kind': 'sj#album',
                        'name': 'Work Out',
                        'year': 2011
                    },
                    'type': '3'
                }],
                'artist_hits': [{
                    'artist': {
                        'artistArtRef': 'http://lh3.googleusercontent.com/MJe-cDw9uQ-pUagoLlm...',
                        'artistArtRefs': [{
                            'aspectRatio': '2',
                            'autogen': False,
                            'kind': 'sj#imageRef',
                            'url': 'http://lh3.googleusercontent.com/MJe-cDw9uQ-pUagoLlmKX3x_K...'
                        }],
                        'artistId': 'Ajgnxme45wcqqv44vykrleifpji',
                        'artist_bio_attribution': {
                            'kind': 'sj#attribution',
                            'source_title': 'David Jeffries, Rovi'
                        },
                        'kind': 'sj#artist',
                        'name': 'J. Cole'
                    },
                    'type': '2'
                }],
                'playlist_hits': [{
                    'playlist': {
                        'albumArtRef': [
                            {'url': 'http://lh3.googleusercontent.com/KJsAhrg8Jk_5A4xYLA68LFC...'}
                        ],
                        'description': 'Workout Plan ',
                        'kind': 'sj#playlist',
                        'name': 'Workout',
                        'ownerName': 'Ida Sarver',
                        'shareToken': 'AMaBXyktyF6Yy_G-8wQy8Rru0tkueIbIFblt2h0BpkvTzHDz-fFj6P...',
                        'type': 'SHARED'
                    },
                    'type': '4'
                }],
                'podcast_hits': [{
                    'series': {
                        'art': [
                            {
                                'aspectRatio': '1',
                                'autogen': False,
                                'kind': 'sj#imageRef',
                                'url': 'https://lh3.googleusercontent.com/je4lsaiQCdfcOWoYm3Z_mC...'
                            }
                        ],
                        'author': 'Steve Boyett',
                        'continuationToken': '',
                        'copyright': 'Music copyright c the respective artists. All other '
                                     'material c2006, 2016 by Podrunner, LLC. All rights '
                                     'reserved. For personal use only. Unauthorized '
                                     'reproduction, sale, rental, exchange, public '
                                     'performance, or broadcast of this audio is '
                                     'prohibited.',
                        'description': 'Nonstop, one-hour, high-energy workout music mixes '
                                       "to help you groove while you move. Podrunner's "
                                       'fixed-tempo and interval exercise mixes are '
                                       'perfect for power walking, jogging, running, '
                                       'spinning, elliptical, aerobics, and many other '
                                       'tempo-based forms of exercise. An iTunes '
                                       'award-winner six years in a row!',
                        'explicitType': '2',
                        'link': 'http://www.podrunner.com/',
                        'seriesId': 'Ilx4ufdua5rdvzplnojtloulo3a',
                        'title': 'PODRUNNER: Workout Music',
                        'totalNumEpisodes': 0
                    },
                    'type': '9'
                }],
                'situation_hits': [{
                    'situation': {
                        'description':
                            'Level up and enter beast mode with some loud, aggressive music.',
                        'id': 'Nrklpcyfewwrmodvtds5qlfp5ve',
                        'imageUrl': 'http://lh3.googleusercontent.com/Cd8WRMaG_pDwjTC_dSPIIuf...',
                        'title': 'Entering Beast Mode',
                        'wideImageUrl': 'http://lh3.googleusercontent.com/8A9S-nTb5pfJLcpS8P...'},
                    'type': '7'
                }],
                'song_hits': [{
                    'track': {
                        'album': 'Work Out',
                        'albumArtRef': [{
                            'aspectRatio': '1',
                            'autogen': False,
                            'kind': 'sj#imageRef',
                            'url': 'http://lh5.ggpht.com/DVIg4GiD6msHfgPs_Vu_2eRxCyAoz0fFdxj5w...'
                        }],
                        'albumArtist': 'J.Cole',
                        'albumAvailableForPurchase': True,
                        'albumId': 'Bfp2tuhynyqppnp6zennhmf6w3y',
                        'artist': 'J Cole',
                        'artistId': ['Ajgnxme45wcqqv44vykrleifpji', 'Ampniqsqcwxk7btbgh5ycujij5i'],
                        'composer': '',
                        'discNumber': 1,
                        'durationMillis': '234000',
                        'estimatedSize': '9368582',
                        'explicitType': '1',
                        'genre': 'Pop',
                        'kind': 'sj#track',
                        'nid': 'Tq3nsmzeumhilpegkimjcnbr6aq',
                        'primaryVideo': {
                            'id': '6PN78PS_QsM',
                            'kind': 'sj#video',
                            'thumbnails': [{
                                'height': 180,
                                'url': 'https://i.ytimg.com/vi/6PN78PS_QsM/mqdefault.jpg',
                                'width': 320
                            }]
                        },
                        'storeId': 'Tq3nsmzeumhilpegkimjcnbr6aq',
                        'title': 'Work Out',
                        'trackAvailableForPurchase': True,
                        'trackAvailableForSubscription': True,
                        'trackNumber': 1,
                        'trackType': '7',
                        'year': 2011
                    },
                    'type': '1'
                }],
                'station_hits': [{
                    'station': {
                        'compositeArtRefs': [{
                                'aspectRatio': '1',
                                'kind': 'sj#imageRef',
                                'url': 'http://lh3.googleusercontent.com/3aD9mFppy6PwjADnjwv_w...'
                        }],
                        'contentTypes': ['1'],
                        'description':
                            'These riff-tastic metal tracks are perfect '
                            'for getting the blood pumping.',
                        'imageUrls': [{
                            'aspectRatio': '1',
                            'autogen': False,
                            'kind': 'sj#imageRef',
                            'url': 'http://lh5.ggpht.com/YNGkFdrtk43e8H941fuAHjflrNZ1CJUeqdoys...'
                        }],
                        'kind': 'sj#radioStation',
                        'name': 'Heavy Metal Workout',
                        'seed': {
                            'curatedStationId': 'Lcwg73w3bd64hsrgarnorif52r',
                            'kind': 'sj#radioSeed',
                            'seedType': '9'
                        },
                        'skipEventHistory': [],
                        'stationSeeds': [{
                            'curatedStationId': 'Lcwg73w3bd64hsrgarnorif52r',
                            'kind': 'sj#radioSeed',
                            'seedType': '9'}
                        ]},
                    'type': '6'
                }],
                'video_hits': [{
                    'score': 629.6226806640625,
                    'type': '8',
                    'youtube_video': {
                        'id': '6PN78PS_QsM',
                        'kind': 'sj#video',
                        'thumbnails': [{
                            'height': 180,
                            'url': 'https://i.ytimg.com/vi/6PN78PS_QsM/mqdefault.jpg',
                            'width': 320
                        }],
                        'title': 'J. Cole - Work Out'
                    }
                }]
            }
        """

        res = self._make_call(mobileclient.Search, query, max_results)

        hits = res.get('entries', [])

        hits_by_type = defaultdict(list)
        for hit in hits:
            hits_by_type[hit['type']].append(hit)

        return {'album_hits': hits_by_type['3'],
                'artist_hits': hits_by_type['2'],
                'playlist_hits': hits_by_type['4'],
                'podcast_hits': hits_by_type['9'],
                'situation_hits': hits_by_type['7'],
                'song_hits': hits_by_type['1'],
                'station_hits': hits_by_type['6'],
                'video_hits': hits_by_type['8']}

    @utils.enforce_id_param
    def get_artist_info(self, artist_id, include_albums=True, max_top_tracks=5, max_rel_artist=5):
        """Retrieves details on an artist.

        :param artist_id: an artist id (hint: they always start with 'A')
        :param include_albums: when True, create the ``'albums'`` substructure
        :param max_top_tracks: maximum number of top tracks to retrieve
        :param max_rel_artist: maximum number of related artists to retrieve

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

    def _get_all_items(self, call, incremental, **kwargs):
        """
        :param call: protocol.McCall
        :param incremental: bool

        kwargs are passed to the call.
        """
        if not incremental:
            # slight optimization: get more items in a page
            kwargs.setdefault('max_results', 20000)

        generator = self._get_all_items_incremental(call, **kwargs)
        if incremental:
            return generator

        return [s for chunk in generator for s in chunk]

    def _get_all_items_incremental(self, call, **kwargs):
        """Return a generator of lists of tracks.

        kwargs are passed to the call."""

        get_next_chunk = True
        lib_chunk = {}
        next_page_token = None

        while get_next_chunk:
            lib_chunk = self._make_call(call,
                                        start_token=next_page_token,
                                        **kwargs)

            items = []

            for item in lib_chunk['data']['items']:
                if 'userPreferences' in item:
                    if item['userPreferences'].get('subscribed', False):
                        items.append(item)
                elif not item.get('deleted', False):
                    items.append(item)

            # Conditional prevents generator from yielding empty
            # list for last page of podcast list calls.
            if items:
                yield items

            # Podcast list calls always include 'nextPageToken' in responses.
            # We have to check to make sure we don't get stuck in an infinite loop
            # by comparing the previous and next page tokens.
            prev_page_token = next_page_token
            next_page_token = lib_chunk.get('nextPageToken')

            get_next_chunk = (next_page_token and next_page_token != prev_page_token)

    @utils.enforce_id_param
    def get_album_info(self, album_id, include_tracks=True):
        """Retrieves details on an album.

        :param album_id: an album id (hint: they always start with 'B')
        :param include_tracks: when True, create the ``'tracks'`` substructure

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

        :param store_track_id: a store track id (hint: they always start with 'T')

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

    def get_genres(self, parent_genre_id=None):
        """Retrieves information on Google Music genres.

        :param parent_genre_id: (optional) If provided, only child genres
          will be returned. By default, all root genres are returned.
          If this id is invalid, an empty list will be returned.

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
        to seed a radio station.
        """

        res = self._make_call(mobileclient.GetGenres, parent_genre_id)

        # An invalid parent genre won't respond with a genres key.
        return res.get('genres', [])
