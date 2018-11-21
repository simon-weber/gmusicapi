# -*- coding: utf-8 -*-

"""Calls made by the Music Manager (related to uploading)."""
from __future__ import print_function, division, absolute_import, unicode_literals
from six import raise_from
from builtins import *  # noqa

import base64
import hashlib
import itertools
import os
import shutil
from tempfile import NamedTemporaryFile

import dateutil.parser
from decorator import decorator
from google.protobuf.message import DecodeError
import mutagen

import json
from gmusicapi.exceptions import CallFailure
from gmusicapi.protocol import upload_pb2, locker_pb2, download_pb2
from gmusicapi.protocol.shared import Call, ParseException, authtypes
from gmusicapi.utils import utils

log = utils.DynamicClientLogger(__name__)


_android_url = 'https://android.clients.google.com/upsj/'


@decorator
def pb(f, *args, **kwargs):
    """Decorator to serialize a protobuf message."""
    msg = f(*args, **kwargs)
    return msg.SerializeToString()


class MmCall(Call):
    """Abstract base for Music Manager calls."""

    static_method = 'POST'
    # remember that setting this in a subclass overrides, not merges
    # static + dynamic does merge, though
    static_headers = {'User-agent': 'Music Manager (1, 0, 55, 7425 HTTPS - Windows)'}

    required_auth = authtypes(oauth=True)

    # this is a shared union class that has all specific upload types
    # nearly all of the proto calls return a message of this form
    res_msg_type = upload_pb2.UploadResponse

    @classmethod
    def parse_response(cls, response):
        """Parse the cls.res_msg_type proto msg."""
        res_msg = cls.res_msg_type()
        try:
            res_msg.ParseFromString(response.content)
        except DecodeError as e:
            raise_from(ParseException(str(e)), e)

        return res_msg

    @classmethod
    def filter_response(cls, msg):
        return Call._filter_proto(msg)


class GetClientState(MmCall):
    static_url = _android_url + 'clientstate'

    @classmethod
    @pb
    def dynamic_data(cls, uploader_id):
        """
        :param uploader_id: MM uses host MAC address
        """

        req_msg = upload_pb2.ClientStateRequest()

        req_msg.uploader_id = uploader_id

        return req_msg


class AuthenticateUploader(MmCall):
    """Sent to auth, reauth, or register our upload client."""

    static_url = _android_url + 'upauth'

    @classmethod
    def check_success(cls, response, msg):
        if msg.HasField('auth_status') and msg.auth_status != upload_pb2.UploadResponse.OK:
            enum_desc = upload_pb2._UPLOADRESPONSE.enum_types[1]
            res_name = enum_desc.values_by_number[msg.auth_status].name

            raise CallFailure(
                "Upload auth error code %s: %s."
                " See http://goo.gl/O6xe7 for more information. " % (
                    msg.auth_status, res_name
                ), cls.__name__
            )

    @classmethod
    @pb
    def dynamic_data(cls, uploader_id, uploader_friendly_name):
        """
        :param uploader_id: MM uses host MAC address
        :param uploader_friendly_name: MM uses hostname
        """
        req_msg = upload_pb2.UpAuthRequest()

        req_msg.uploader_id = uploader_id
        req_msg.friendly_name = uploader_friendly_name

        return req_msg


