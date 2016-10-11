# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals
from future.utils import PY3
from past.builtins import basestring
from builtins import *  # noqa

import warnings

if PY3:
    from urllib.parse import parse_qsl, urlparse
else:
    from urlparse import parse_qsl, urlparse

import gmusicapi
from gmusicapi.clients.shared import _Base
from gmusicapi.exceptions import GmusicapiWarning
from gmusicapi.protocol import webclient
from gmusicapi.utils import utils
import gmusicapi.session


class Webclient(_Base):
    """Allows library management and streaming by posing as the
    music.google.com webclient.

    Uploading is not supported by this client (use the :class:`Musicmanager`
    to upload).

    Any methods in this class that are duplicated by
    the :class:`Mobileclient` are deprecated, and will generate a
    warning at runtime.

    The following methods are *not* deprecated:

        * :func:`get_shared_playlist_info`
        * :func:`get_song_download_info`
        * :func:`get_stream_urls`
        * :func:`get_stream_audio`
        * :func:`report_incorrect_match`
        * :func:`upload_album_art`
    """

    _session_class = gmusicapi.session.Webclient

    def __init__(self, debug_logging=True, validate=True, verify_ssl=True):
        warnings.warn(
            "Webclient functionality is not tested nor well supported. "
            "Use Mobileclient or Musicmanager if possible.",
            GmusicapiWarning
        )

        super(Webclient, self).__init__(self.__class__.__name__,
                                        debug_logging,
                                        validate,
                                        verify_ssl)

    def login(self, email, password):
        """Authenticates the webclient.
        Returns ``True`` on success, ``False`` on failure.

        :param email: eg ``'test@gmail.com'`` or just ``'test'``.
        :param password: the account's password.
          This is not stored locally, and is sent securely over SSL.
          App-specific passwords are not supported on the webclient.

        Users who don't use two-factor auth will likely need to enable
        `less secure login <https://www.google.com/settings/security/lesssecureapps>`__.
        If this is needed, a warning will be logged during login (which will print to stderr
        in the default logging configuration).
        """

        if not self.session.login(email, password):
            self.logger.info("failed to authenticate")
            return False

        self.logger.info("authenticated")

        return True

    def logout(self):
        return super(Webclient, self).logout()

    def get_shared_playlist_info(self, share_token):
        """
        Returns a dictionary with four keys: author, description, num_tracks, and title.

        :param share_token: from ``playlist['shareToken']``, or a playlist share
          url (``https://play.google.com/music/playlist/<token>``).

          Note that tokens from urls will need to be url-decoded,
          eg ``AM...%3D%3D`` becomes ``AM...==``.
        """

        res = self._make_call(webclient.GetSharedPlaylist, '', share_token)
        num_tracks = len(res[1][0])
        md = res[1][1]

        return {
            u'author': md[8],
            u'description': md[7],
            u'num_tracks': num_tracks,
            u'title': md[1],
        }

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

        # TODO the protocol expects a list of songs - could extend with accept_singleton
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

        # TODO shouldn't session.send be used throughout?

        if len(urls) == 1:
            return self.session._rsession.get(urls[0]).content

        # AA tracks are separated into multiple files.
        # the url contains the range of each file to be used.

        range_pairs = [[int(s) for s in val.split('-')]
                       for url in urls
                       for key, val in parse_qsl(urlparse(url)[4])
                       if key == 'range']

        stream_pieces = bytearray()
        prev_end = 0
        headers = None

        for url, (start, end) in zip(urls, range_pairs):
            if use_range_header or use_range_header is None:
                headers = {'Range': 'bytes=' + str(prev_end - start) + '-'}

            audio = self.session._rsession.get(url, headers=headers).content

            if end - prev_end != len(audio) - 1:
                # content length is not in the right range

                if use_range_header:
                    # the user didn't want automatic response fixup
                    raise IOError('use_range_header is True but the response'
                                  ' was not the correct content length.'
                                  ' This might be caused by a (poorly-written) http proxy.')

                # trim to the proper range
                audio = audio[prev_end - start:]

            stream_pieces.extend(audio)

            prev_end = end + 1

        return bytes(stream_pieces)

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    def report_incorrect_match(self, song_ids):
        """Equivalent to the 'Fix Incorrect Match' button, this requests re-uploading of songs.
        Returns the song_ids provided.

        :param song_ids: a list of song ids to report, or a single song id.

        Note that if you uploaded a song through gmusicapi, it won't be reuploaded
        automatically - this currently only works for songs uploaded with the Music Manager.
        See issue `#89 <https://github.com/simon-weber/gmusicapi/issues/89>`__.

        This should only be used on matched tracks (``song['type'] == 6``).
        """

        self._make_call(webclient.ReportBadSongMatch, song_ids)

        return song_ids

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    def upload_album_art(self, song_ids, image_filepath):
        """Uploads an image and sets it as the album art for songs.
        Returns a url to the image on Google's servers.

        :param song_ids: a list of song ids, or a single song id.
        :param image_filepath: filepath of the art to use. jpg and png are known to work.

        This function will *always* upload the provided image, even if it's already uploaded.
        If the art is already uploaded and set for another song, copy over the
        value of the ``'albumArtUrl'`` key using :func:`Mobileclient.change_song_metadata` instead.
        """

        res = self._make_call(webclient.UploadImage, image_filepath)
        url = res['imageUrl']

        song_dicts = [dict((('id', id), ('albumArtUrl', url))) for id in song_ids]

        self._make_call(webclient.ChangeSongMetadata, song_dicts)

        return url

    @utils.accept_singleton(dict)
    @utils.empty_arg_shortcircuit
    def change_song_metadata(self, songs):
        """Changes metadata of songs.

        Returns a list of the song ids changed.

        :param songs: a list of song dictionaries, each dictionary must contain valid song 'id'

        The following fields are supported: title, album, albumArtist, artist
        """

        self._make_call(webclient.ChangeSongMetadata, songs)

        return list(song['id'] for song in songs)

    # deprecated methods follow:

    @utils.deprecated('prefer Mobileclient.create_playlist')
    def create_playlist(self, name, description=None, public=False):
        """
        Creates a playlist and returns its id.

        :param name: the name of the playlist.
        :param description: (optional) the description of the playlist.
        :param public: if True and the user has All Access, create a shared playlist.
        """
        res = self._make_call(webclient.CreatePlaylist, name, description, public)

        return res[1][0]

    @utils.deprecated('prefer Mobileclient.get_registered_devices')
    def get_registered_devices(self):
        """
        Returns a list of dictionaries representing devices associated with the account.

        Performing the :class:`Musicmanager` OAuth flow will register a device
        of type 1.

        Installing the Google Music app on an android or ios device
        and logging into it will register a device of type 2 or 3,
        which is used for streaming with the :class:`Mobileclient`.

        Here is an example response::

            [
              {
                u'deviceType': 1,  # laptop/desktop
                u'id': u'00:11:22:33:AA:BB',
                u'lastAccessedFormatted': u'May 24, 2015',
                u'lastAccessedTimeMillis': 1432468588200,  # utc-millisecond
                u'lastEventTimeMillis': 1434211605335,
                u'name': u'my computer'},
              },
              {
                u'deviceType': 2,  # android device
                u'carrier': u'Google',
                u'id': u'0x00112233aabbccdd',  # remove 0x when streaming
                u'lastAccessedFormatted': u'September 19, 2015',
                u'lastAccessedTimeMillis': 1442706069906,
                u'lastEventTimeMillis': 1435271137193,
                u'manufacturer': u'Asus',
                u'model': u'Nexus 7',
                u'name': u'my nexus 7'
              },
              {
                u'deviceType': 3,  # ios device
                u'id': u'ios:01234567-0123-0123-0123-0123456789AB',
                u'lastAccessedFormatted': u'June 25, 2015',
                u'lastAccessedTimeMillis': 1435271588780,
                u'lastEventTimeMillis': 1435271442417,
                u'name': u'my iphone'
              }
            ]
        """

        # TODO sessionid stuff
        res = self._make_call(webclient.GetSettings, '')
        return res['settings']['uploadDevice']

    @utils.accept_singleton(basestring)
    @utils.enforce_ids_param
    @utils.empty_arg_shortcircuit
    @utils.deprecated('prefer Mobileclient.delete_songs')
    def delete_songs(self, song_ids):
        """**Deprecated**: prefer :func:`Mobileclient.delete_songs`.

        Deletes songs from the entire library. Returns a list of deleted song ids.

        :param song_ids: a list of song ids, or a single song id.
        """

        res = self._make_call(webclient.DeleteSongs, song_ids)

        return res['deleteIds']

    @utils.accept_singleton(basestring, 2)
    @utils.enforce_ids_param(2)
    @utils.enforce_id_param
    @utils.empty_arg_shortcircuit(position=2)
    @utils.deprecated('prefer Mobileclient.add_songs_to_playlist')
    def add_songs_to_playlist(self, playlist_id, song_ids):
        """**Deprecated**: prefer :func:`Mobileclient.add_songs_to_playlist`.

        Appends songs to a playlist.
        Returns a list of (song id, playlistEntryId) tuples that were added.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.

        Playlists have a maximum size of 1000 songs.
        """

        res = self._make_call(webclient.AddToPlaylist, playlist_id, song_ids)
        new_entries = res['songIds']

        return [(e['songId'], e['playlistEntryId']) for e in new_entries]

    @utils.accept_singleton(basestring, 2)
    @utils.enforce_ids_param(2)
    @utils.enforce_id_param
    @utils.empty_arg_shortcircuit(position=2)
    @utils.deprecated('prefer Mobileclient.remove_entries_from_playlist')
    def remove_songs_from_playlist(self, playlist_id, sids_to_match):
        """**Deprecated**: prefer :func:`Mobileclient.remove_entries_from_playlist`.

        Removes all copies of the given song ids from a playlist.
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
            # Call returns "sid_eid" strings.
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

        # GM requires the song ids in the call as well; find them.
        playlist_tracks = self.get_playlist_songs(playlist_id)
        remove_eid_set = set(entry_ids_to_remove)

        e_s_id_pairs = [(t["id"], t["playlistEntryId"])
                        for t in playlist_tracks
                        if t["playlistEntryId"] in remove_eid_set]

        num_not_found = len(entry_ids_to_remove) - len(e_s_id_pairs)
        if num_not_found > 0:
            self.logger.warning("when removing, %d entry ids could not be found in playlist id %s",
                                num_not_found, playlist_id)

        # Unzip the pairs.
        sids, eids = list(zip(*e_s_id_pairs))

        res = self._make_call(webclient.DeleteSongs, sids, playlist_id, eids)

        return res['deleteIds']
