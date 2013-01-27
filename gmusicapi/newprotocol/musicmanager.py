#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the Music Manager (related to uploading)."""

import base64
import hashlib
import json
import os
import subprocess

from decorator import decorator
import mutagen

from gmusicapi.exceptions import CallFailure
from gmusicapi.newprotocol import upload_pb2, locker_pb2
from gmusicapi.newprotocol.shared import Call
from gmusicapi.utils import utils


@decorator
def pb(f, *args, **kwargs):
    """Decorator to serialize a protobuf message."""
    msg = f(*args, **kwargs)
    return msg.SerializeToString()


class MmCall(Call):
    """Abstract base for Music Manager calls."""

    _base_url = 'https://android.clients.google.com/upsj/'

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

    static_url = MmCall._base_url + 'upauth'

    @classmethod
    def check_success(cls, res):
        if res.HasField('auth_status') and res.auth_status != upload_pb2.UploadResponse.OK:
            raise CallFailure(
                "Two accounts have been registered for this uploader_id/machine."
                " Only 2 are allowed; deauthorize this uploader_id/machine to continue."
                " See http://goo.gl/O6xe7 for more information.",
                cls.__name__)

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
    static_url = MmCall._base_url + 'metadata'

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
            asf_dict = {k: [ve.value for ve in v] for (k, v) in audio.tags.as_dict().items()}
            audio.tags = asf_dict

        print filepath
        print audio.__class__

        track.duration_millis = int(audio.info.length * 1000)

        try:
            print 'info bitrate: ', audio.info.bitrate
            bitrate = int(audio.info.bitrate / 1000)
        except AttributeError:
            #mutagen doesn't provide bitrate for FLAC and OGGFLAC.
            #Provide an estimation instead. This shouldn't matter too much;
            # the bitrate will always be > 320, which is the highest scan and match quality.
            bitrate = (track.estimated_size * 8) / track.duration_millis
            print 'estimating bitrate!', bitrate

        track.original_bit_rate = bitrate

        #Populate metadata.

        #Title is required.
        #If it's not in the metadata, the filename will be used.
        if "title" in audio:
            title = audio['title'][0]
            if isinstance(title, mutagen.asf.ASFUnicodeAttribute):
                title = title.value

            track.title = title
        else:
            #attempt to handle non-ascii path encodings.
            enc = utils.guess_str_encoding(filepath)[0]

            filename = os.path.basename(filepath)
            track.title = filename.decode(enc)

        if "date" in audio:
            #assumption; should check examples
            track.year = int(audio["date"][0].split("-")[0])

        #Mass-populate the rest of the simple fields.
        #Merge shared and unshared fields into {mutagen: Track}.
        fields = dict(
            {shared: shared for shared in cls.shared_fields}.items() +
            cls.field_map.items()
        )

        for mutagen_f, track_f in fields.items():
            if mutagen_f in audio:
                setattr(track, track_f, audio[mutagen_f][0])

        for mutagen_f, (track_f, track_total_f) in cls.count_fields.items():
            if mutagen_f in audio:
                numstrs = audio[mutagen_f][0].split("/")
                setattr(track, track_f, int(numstrs[0]))

                if len(numstrs) == 2 and numstrs[1]:
                    setattr(track, track_total_f, int(numstrs[1]))

        return track

    @classmethod
    @pb
    def dynamic_data(cls, tracks, uploader_id):
        """Track is a list of filled locker_pb2.Track."""
        req_msg = upload_pb2.UploadMetadataRequest()

        req_msg.track.extend(tracks)
        req_msg.uploader_id = uploader_id

        return req_msg


class GetUploadJobs(MmCall):
    #TODO
    static_url = MmCall._base_url + 'getjobs'

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
                     track, filepath, server_id):
        """track is a locker_pb2.Track, and the server_id is from a metadata upload."""
        #small info goes inline, big things get their own external PUT.
        #still not sure as to thresholds - I've seen big album art go inline.
        inlined = {
            "title": "jumper-uploader-title-42",
            "ClientId": track.client_id,
            "ClientTotalSongCount": "1",  # this supports more than 1 concurrent request
            "CurrentTotalUploadedCount": str(num_already_uploaded),
            "CurrentUploadingTrack": track.title,
            "ServerId": server_id,
            "SyncNow": "true",
            "TrackBitRate": track.original_bit_rate,
            "TrackDoNotRematch": "false",
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
            message['createSessionRequest']['fields'].append(
                {
                    "inlined": {
                        "content": str(inlined[key]),
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
    """Give the server a scan and match sample."""

    static_method = 'POST'
    static_params = {'version': 1}
    static_url = 'https://android.clients.google.com/upsj/sample'

    @staticmethod
    @pb
    def dynamic_data(file_contents, server_challenge, track, uploader_id):
        """Raise ValueError on problems."""
        msg = upload_pb2.UploadSampleRequest()

        msg.uploader_id = uploader_id

        sample_msg = upload_pb2.TrackSample()
        sample_msg.track.CopyFrom(track)
        sample_msg.signed_challenge_info.CopyFrom(server_challenge)

        #The sample is simply a small (usually 15 second) clip of the song,
        # transcoded into 128kbs mp3. The server dictates where the cut should be made.
        try:
            err_output = None
            sample_spec = server_challenge.challenge_info  # convenience

            #avconv with input on stdin, output to stdout
            p = subprocess.Popen(
                ['avconv',
                 '-i', 'pipe:0',
                 '-t', str(sample_spec.duration_millis / 1000),
                 '-ss', str(sample_spec.start_millis / 1000),
                 '-ab', '128k',
                 #don't output id3 headers
                 '-f', 's16be',
                 '-c', 'libmp3lame',
                 'pipe:1'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
            )

            sample, err_output = p.communicate(input=file_contents)

            if p.returncode != 0:
                raise OSError  # handle errors in except

        except OSError:
            err_msg = 'could not create a scan and match sample with avconv. '

            if err_output is not None:
                err_msg += 'Is it installed?'
            else:
                err_msg += "output: '%s'" % err_output

            raise ValueError(err_msg)

        else:
            sample_msg.sample = sample

        #You can provide multiple samples; I just provide one.
        msg.track_sample.extend([sample_msg])

        #debug
        print MmCall.filter_response(msg)
        print

        return msg