class UploadMetadata(MmCall):
    static_url = _android_url + 'metadata'

    static_params = {'version': 1}

    @staticmethod
    def get_track_clientid(filepath):
        # The id is a 22 char hash of the file. It is found by:
        # stripping tags
        # getting an md5 sum
        # converting sum to base64
        # removing trailing ===

        m = hashlib.md5()

        try:
            ext = os.path.splitext(filepath)[1]

            # delete=False is needed because the NamedTemporaryFile
            # can't be opened by name a second time on Windows otherwise.
            with NamedTemporaryFile(suffix=ext, delete=False) as temp:
                shutil.copy(filepath, temp.name)

                audio = mutagen.File(temp.name, easy=True)
                audio.delete()
                audio.save()

                while True:
                    data = temp.read(65536)
                    if not data:
                        break
                    m.update(data)
        finally:
            try:
                os.remove(temp.name)
            except OSError:
                log.exception("Could not remove temporary file %r", temp.name)

        return base64.encodestring(m.digest())[:-3]

    # these collections define how locker_pb2.Track fields align to mutagen's.
    shared_fields = ('album', 'artist', 'composer', 'genre')
    field_map = {  # mutagen: Track
        'albumartist': 'album_artist',
        'bpm': 'beats_per_minute',
    }
    count_fields = {  # mutagen: (part, total)
        'discnumber': ('disc_number', 'total_disc_count'),
        'tracknumber': ('track_number', 'total_track_count'),
    }

    @classmethod
    def fill_track_info(cls, filepath):
        """Given the path and contents of a track, return a filled locker_pb2.Track.
        On problems, raise ValueError."""
        track = locker_pb2.Track()

        # The track protobuf message supports an additional metadata list field.
        # ALBUM_ART_HASH has been observed being sent in this field so far.
        # Append locker_pb2.AdditionalMetadata objects to additional_metadata.
        # AdditionalMetadata objects consist of two fields, 'tag_name' and 'value'.
        additional_metadata = []

        track.client_id = cls.get_track_clientid(filepath)

        audio = mutagen.File(filepath, easy=True)

        if audio is None:
            raise ValueError("could not open to read metadata")
        elif isinstance(audio, mutagen.asf.ASF):
            # WMA entries store more info than just the value.
            # Monkeypatch in a dict {key: value} to keep interface the same for all filetypes.
            asf_dict = dict((k, [ve.value for ve in v]) for (k, v) in audio.tags.as_dict().items())
            audio.tags = asf_dict

        extension = os.path.splitext(filepath)[1].upper()

        if isinstance(extension, bytes):
            extension = extension.decode('utf8')

        if extension:
            # Trim leading period if it exists (ie extension not empty).
            extension = extension[1:]

        if isinstance(audio, mutagen.mp4.MP4) and (
                audio.info.codec == 'alac' or audio.info.codec_description == 'ALAC'):
            extension = 'ALAC'
        elif isinstance(audio, mutagen.mp4.MP4) and audio.info.codec_description.startswith('AAC'):
            extension = 'AAC'

        if extension.upper() == 'M4B':
            # M4B are supported by the music manager, and transcoded like normal.
            extension = 'M4A'

        if not hasattr(locker_pb2.Track, extension):
            raise ValueError("unsupported filetype: {0} for file {1}".format(extension, filepath))

        track.original_content_type = getattr(locker_pb2.Track, extension)

        track.estimated_size = os.path.getsize(filepath)
        track.last_modified_timestamp = int(os.path.getmtime(filepath))

        # These are typically zeroed in my examples.
        track.play_count = 0
        track.client_date_added = 0
        track.recent_timestamp = 0
        track.rating = locker_pb2.Track.NOT_RATED  # star rating

        track.duration_millis = int(audio.info.length * 1000)

        try:
            bitrate = audio.info.bitrate // 1000
        except AttributeError:
            # mutagen doesn't provide bitrate for some lossless formats (eg FLAC), so
            # provide an estimation instead. This shouldn't matter too much;
            # the bitrate will always be > 320, which is the highest scan and match quality.
            bitrate = (track.estimated_size * 8) // track.duration_millis

        track.original_bit_rate = bitrate

        # Populate metadata.

        def track_set(field_name, val, msg=track):
            """Returns result of utils.pb_set and logs on failures.
            Should be used when setting directly from metadata."""
            success = utils.pb_set(msg, field_name, val)

            if not success:
                log.info("could not pb_set track.%s = %r for '%r'", field_name, val, filepath)

            return success

        # Title is required.
        # If it's not in the metadata, the filename will be used.
        if "title" in audio:
            title = audio['title'][0]
            if isinstance(title, mutagen.asf.ASFUnicodeAttribute):
                title = title.value

            track_set('title', title)
        else:
            # Assume ascii or unicode.
            track.title = os.path.basename(filepath)

        if "date" in audio:
            date_val = str(audio['date'][0])
            try:
                datetime = dateutil.parser.parse(date_val, fuzzy=True)
            except (ValueError, TypeError) as e:
                # TypeError provides compatibility with:
                #  https://bugs.launchpad.net/dateutil/+bug/1247643
                log.warning("could not parse date md for '%r': (%s)", filepath, e)
            else:
                track_set('year', datetime.year)

        for null_field in ['artist', 'album']:
            # If these fields aren't provided, they'll render as "undefined" in the web interface;
            # see https://github.com/simon-weber/gmusicapi/issues/236.
            # Defaulting them to an empty string fixes this.
            if null_field not in audio:
                track_set(null_field, '')

        # Mass-populate the rest of the simple fields.
        # Merge shared and unshared fields into {mutagen: Track}.
        fields = dict(
            itertools.chain(
                ((shared, shared) for shared in cls.shared_fields),
                cls.field_map.items()))

        for mutagen_f, track_f in fields.items():
            if mutagen_f in audio:
                track_set(track_f, audio[mutagen_f][0])

        for mutagen_f, (track_f, track_total_f) in cls.count_fields.items():
            if mutagen_f in audio:
                numstrs = str(audio[mutagen_f][0]).split("/")
                track_set(track_f, numstrs[0])

                if len(numstrs) == 2 and numstrs[1]:
                    track_set(track_total_f, numstrs[1])

        if additional_metadata:
            track.track_extras.additional_metadata.extend(additional_metadata)

        return track

    @classmethod
    @pb
    def dynamic_data(cls, tracks, uploader_id, do_not_rematch=False):
        """
        :param tracks: list of filled locker_pb2.Track
        :param uploader_id:
        :param do_not_rematch: seems to be ignored
        """

        req_msg = upload_pb2.UploadMetadataRequest()

        req_msg.track.extend(tracks)

        for track in req_msg.track:
            track.do_not_rematch = do_not_rematch

        req_msg.uploader_id = uploader_id

        return req_msg


