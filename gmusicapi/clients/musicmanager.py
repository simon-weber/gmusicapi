# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals
from future.utils import PY3
from past.builtins import basestring
from builtins import *  # noqa

import os
from socket import gethostname
import time
from uuid import getnode as getmac

if PY3:
    from urllib.parse import unquote
else:
    from urllib import unquote

import httplib2  # included with oauth2client
from oauth2client.client import TokenRevokeError

import gmusicapi
from gmusicapi.clients.shared import _OAuthClient
from gmusicapi.appdirs import my_appdirs
from gmusicapi.exceptions import CallFailure, NotLoggedIn
from gmusicapi.protocol import musicmanager, upload_pb2, locker_pb2
from gmusicapi.utils import utils
from gmusicapi import session


class Musicmanager(_OAuthClient):
    """Allows uploading by posing as Google's Music Manager.

    Musicmanager uses OAuth, so a plaintext email and password are not required
    when logging in.

    For most authors and users of gmusicapi scripts,
    :func:`perform_oauth` should be run once per machine to
    store credentials to disk.
    Future calls to :func:`login` can use
    use the stored credentials by default.

    Some authors may want more control over the OAuth flow.
    In this case, credentials can be directly provided to :func:`login`.
    """
    OAUTH_FILEPATH = os.path.join(my_appdirs.user_data_dir, 'oauth.cred')

    _session_class = session.Musicmanager

    def __init__(self, debug_logging=True, validate=True, verify_ssl=True):
        super(Musicmanager, self).__init__(self.__class__.__name__,
                                           debug_logging,
                                           validate,
                                           verify_ssl)

    def login(self, oauth_credentials=OAUTH_FILEPATH,
              uploader_id=None, uploader_name=None):
        """Authenticates the Music Manager using OAuth.
        Returns ``True`` on success, ``False`` on failure.

        Unlike the :class:`Webclient`, OAuth allows authentication without
        providing plaintext credentials to the application.

        In most cases, the default parameters should be acceptable. Users on
        virtual machines will want to provide `uploader_id`.

        :param oauth_credentials: ``oauth2client.client.OAuth2Credentials`` or the path to a
          ``oauth2client.file.Storage`` file. By default, the same default path used by
          :func:`perform_oauth` is used.

          Endusers will likely call :func:`perform_oauth` once to write
          credentials to disk and then ignore this parameter.

          This param
          is mostly intended to allow flexibility for developers of a
          3rd party service who intend to perform their own OAuth flow
          (eg on their website).

        :param uploader_id: a unique id as a MAC address, eg ``'00:11:22:33:AA:BB'``.
          This should only be provided in cases where the default
          (host MAC address incremented by 1) will not work.

          Upload behavior is undefined if a Music Manager uses the same id, especially when
          reporting bad matches.

          ``ValueError`` will be raised if this is provided but not in the proper form.

          ``OSError`` will be raised if this is not provided and a real MAC could not be
          determined (most common when running on a VPS).

          If provided, use the same id on all future runs for this machine,
          because of the upload device limit explained below.

        :param uploader_name: human-readable non-unique id; default is
          ``"<hostname> (gmusicapi-{version})"``.

          This doesn't appear to be a part of authentication at all.
          Registering with (id, name = X, Y) and logging in with
          (id, name = X, Z) works, and does not change the server-stored
          uploader_name.

        There are hard limits on how many upload devices can be registered; refer to `Google's
        docs <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1230356>`__. There
        have been limits on deauthorizing devices in the past, so it's smart not to register
        more devices than necessary.
        """

        return (self._oauth_login(oauth_credentials) and
                self._perform_upauth(uploader_id, uploader_name))

    def _perform_upauth(self, uploader_id, uploader_name):
        """Auth or register ourselves as an upload client.

        Return True on success; see :py:func:`login` for params.
        """

        if uploader_id is None:
            mac_int = getmac()
            if (mac_int >> 40) % 2:
                self.session.logout()
                raise OSError('a valid MAC could not be determined.'
                              ' Provide uploader_id (and be'
                              ' sure to provide the same one on future runs).')

            else:
                # distinguish us from a Music Manager on this machine
                mac_int = (mac_int + 1) % (1 << 48)

            uploader_id = utils.create_mac_string(mac_int)

        if not utils.is_valid_mac(uploader_id):
            self.session.logout()
            raise ValueError('uploader_id is not in a valid form.'
                             '\nProvide 6 pairs of hex digits'
                             ' with capital letters',
                             ' (eg "00:11:22:33:AA:BB")')

        if uploader_name is None:
            uploader_name = gethostname() + u" (gmusicapi-%s)" % gmusicapi.__version__

        try:
            # this is a MM-specific step that might register a new device.
            self._make_call(musicmanager.AuthenticateUploader,
                            uploader_id,
                            uploader_name)
            self.logger.info("successful upauth")
            self.uploader_id = uploader_id
            self.uploader_name = uploader_name

        except CallFailure:
            self.logger.exception("upauth failure")
            self.session.logout()
            return False

        return True

    def logout(self, revoke_oauth=False):
        """Forgets local authentication in this Client instance.

        :param revoke_oauth: if True, oauth credentials will be permanently
          revoked. If credentials came from a file, it will be deleted.

        Returns ``True`` on success."""

        # TODO the login/logout stuff is all over the place

        success = True

        if revoke_oauth:
            try:
                # this automatically deletes a Storage file, if present
                self.session._oauth_creds.revoke(httplib2.Http())
            except TokenRevokeError:
                self.logger.exception("could not revoke oauth credentials")
                success = False

        self.uploader_id = None
        self.uploader_name = None

        return success and super(Musicmanager, self).logout()

    # mostly copy-paste from Webclient.get_all_songs.
    # not worried about overlap in this case; the logic of either could change.
    def get_uploaded_songs(self, incremental=False):
        """Returns a list of dictionaries, each with the following keys:
        ``('id', 'title', 'album', 'album_artist', 'artist', 'track_number',
        'track_size', 'disc_number', 'total_disc_count')``.

        All Access tracks that were added to the library will not be included,
        only tracks uploaded/matched by the user.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 dictionaries
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.
        """

        to_return = self._get_all_songs()

        if not incremental:
            to_return = [song for chunk in to_return for song in chunk]

        return to_return

    # mostly copy-paste from Webclient.get_all_songs.
    # not worried about overlap in this case; the logic of either could change.
    def get_purchased_songs(self, incremental=False):
        """Returns a list of dictionaries, each with the following keys:
        ``('id', 'title', 'album', 'album_artist', 'artist', 'track_number',
        'track_size', 'disc_number', 'total_disc_count')``.

        :param incremental: if True, return a generator that yields lists
          of at most 1000 dictionaries
          as they are retrieved from the server. This can be useful for
          presenting a loading bar to a user.
        """

        to_return = self._get_all_songs(export_type=2)

        if not incremental:
            to_return = [song for chunk in to_return for song in chunk]

        return to_return

    @staticmethod
    def _track_info_to_dict(track_info):
        """Given a download_pb2.DownloadTrackInfo, return a dictionary."""
        # figure it's better to hardcode keys here than use introspection
        # and risk returning a new field all of a sudden.

        return dict((field, getattr(track_info, field)) for field in
                    ('id', 'title', 'album', 'album_artist', 'artist',
                     'track_number', 'track_size', 'disc_number',
                     'total_disc_count'))

    def _get_all_songs(self, export_type=1):
        """Return a generator of song chunks."""

        get_next_chunk = True

        # need to spoof .continuation_token access, and
        # can't add attrs to object(). Can with functions.

        lib_chunk = lambda: 0  # noqa
        lib_chunk.continuation_token = None

        while get_next_chunk:
            lib_chunk = self._make_call(musicmanager.ListTracks,
                                        self.uploader_id,
                                        lib_chunk.continuation_token,
                                        export_type)

            yield [self._track_info_to_dict(info)
                   for info in lib_chunk.download_track_info]

            get_next_chunk = lib_chunk.HasField('continuation_token')

    @utils.enforce_id_param
    def download_song(self, song_id):
        """Download an uploaded or purchased song from your library.

        Subscription tracks can't be downloaded with this method.

        Returns a tuple ``(u'suggested_filename', 'audio_bytestring')``.
        The filename
        will be what the Music Manager would save the file as,
        presented as a unicode string with the proper file extension.
        You don't have to use it if you don't want.


        :param song_id: a single uploaded or purchased song id.

        To write the song to disk, use something like::

            filename, audio = mm.download_song(an_id)

            # if open() throws a UnicodeEncodeError, either use
            #   filename.encode('utf-8')
            # or change your default encoding to something sane =)
            with open(filename, 'wb') as f:
                f.write(audio)

        Unlike with :py:func:`Webclient.get_song_download_info
        <gmusicapi.clients.Webclient.get_song_download_info>`,
        there is no download limit when using this interface.

        Also unlike the Webclient, downloading a track requires authentication.
        Returning a url does not suffice, since retrieving a track without auth
        will produce an http 500.
        """

        url = self._make_call(musicmanager.GetDownloadLink,
                              song_id,
                              self.uploader_id)['url']

        response = self._make_call(musicmanager.DownloadTrack, url)

        cd_header = response.headers['content-disposition']

        filename = unquote(cd_header.split("filename*=UTF-8''")[-1])

        return (filename, response.content)

    def get_quota(self):
        """Returns a tuple of (number of uploaded tracks, allowed number of uploaded tracks)."""

        if self.uploader_id is None:
            raise NotLoggedIn("Not authenticated as an upload device;"
                              " run Musicmanager.login(...perform_upload_auth=True...)"
                              " first.")

        client_state = self._make_call(
            musicmanager.GetClientState, self.uploader_id).clientstate_response

        return (client_state.total_track_count, client_state.locker_track_limit)

    @utils.accept_singleton(basestring)
    @utils.empty_arg_shortcircuit(return_code='{}')
    def upload(self, filepaths, enable_matching=False,
               enable_transcoding=True, transcode_quality='320k'):
        """Uploads the given filepaths.

        All non-mp3 files will be transcoded before being uploaded.
        This is a limitation of Google's backend.

        An available installation of ffmpeg or avconv is required in most cases:
        see `the installation page
        <https://unofficial-google-music-api.readthedocs.io/en
        /latest/usage.html?#installation>`__ for details.

        Returns a 3-tuple ``(uploaded, matched, not_uploaded)`` of dictionaries, eg::

            (
                {'<filepath>': '<new server id>'},               # uploaded
                {'<filepath>': '<new server id>'},               # matched
                {'<filepath>': '<reason, eg ALREADY_EXISTS>'}    # not uploaded
            )

        :param filepaths: a list of filepaths, or a single filepath.

        :param enable_matching: if ``True``, attempt to use `scan and match
          <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=2920799&topic=2450455>`__
          to avoid uploading every song.
          This requires ffmpeg or avconv.
          **WARNING**: currently, mismatched songs can *not* be fixed with the 'Fix Incorrect Match'
          button nor :py:func:`report_incorrect_match
          <gmusicapi.clients.Webclient.report_incorrect_match>`.
          They would have to be deleted and reuploaded with matching disabled
          (or with the Music Manager).
          Fixing matches from gmusicapi may be supported in a future release; see issue `#89
          <https://github.com/simon-weber/gmusicapi/issues/89>`__.

        :param enable_transcoding:
          if ``False``, non-MP3 files that aren't matched using `scan and match
          <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=2920799&topic=2450455>`__
          will not be uploaded.

        :param transcode_quality: if int, pass to ffmpeg/avconv ``-q:a`` for libmp3lame
          (`lower-better int,
          <http://trac.ffmpeg.org/wiki/Encoding%20VBR%20(Variable%20Bit%20Rate)%20mp3%20audio>`__).
          If string, pass to ffmpeg/avconv ``-b:a`` (eg ``'128k'`` for an average bitrate of 128k).
          The default is 320kbps cbr (the highest possible quality).

        All Google-supported filetypes are supported; see `Google's documentation
        <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1100462>`__.

        If ``PERMANENT_ERROR`` is given as a not_uploaded reason, attempts to reupload will never
        succeed. The file will need to be changed before the server will reconsider it; the easiest
        way is to change metadata tags (it's not important that the tag be uploaded, just that the
        contents of the file change somehow).
        """

        if self.uploader_id is None or self.uploader_name is None:
            raise NotLoggedIn("Not authenticated as an upload device;"
                              " run Api.login(...perform_upload_auth=True...)"
                              " first.")

        # TODO there is way too much code in this function.

        # To return.
        uploaded = {}
        matched = {}
        not_uploaded = {}

        # Gather local information on the files.
        local_info = {}  # {clientid: (path, Track)}
        for path in filepaths:
            try:
                track = musicmanager.UploadMetadata.fill_track_info(path)
            except BaseException as e:
                self.logger.exception("problem gathering local info of '%r'", path)

                user_err_msg = str(e)

                if 'Non-ASCII strings must be converted to unicode' in str(e):
                    # This is a protobuf-specific error; they require either ascii or unicode.
                    # To keep behavior consistent, make no effort to guess - require users
                    # to decode first.
                    user_err_msg = ("nonascii bytestrings must be decoded to unicode"
                                    " (error: '%s')" % user_err_msg)

                not_uploaded[path] = user_err_msg
            else:
                local_info[track.client_id] = (path, track)

        if not local_info:
            return uploaded, matched, not_uploaded

        # TODO allow metadata faking

        # Upload metadata; the server tells us what to do next.
        res = self._make_call(musicmanager.UploadMetadata,
                              [t for (path, t) in local_info.values()],
                              self.uploader_id)

        # TODO checking for proper contents should be handled in verification
        md_res = res.metadata_response

        responses = [r for r in md_res.track_sample_response]
        sample_requests = [req for req in md_res.signed_challenge_info]

        # Send scan and match samples if requested.
        for sample_request in sample_requests:
            path, track = local_info[sample_request.challenge_info.client_track_id]

            bogus_sample = None
            if not enable_matching:
                bogus_sample = b''  # just send empty bytes

            try:
                res = self._make_call(musicmanager.ProvideSample,
                                      path, sample_request, track,
                                      self.uploader_id, bogus_sample)

            except (IOError, ValueError) as e:
                self.logger.warning("couldn't create scan and match sample for '%r': %s",
                                    path, str(e))
                not_uploaded[path] = str(e)
            else:
                responses.extend(res.sample_response.track_sample_response)

        # Read sample responses and prep upload requests.
        to_upload = {}  # {serverid: (path, Track, do_not_rematch?)}
        for sample_res in responses:
            path, track = local_info[sample_res.client_track_id]

            if sample_res.response_code == upload_pb2.TrackSampleResponse.MATCHED:
                self.logger.info("matched '%r' to sid %s", path, sample_res.server_track_id)

                matched[path] = sample_res.server_track_id

                if not enable_matching:
                    self.logger.error("'%r' was matched without matching enabled", path)

            elif sample_res.response_code == upload_pb2.TrackSampleResponse.UPLOAD_REQUESTED:
                to_upload[sample_res.server_track_id] = (path, track, False)

            else:
                # there was a problem
                # report the symbolic name of the response code enum for debugging
                enum_desc = upload_pb2._TRACKSAMPLERESPONSE.enum_types[0]
                res_name = enum_desc.values_by_number[sample_res.response_code].name

                err_msg = "TrackSampleResponse code %s: %s" % (sample_res.response_code, res_name)

                if res_name == 'ALREADY_EXISTS':
                    # include the sid, too
                    # this shouldn't be relied on externally, but I use it in
                    # tests - being surrounded by parens is how it's matched
                    err_msg += "(%s)" % sample_res.server_track_id

                self.logger.warning("upload of '%r' rejected: %s", path, err_msg)
                not_uploaded[path] = err_msg

        # Send upload requests.
        if to_upload:
            # TODO reordering requests could avoid wasting time waiting for reup sync
            self._make_call(musicmanager.UpdateUploadState, 'start', self.uploader_id)

            for server_id, (path, track, do_not_rematch) in to_upload.items():
                # It can take a few tries to get an session.
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
                        self.logger.info("got an upload session for '%r'", path)
                        break

                    should_retry, reason, error_code = error_details
                    self.logger.debug("problem getting upload session: %s\ncode=%s retrying=%s",
                                      reason, error_code, should_retry)

                    if error_code == 200 and do_not_rematch:
                        # reupload requests need to wait on a server sync
                        # 200 == already uploaded, so force a retry in this case
                        should_retry = True

                    time.sleep(6)  # wait before retrying
                else:
                    err_msg = "GetUploadSession error %s: %s" % (error_code, reason)

                    self.logger.warning("giving up on upload session for '%r': %s", path, err_msg)
                    not_uploaded[path] = err_msg

                    continue  # to next upload

                # got a session, do the upload
                # this terribly inconsistent naming isn't my fault: Google--
                session = session['sessionStatus']
                external = session['externalFieldTransfers'][0]

                session_url = external['putInfo']['url']
                content_type = external.get('content_type', 'audio/mpeg')

                if track.original_content_type != locker_pb2.Track.MP3:
                    if enable_transcoding:
                        try:
                            self.logger.info("transcoding '%r' to mp3", path)
                            contents = utils.transcode_to_mp3(path, quality=transcode_quality)
                        except (IOError, ValueError) as e:
                            self.logger.warning("error transcoding %r: %s", path, e)
                            not_uploaded[path] = "transcoding error: %s" % e
                            continue
                    else:
                        not_uploaded[path] = "transcoding disabled"
                        continue
                else:
                    with open(path, 'rb') as f:
                        contents = f.read()

                upload_response = self._make_call(musicmanager.UploadFile,
                                                  session_url, content_type, contents)

                success = upload_response.get('sessionStatus', {}).get('state')
                if success:
                    uploaded[path] = server_id
                else:
                    # 404 == already uploaded? serverside check on clientid?
                    self.logger.debug("could not finalize upload of '%r'. response: %s",
                                      path, upload_response)
                    not_uploaded[path] = 'could not finalize upload; details in log'

            self._make_call(musicmanager.UpdateUploadState, 'stopped', self.uploader_id)

        return uploaded, matched, not_uploaded
