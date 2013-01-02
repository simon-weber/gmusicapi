#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the Music Manager (related to uploading)."""

import base64
import hashlib
import os

import mutagen

from gmusicapi.exceptions import CallFailure
from gmusicapi.newprotocol import upload_pb2, locker_pb2
from gmusicapi.newprotocol.shared import Call, Transaction
from gmusicapi.utils import utils


class MmCall(Call):
    """Abstract base for Music Manager calls."""

    _base_url = 'https://android.clients.google.com/upsj/'
    #mm calls sometimes have strange names. I'll name mine semantically, using
    #this for the actual url.
    _suburl = utils.NotImplementedField

    #nearly all mm calls are POSTs
    method = 'POST'

    #protobuf calls don't send the xt token
    send_xt = False

    #implementing classes define req/res protos
    req_msg_type = utils.NotImplementedField
    #this is a shared union class that has all specific upload types
    res_msg_type = upload_pb2.UploadResponse

    @classmethod
    def build_transaction(cls, *args, **kwargs):
        #template out the transaction; most of it is shared.
        return Transaction(
            cls._request_factory({
                'url': cls._base_url + cls._suburl,
                'data': cls._build_protobuf(
                    *args, **kwargs).SerializeToString(),
                'headers': {'Content-Type': 'application/x-google-protobuf'},
            }),
            cls.verify_res_schema,
            cls.verify_res_success
        )
        pass

    @classmethod
    def verify_res_schema(cls, res):
        """Parsing also verifies the schema for protobufs."""
        #TODO could verify the response_type
        pass

    @classmethod
    def verify_res_success(cls, res):
        #TODO not sure how to do this yet.
        #auth is a factor, but both protocols share that, I think
        pass

    @classmethod
    def _build_protobuf(cls, *args, **kwargs):
        """Return a req_msg_type filled with call-specific args."""
        raise NotImplementedError

    @classmethod
    def parse_response(cls, text):
        """Parse the cls.res_msg_type proto msg."""
        res_msg = cls.res_msg_type()
        res_msg.ParseFromString(text)

        #TODO do something with ParseError

        return res_msg


class AuthenticateUploader(MmCall):
    """Sent to auth, reauth, or register our upload client."""

    _suburl = 'upauth'
    req_msg_type = upload_pb2.UpAuthRequest

    @classmethod
    def verify_res_success(cls, res):
        if res.HasField('auth_status') and res.auth_status != upload_pb2.UploadResponse.OK:
            raise CallFailure(
                "Two accounts have been registered on this machine."
                " Only 2 are allowed; deauthorize this machine to continue."
                " See http://goo.gl/O6xe7 for more information.",
                cls.__name__)

    @classmethod
    def _build_protobuf(cls, uploader_id, uploader_friendly_name):
        """
        :param uploader_id: MM uses host MAC address
        :param uploader_friendly_name: MM uses hostname
        """
        req_msg = cls.req_msg_type()

        req_msg.uploader_id = uploader_id
        req_msg.friendly_name = uploader_friendly_name

        return req_msg


class UploadMetadata(MmCall):
    _suburl = 'metadata'

    static_config = {
        'params': {'version': 1}
    }

    req_msg_type = upload_pb2.UploadMetadataRequest

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
        On problems, return None."""
        track = locker_pb2.Track()

        audio = mutagen.File(filepath)

        if audio is None:
            #TODO warn
            return None

        track.client_id = cls.get_track_clientid(file_contents)

        track.original_bit_rate = int(audio.info.bitrate / 1000)
        track.duration_millis = int(audio.info.length * 1000)

        track.estimated_size = os.path.getsize(filepath)
        track.last_modified_timestamp = os.path.getmtime(filepath)

        #These are zeroed in my examples.
        track.play_count = 0
        track.client_date_added = 0
        track.recent_timestamp = 0
        track.rating = locker_pb2.Track.NOT_RATED  # star rating

        #Title is required.
        #If it's not in the metadata, the filename will be used.
        if "title" in audio:
            track.title = audio["title"][0]
        else:
            #attempt to handle non-ascii path encodings.
            enc = utils.guess_str_encoding(filepath)[0]

            filename = os.path.split(filepath)[1]
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
    def _build_protobuf(cls, track, uploader_id):
        """Track is a filled locker_pb2.Track.
        This call supports multiple tracks, but I don't."""
        req_msg = cls.req_msg_type()

        #Python protobuf generated code is a bit wonky;
        # this is just like append.
        req_msg.track.extend([track])

        req_msg.uploader_id = uploader_id

        return req_msg