class GetUploadJobs(MmCall):
    # TODO
    static_url = _android_url + 'getjobs'

    static_params = {'version': 1}

    @classmethod
    def check_success(cls, response, msg):
        if msg.HasField('getjobs_response') and not msg.getjobs_response.get_tracks_success:
            raise CallFailure('get_tracks_success == False', cls.__name__)

    @classmethod
    @pb
    def dynamic_data(cls, uploader_id):
        """
        :param uploader_id: MM uses host MAC address
        """
        req_msg = upload_pb2.GetJobsRequest()

        req_msg.uploader_id = uploader_id

        return req_msg


class GetUploadSession(MmCall):
    """Called when we want to upload; the server returns the url to use.
    This is a json call, and doesn't share much with the other calls."""

    static_method = 'POST'
    static_url = 'https://uploadsj.clients.google.com/uploadsj/scottyagent'

    @classmethod
    def parse_response(cls, response):
        return cls._parse_json(response.text)

    @staticmethod
    def filter_response(res):
        return res

    @staticmethod
    def dynamic_data(uploader_id, num_already_uploaded,
                     track, filepath, server_id, do_not_rematch=False):
        """track is a locker_pb2.Track, and the server_id is from a metadata upload."""
        # small info goes inline, big things get their own external PUT.
        # still not sure as to thresholds - I've seen big album art go inline.

        if isinstance(filepath, bytes):
            filepath = filepath.decode('utf8')

        inlined = {
            "title": "jumper-uploader-title-42",
            "ClientId": track.client_id,
            "ClientTotalSongCount": "1",  # TODO think this is ie "how many will you upload"
            "CurrentTotalUploadedCount": str(num_already_uploaded),
            "CurrentUploadingTrack": track.title,
            "ServerId": server_id,
            "SyncNow": "true",
            "TrackBitRate": track.original_bit_rate,
            "TrackDoNotRematch": str(do_not_rematch).lower(),
            "UploaderId": uploader_id,
        }

        message = {
            "clientId": "Jumper Uploader",
            "createSessionRequest": {
                "fields": [
                    {
                        "external": {
                            "filename": os.path.basename(filepath),
                            "name": os.path.abspath(filepath),
                            "put": {},
                            # used to use this; don't see it in examples
                            # "size": track.estimated_size,
                        }
                    }
                ]
            },
            "protocolVersion": "0.8"
        }

        # Insert the inline info.
        for key in inlined:
            payload = inlined[key]
            if not isinstance(payload, str):
                payload = str(payload)

            message['createSessionRequest']['fields'].append(
                {
                    "inlined": {
                        "content": payload,
                        "name": key
                    }
                }
            )

        return json.dumps(message)

    @staticmethod
    def process_session(res):
        """Return (got_session, error_details).
        error_details is (should_retry, reason, error_code) or None if got_session."""

        if 'sessionStatus' in res:
            return (True, None)

        if 'errorMessage' in res:
            try:
                # This terribly nested structure is Google's doing.
                error_code = (res['errorMessage']['additionalInfo']
                              ['uploader_service.GoogleRupioAdditionalInfo']['completionInfo']
                              ['customerSpecificInfo']['ResponseCode'])
            except KeyError:
                # The returned nested structure is not as expected: cannot get Response Code
                error_code = None

            got_session = False

            if error_code == 503:
                should_retry = True
                reason = 'upload servers still syncing'

            # TODO unsure about these codes
            elif error_code == 200:
                should_retry = False
                reason = 'this song is already uploaded'

            elif error_code == 404:
                should_retry = False
                reason = 'the request was rejected'

            else:
                should_retry = True
                reason = 'the server reported an unknown error'

            return (got_session, (should_retry, reason, error_code))

        return (False, (True, "the server's response could not be understood", None))


