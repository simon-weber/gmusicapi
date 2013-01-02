#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the Music Manager (related to uploading)."""

from gmusicapi.exceptions import CallFailure
from gmusicapi.newprotocol import upload_pb2
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
        if res.HasField('auth_status') and \
           res.auth_status != upload_pb2.UploadResponse.OK:

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
