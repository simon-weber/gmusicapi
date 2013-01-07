"""Calls made by the web client."""

import json
import sys

import validictory

from gmusicapi.exceptions import CallFailure, ValidationException
from gmusicapi.newprotocol.shared import Call
from gmusicapi.utils import utils


class WcCall(Call):
    """Abstract base for web client calls."""

    _base_url = 'https://play.google.com/music/'
    _suburl = 'services/'

    send_xt = True
    send_sso = True

    #validictory schema for the response
    _res_schema = utils.NotImplementedField

    @classmethod
    def validate(cls, res):
        """Use validictory and a static schema (stored in cls.res_schema)."""
        try:
            return validictory.validate(res, cls._res_schema)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ValidationException(e.message), None, trace

    @classmethod
    def check_success(cls, res):
        #Failed responses always have a success=False key.
        #Some successful responses do not have a success=True key, however.
        #TODO remove utils.call_succeeded

        if 'success' in res and not res['success']:
            raise CallFailure(
                "the server reported failure. This is usually"
                "caused by bad arguments, but can also happen if requests"
                "are made too quickly (eg creating a playlist then"
                "modifying it before the server has created it)",
                cls.__name__)

    @classmethod
    def parse_response(cls, text):
        return cls._parse_json(text)


class AddPlaylist(WcCall):
    """Creates a new playlist."""

    static_method = 'POST'
    static_url = WcCall._base_url + WcCall._suburl + 'addplaylist'

    _res_schema = {"type": "object",
                   "properties": {
                       "id": {"type": "string"},
                       "title": {"type": "string"},
                       "success": {"type": "boolean"},
                   },
                   "additionalProperties": False}

    @staticmethod
    def dynamic_data(title):
        """
        :param title: the title of the playlist to create.
        """
        return {'json': json.dumps({"title": title})}


class ReportBadSongMatch(WcCall):
    """Request to signal the uploader to reupload a matched track."""

    static_method = 'POST'
    static_url = WcCall._base_url + WcCall._suburl + 'fixsongmatch'
    static_params = {'format': 'jsarray'}

    #eg response: [ [0], [] ]
    res_schema = {
        'type': 'array',
        'items': {
            'type': 'array'
        }
    }

    @classmethod
    def dynamic_data(song_id):
        return json.dumps([["", 1], [[song_id]]])
