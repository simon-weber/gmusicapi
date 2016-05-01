from __future__ import print_function, division, absolute_import, unicode_literals
from future import standard_library
standard_library.install_aliases()
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

        Currently, only the ``rating`` key can be changed.
        Set it to ``'0'`` (no thumb), ``'1'`` (down thumb), or ``'5'`` (up thumb)
        unless you're using the 5-star ratings lab.

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
    def add_store_track(self, store_song_id):
        """Adds a store track to the library

        Returns the library track id of added store track.

        :param store_song_id: store song id
        """
        # TODO is there a way to do this on multiple tracks at once?
        # problem is with gathering store track info

        store_track_info = self.get_track_info(store_song_id)

        mutate_call = mobileclient.BatchMutateTracks
        add_mutation = mutate_call.build_track_add(store_track_info)
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

        if device_id is None:
            device_id = self.android_id

        if len(device_id) == 16 and re.match('^[a-z0-9]*$', device_id):
            # android device ids are now sent in base 10
            device_id = str(int(device_id, 16))

        return self._make_call(mobileclient.GetStreamUrl, song_id, device_id, quality)

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
                                   incremental=False, include_deleted=False,
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
        :param max_results: Maximum number of items to be retrieved

        The results are returned in a dictionary with keys:
        ``album_hits, artist_hits, playlist_hits, situation_hits,
        song_hits, station_hits, video_hits``
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
                items = [item for item in items
                         if not item.get('deleted', False)]

            yield items

            get_next_chunk = 'nextPageToken' in lib_chunk

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
