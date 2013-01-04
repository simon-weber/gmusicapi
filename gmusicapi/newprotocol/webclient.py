"""Calls made by the web client."""

import json
import sys
from urllib import quote_plus

import validictory

from gmusicapi.exceptions import CallFailure, ValidationException
from gmusicapi.newprotocol.shared import Call, Transaction
from gmusicapi.utils import utils


class WcCall(Call):
    """Abstract base for web client calls."""

    _base_url = 'https://play.google.com/music/'

    #Added to the url after _base_url.
    #Expected to end with a forward slash.
    _suburl = 'services/'

    #validictory schema for the response
    res_schema = utils.NotImplementedField

    @classmethod
    def build_transaction(cls, *args, **kwargs):
        #template out the transaction; most of it is shared.
        return Transaction(
            cls._request_factory({
                'url': cls._base_url + cls._suburl + cls.__name__.lower(),
                'data': 'json=' + quote_plus(
                    json.dumps(cls._build_json(*args, **kwargs)))
            }),
            cls.verify_res_schema,
            cls.verify_res_success
        )

    @classmethod
    def verify_res_schema(cls, res):
        """Use validictory and a static schema (stored in cls.res_schema)."""
        try:
            return validictory.validate(res, cls.res_schema)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ValidationException(e.message), None, trace

    @classmethod
    def verify_res_success(cls, res):
        #Failed responses always have a success=False key.
        #Some successful responses do not have a success=True key, however.
        #TODO remove utils.call_succeeded

        if 'success' in res.keys() and not res['success']:
            raise CallFailure(
                    "the server reported failure. This is usually"
                    "caused by bad arguments, but can also happen if requests"
                    "are made too quickly (eg creating a playlist then"
                    "modifying it before the server has created it)",
                    cls.__name__)

    @classmethod
    def parse_response(cls, text):
        return cls.parse_json(text)

    @staticmethod
    def _build_json(title):
        """Return a Python representation of the call's json."""
        raise NotImplementedError


class AddPlaylist(WcCall):
    """Creates a new playlist."""

    method = 'POST'

    res_schema = {"type": "object",
                  "properties": {
                      "id": {"type": "string"},
                      "title": {"type": "string"},
                      "success": {"type": "boolean"},
                  },
                  "additionalProperties": False}

    @staticmethod
    def _build_json(title):
        """
        :param title: the title of the playlist to create.
        """
        return {"title": title}


class ReportBadSongMatch(WcCall):
    """Request to signal the uploader to reupload a matched track."""

    method = 'POST'

    #eg response: [ [0], [] ]
    res_schema = {
        'type': 'array',
        'items': {
            'type': 'array'
        }
    }

    @classmethod
    def build_transaction(cls, song_id):
        #This is a weird one.
        return Transaction(
            cls._request_factory({
                'url': cls._base_url + cls._suburl + 'fixsongmatch',
                #Here, the body is just raw json
                'data': json.dumps([["", 1], [[song_id]]]),
                'params': {'format': 'jsarray'},  # not sure if other formats exist
            }),
            cls.verify_res_schema,
            cls.verify_res_success
        )
