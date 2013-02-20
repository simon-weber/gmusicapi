#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the Music Manager (related to uploading)."""

import base64
import hashlib
import logging
import os

import dateutil.parser
from decorator import decorator
import mutagen

from gmusicapi.compat import json
from gmusicapi.exceptions import CallFailure
from gmusicapi.protocol import upload_pb2, locker_pb2
from gmusicapi.protocol.shared import Call
from gmusicapi.utils import utils

log = logging.getLogger(__name__)


#This url has SSL issues, hence the verify=False for session_options.
_android_url = 'https://android.clients.google.com/upsj/'


@decorator
def pb(f, *args, **kwargs):
    """Decorator to serialize a protobuf message."""
    msg = f(*args, **kwargs)
    return msg.SerializeToString()


class MmCall(Call):
    """Abstract base for Music Manager calls."""

    static_method = 'POST'
    static_headers = {'USER-AGENT': 'Music Manager (1, 0, 54, 4672 HTTPS - Windows)'}

    #'headers': {'Content-Type': 'application/x-google-protobuf'},

    send_clientlogin = True

    #this is a shared union class that has all specific upload types
    res_msg_type = upload_pb2.UploadResponse

    @classmethod
    def parse_response(cls, response):
        """Parse the cls.res_msg_type proto msg."""
        res_msg = cls.res_msg_type()
        res_msg.ParseFromString(response.content)

        #TODO do something with ParseError

        return res_msg

    @classmethod
    def filter_response(cls, msg):
        return Call._filter_proto(msg)


