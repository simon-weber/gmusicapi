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
                " Only 2 are allowed; deauthorize accounts to continue."
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
    mutagen_to_track = {
        'performer': 'album_artist',
        'bpm': 'beats_per_minute',
    }

    @classmethod
    def fill_track_info(cls, filepath):
        """Given a filepath to a track, return a filled locker_pb2.Track.
        On problems, return None."""
        track = locker_pb2.Track()

        audio = mutagen.File(filepath)

        if audio is None:
            #TODO warn
            return None

        track.original_bit_rate = audio.info.bitrate / 1000
        track.duration_millis = int(audio.info.length * 1000)

        #Title is required.
        #If it's not in the metadata, the filename will be used.
        if "title" in audio:
            track.title = audio["title"][0]
        else:
            #attempt to handle non-ascii path encodings.
            enc = utils.guess_str_encoding(filepath)[0]

            filename = os.path.split(filepath)[1]
            track.title = filename.decode(enc)

        #Merge shared and unshared fields into {mutagen: Track}.
        fields = dict(
            {shared: shared for shared in cls.shared_fields}.items() +
            cls.mutagen_to_track.items()
        )

        #for mutagen_f, track_f in fields



        #    #albumartist is 'performer' according to this guy: 
        #    # https://github.com/plexinc-plugins/Scanners.bundle/commit/95cc0b9eeb7fa8fa77c36ffcf0ec51644a927700

        #    if "performer" in audio: track.albumArtist = audio["performer"][0]
        #    if "genre" in audio: track.genre = audio["genre"][0]
        #    if "date" in audio: track.year = int(audio["date"][0].split("-")[0]) #this looks like an assumption
        #    if "bpm" in audio: track.beatsPerMinute = int(audio["bpm"][0])

        #    #think these are assumptions:
        #    if "tracknumber" in audio: 
        #        tracknumber = audio["tracknumber"][0].split("/")
        #        track.track = int(tracknumber[0])
        #        if len(tracknumber) == 2 and tracknumber[1]:
        #            track.totalTracks = int(tracknumber[1])

        #    if "discnumber" in audio:
        #        discnumber = audio["discnumber"][0].split("/")
        #        track.disc = int(discnumber[0])
        #        if len(discnumber) == 2 and discnumber[1]:
        #            track.totalDiscs = int(discnumber[1])

        return (metadata, filemap)

    @classmethod
    def _build_protobuf(cls, track, uploader_id):
        """Track is a dictionary with a subset of locker_pb2.Track fields.
        This call supports multiple tracks, but I don't."""
        req_msg = cls.req_msg_type()

        msg_track = req_msg.track.add()
        for k, v in track.iteritems():
            setattr(msg_track, k, v)

        req_msg.uploader_id = uploader_id

        return req_msg