class UploadFile(MmCall):
    """Called after getting a session to actually upload a file."""
    # TODO recent protocols use multipart encoding

    static_method = 'PUT'

    @classmethod
    def parse_response(cls, response):
        return cls._parse_json(response.text)

    @staticmethod
    def filter_response(res):
        return res

    @staticmethod
    def dynamic_headers(session_url, content_type, audio):
        return {'CONTENT-TYPE': content_type}

    @staticmethod
    def dynamic_url(session_url, content_type, audio):
        # this actually includes params, but easier to pass them straight through
        return session_url

    @staticmethod
    def dynamic_data(session_url, content_type, audio):
        return audio


class ProvideSample(MmCall):
    """Give the server a scan and match sample.
    The sample is a 128k mp3 slice of the file, usually 15 seconds long."""

    static_method = 'POST'
    static_params = {'version': 1}
    static_url = _android_url + 'sample'

    @staticmethod
    @pb
    def dynamic_data(filepath, server_challenge, track, uploader_id, mock_sample=None):
        """Raise IOError on transcoding problems, or ValueError for invalid input.

        :param mock_sample: if provided, will be sent in place of a proper sample

        """
        msg = upload_pb2.UploadSampleRequest()

        msg.uploader_id = uploader_id

        sample_msg = upload_pb2.TrackSample()
        sample_msg.track.CopyFrom(track)
        sample_msg.signed_challenge_info.CopyFrom(server_challenge)

        sample_spec = server_challenge.challenge_info  # convenience

        if mock_sample is None:
            # The sample is simply a small (usually 15 second) clip of the song,
            # transcoded into 128kbs mp3. The server dictates where the cut should be made.
            sample_msg.sample = utils.transcode_to_mp3(
                filepath, quality='128k',
                slice_start=sample_spec.start_millis // 1000,
                slice_duration=sample_spec.duration_millis // 1000
            )
        else:
            sample_msg.sample = mock_sample

        # You can provide multiple samples; I just provide one at a time.
        msg.track_sample.extend([sample_msg])

        return msg


class UpdateUploadState(MmCall):
    """Notify the server that we will be starting/stopping/pausing our upload.

    I believe this is used for the webclient 'currently uploading' widget, but that might also be
    the current_uploading information.
    """

    static_method = 'POST'
    static_params = {'version': 1}
    static_url = _android_url + 'uploadstate'

    @staticmethod
    @pb
    def dynamic_data(to_state, uploader_id):
        """Raise ValueError on problems.

        :param to_state: one of 'start', 'paused', or 'stopped'
        """

        msg = upload_pb2.UpdateUploadStateRequest()
        msg.uploader_id = uploader_id

        try:
            state = getattr(upload_pb2.UpdateUploadStateRequest, to_state.upper())
        except AttributeError as e:
            raise ValueError(str(e))

        msg.state = state

        return msg