class AuthenticateUploader(MmCall):
    """Sent to auth, reauth, or register our upload client."""

    static_url = _android_url + 'upauth'
    session_options = {'verify': False}  # the android url has SSL troubles

    @classmethod
    def check_success(cls, res):
        if res.HasField('auth_status') and res.auth_status != upload_pb2.UploadResponse.OK:
            enum_desc = upload_pb2._UPLOADRESPONSE.enum_types[1]
            res_name = enum_desc.values_by_number[res.auth_status].name

            raise CallFailure(
                "Upload auth error code %s: %s."
                " See http://goo.gl/O6xe7 for more information. " % (
                    res.auth_status, res_name
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
    session_options = {'verify': False}

    static_params = {'version': 1}

    @staticmethod
    def get_track_clientid(file_contents):
        #The id is a 22 char hash of the file. It is found by:
        # stripping tags
        # getting an md5 sum
        # converting sum to base64
        # removing trailing ===

        #My implementation is _not_ the same hash the music manager will send;
        # they strip tags first. But files are differentiated across accounts,
        # so this shouldn't cause problems.

        #This will attempt to reupload files if their tags change.
        cid = hashlib.md5(file_contents).digest()
        cid = base64.encodestring(cid)[:-3]
        return cid

    #these collections define how locker_pb2.Track fields align to mutagen's.
    shared_fields = ('album', 'artist', 'composer', 'genre')
    field_map = {  # mutagen: Track
        #albumartist is 'performer' according to:
        # http://goo.gl/5i18X
        'performer': 'album_artist',
        'bpm': 'beats_per_minute',
    }
    count_fields = {  # mutagen: (part, total)
        'discnumber': ('disc_number', 'total_disc_count'),
        'tracknumber': ('track_number', 'total_track_count'),
    }

    @classmethod
    def fill_track_info(cls, filepath, file_contents):
        """Given the path and contents of a track, return a filled locker_pb2.Track.
        On problems, raise ValueError."""
        track = locker_pb2.Track()

        track.client_id = cls.get_track_clientid(file_contents)

        extension = os.path.splitext(filepath)[1].upper()
        if extension:
            #Trim leading period if it exists (ie extension not empty).
            extension = extension[1:]

        if not hasattr(locker_pb2.Track, extension):
            raise ValueError("unsupported filetype")

        track.original_content_type = getattr(locker_pb2.Track, extension)

        track.estimated_size = os.path.getsize(filepath)
        track.last_modified_timestamp = int(os.path.getmtime(filepath))

        #These are typically zeroed in my examples.
        track.play_count = 0
        track.client_date_added = 0
        track.recent_timestamp = 0
        track.rating = locker_pb2.Track.NOT_RATED  # star rating

        #Populate information about the encoding.
        audio = mutagen.File(filepath, easy=True)
        if audio is None:
            raise ValueError("could not open to read metadata")
        elif isinstance(audio, mutagen.asf.ASF):
            #WMA entries store more info than just the value.
            #Monkeypatch in a dict {key: value} to keep interface the same for all filetypes.
            asf_dict = dict((k, [ve.value for ve in v]) for (k, v) in audio.tags.as_dict().items())
            audio.tags = asf_dict

        track.duration_millis = int(audio.info.length * 1000)

        try:
            bitrate = int(audio.info.bitrate / 1000)
        except AttributeError:
            #mutagen doesn't provide bitrate for some lossless formats (eg FLAC), so
            # provide an estimation instead. This shouldn't matter too much;
            # the bitrate will always be > 320, which is the highest scan and match quality.
            bitrate = (track.estimated_size * 8) / track.duration_millis

        track.original_bit_rate = bitrate

        #Populate metadata.

        def track_set(field_name, val, msg=track):
            """Returns result of utils.pb_set and logs on failures.
            Should be used when setting directly from metadata."""
            success = utils.pb_set(msg, field_name, val)

            if not success:
                log.info("could not pb_set track.%s = %r for '%s'", field_name, val, filepath)

            return success

        #Title is required.
        #If it's not in the metadata, the filename will be used.
        if "title" in audio:
            title = audio['title'][0]
            if isinstance(title, mutagen.asf.ASFUnicodeAttribute):
                title = title.value

            track_set('title', title)
        else:
            #Assume ascii or unicode.
            track.title = os.path.basename(filepath)

        if "date" in audio:
            date_val = str(audio['date'][0])
            datetime = dateutil.parser.parse(date_val, fuzzy=True)

            track_set('year', datetime.year)

        #Mass-populate the rest of the simple fields.
        #Merge shared and unshared fields into {mutagen: Track}.
        fields = dict(
            dict((shared, shared) for shared in cls.shared_fields).items() +
            cls.field_map.items()
        )

        for mutagen_f, track_f in fields.items():
            if mutagen_f in audio:
                track_set(track_f, audio[mutagen_f][0])

        for mutagen_f, (track_f, track_total_f) in cls.count_fields.items():
            if mutagen_f in audio:
                numstrs = str(audio[mutagen_f][0]).split("/")
                track_set(track_f, numstrs[0])

                if len(numstrs) == 2 and numstrs[1]:
                    track_set(track_total_f, numstrs[1])

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
    #TODO
    static_url = _android_url + 'getjobs'
    session_options = {'verify': False}

    static_params = {'version': 1}

    @classmethod
    def check_success(cls, res):
        if res.HasField('getjobs_response') and not res.getjobs_response.get_tracks_success:
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
    static_url = 'http://uploadsj.clients.google.com/uploadsj/rupio'

    #not yet able to intercept newer call, so we use an older version
    static_headers = {'USER-AGENT': 'Music Manager (1, 0, 24, 7712 - Windows)'}

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
        #small info goes inline, big things get their own external PUT.
        #still not sure as to thresholds - I've seen big album art go inline.
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
                            #used to use this; don't see it in examples
                            #"size": track.estimated_size,
                        }
                    }
                ]
            },
            "protocolVersion": "0.8"
        }

        #Insert the inline info.
        for key in inlined:
            payload = inlined[key]
            if not isinstance(payload, basestring):
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
            #This terribly nested structure is Google's doing.
            error_code = (res['errorMessage']['additionalInfo']
                          ['uploader_service.GoogleRupioAdditionalInfo']
                          ['completionInfo']['customerSpecificInfo']['ResponseCode'])

            got_session = False

            if error_code == 503:
                #Servers still syncing; retry with no penalty.
                should_retry = True
                reason = 'upload servers still syncing'

            #TODO unsure about these codes
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
    #TODO recent protocols use multipart encoding

    static_method = 'PUT'
    static_headers = {'USER-AGENT': 'Music Manager (1, 0, 24, 7712 - Windows)'}

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
        #this actually includes params, but easier to pass them straight through
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
    session_options = {'verify': False}

    @staticmethod
    @pb
    def dynamic_data(file_contents, server_challenge, track, uploader_id):
        """Raise OSError on transcoding problems, or ValueError for invalid input."""
        msg = upload_pb2.UploadSampleRequest()

        msg.uploader_id = uploader_id

        sample_msg = upload_pb2.TrackSample()
        sample_msg.track.CopyFrom(track)
        sample_msg.signed_challenge_info.CopyFrom(server_challenge)

        sample_spec = server_challenge.challenge_info  # convenience

        #The sample is simply a small (usually 15 second) clip of the song,
        # transcoded into 128kbs mp3. The server dictates where the cut should be made.
        sample_msg.sample = utils.transcode_to_mp3(
            file_contents, quality='128k',
            slice_start=sample_spec.start_millis / 1000,
            slice_duration=sample_spec.duration_millis / 1000
        )

        #You can provide multiple samples; I just provide one at a time.
        msg.track_sample.extend([sample_msg])

        return msg


class UpdateUploadState(MmCall):
    """Notify the server that we will be starting/stopping/pausing our upload.

    I believe this is used for the webclient 'currently uploading' widget, but that might also be
    the current_uploading information.
    """

    static_method = 'POST'
    static_params = {'version': 1}
    static_url = _android_url + 'sample'
    session_options = {'verify': False}

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