class CancelUploadJobs(MmCall):
    """This call will cancel any outstanding upload jobs (ie from GetJobs).
    The Music Manager only calls it when the user changes the location of their local collection.

    It doesn't actually return anything useful."""

    static_method = 'POST'
    static_url = _android_url + 'deleteuploadrequested'

    @staticmethod
    @pb
    def dynamic_data(uploader_id):
        """
        :param uploader_id: id
        """

        msg = upload_pb2.DeleteUploadRequestedRequest()  # what a mouthful!
        msg.uploader_id = uploader_id

        return msg


class ListTracks(MmCall):
    """List all tracks. Returns a subset of all available metadata.
    Can optionally filter for only free/purchased tracks."""

    res_msg_type = download_pb2.GetTracksToExportResponse

    static_method = 'POST'
    static_url = 'https://music.google.com/music/exportids'

    # example response:
    # download_track_info {
    #   id: "970d9e51-b392-3857-897a-170e456cba60"
    #   title: "Temporary Trip"
    #   album: "Pay Attention"
    #   album_artist: "The Mighty Mighty Bosstones"
    #   artist: "The Mighty Mighty Bosstones"
    #   track_number: 14
    #   track_size: 3577382
    # }

    @staticmethod
    def dynamic_headers(client_id, *args, **kwargs):
        return {'X-Device-ID': client_id}

    @staticmethod
    @pb
    def dynamic_data(client_id, cont_token=None, export_type=1, updated_min=0):
        """Works similarly to the webclient method.
        Chunks are up to 1000 tracks.


        :param client_id: an authorized uploader_id
        :param cont_token: (optional) token to get the next library chunk.
        :param export_type: 1='ALL', 2='PURCHASED_AND_PROMOTIONAL'
        :param updated_min: likely a timestamp; never seen an example of this != 0
        """

        msg = download_pb2.GetTracksToExportRequest()
        msg.client_id = client_id
        msg.export_type = export_type

        if cont_token is not None:
            msg.continuation_token = cont_token

        msg.updated_min = updated_min

        return msg

    @classmethod
    def check_success(cls, response, msg):
        if msg.status != download_pb2.GetTracksToExportResponse.OK:
            enum_desc = download_pb2._GETTRACKSTOEXPORTRESPONSE.enum_types[0]
            res_name = enum_desc.values_by_number[msg.status].name

            raise CallFailure(
                "Track export (list) error code %s: %s." % (
                    msg.status, res_name
                ), cls.__name__
            )

    # TODO
    @staticmethod
    def filter_response(msg):
        """Only log a summary."""

        cont_token = None
        if msg.HasField('continuation_token'):
            cont_token = msg.continuation_token

        updated_min = None
        if msg.HasField('updated_min'):
            updated_min = msg.updated_min

        return "<%s songs>, updated_min: %r, continuation_token: %r" % (
            len(msg.download_track_info),
            updated_min,
            cont_token)


class GetDownloadLink(MmCall):
    """Get a url where a track can be downloaded.

    Auth is not needed to retrieve the resulting url."""

    static_method = 'GET'
    static_headers = {}
    static_params = {'version': 2}
    static_url = 'https://music.google.com/music/export'

    @staticmethod
    def dynamic_headers(sid, client_id):
        return {'X-Device-ID': client_id}

    @staticmethod
    def dynamic_params(sid, client_id):
        return {'songid': sid}

    @classmethod
    def parse_response(cls, response):
        return cls._parse_json(response.text)

    @staticmethod
    def filter_response(res):
        return res


class DownloadTrack(MmCall):
    """Given a url, retrieve a track. Unlike the Webclient, this
    requires authentication.

    The entire Requests.Response is returned."""

    static_method = 'GET'

    @staticmethod
    def dynamic_url(url):
        """
        :param url: result of a call to GetDownloadLink
        """
        return url

    @classmethod
    def parse_response(cls, response):
        return response

    @staticmethod
    def filter_response(res):
        return "code: %s; size: %s bytes; disposition: %r" % (
            res.status_code,
            res.headers['Content-Length'],
            res.headers['Content-Disposition'])
