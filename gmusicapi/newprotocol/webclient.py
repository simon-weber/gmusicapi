"""Calls made by the web client."""

import json
import sys

import validictory

from gmusicapi.exceptions import CallFailure, ValidationException
from gmusicapi.newprotocol.shared import Call
from gmusicapi.utils import utils

base_url = 'https://play.google.com/music/'
service_url = base_url + 'services/'


class WcCall(Call):
    """Abstract base for web client calls."""

    send_xt = True
    send_sso = True

    #validictory schema for the response
    _res_schema = utils.NotImplementedField

    @classmethod
    def validate(cls, res):
        """Use validictory and a static schema (stored in cls._res_schema)."""
        try:
            return validictory.validate(res, cls._res_schema)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ValidationException(str(e)), None, trace

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
    static_url = service_url + 'addplaylist'

    _res_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "success": {"type": "boolean"},
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(title):
        """
        :param title: the title of the playlist to create.
        """
        return {'json': json.dumps({"title": title})}


class AddToPlaylist(WcCall):
    """Adds songs to a playlist."""
    static_method = 'POST'
    static_url = service_url + 'addtoplaylist'

    _res_schema = {
        "type": "object",
        "properties": {
            "playlistId": {"type": "string"},
            "songIds": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "songId": {"type": "string"},
                        "playlistEntryId": {"type": "string"}
                    }
                }
            }
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(playlist_id, song_ids):
        """
        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids
        """
        #TODO unsure what type means here. Likely involves uploaded vs store/free.
        song_refs = [{'id': sid, 'type': 1} for sid in song_ids]

        return {
            'json': json.dumps(
                {"playlistId": playlist_id, "songRefs": song_refs}
            )
        }


class ChangePlaylistName(WcCall):
    """Changes the name of a playlist."""

    static_method = 'POST'
    static_url = service_url + 'modifyplaylist'

    _res_schema = {
        "type": "object",
        "properties": {},
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(playlist_id, new_name):
        return {
            'json': json.dumps(
                {"playlistId": playlist_id, "playlistName": new_name}
            )
        }


class ReportBadSongMatch(WcCall):
    """Request to signal the uploader to reupload a matched track."""

    static_method = 'POST'
    static_url = service_url + 'fixsongmatch'
    static_params = {'format': 'jsarray'}

    #This response is always the same.
    expected_response = [[0], []]

    @classmethod
    def validate(cls, res):
        if res != cls.expected_response:
            raise ValidationException("response != %r" % cls.expected_response)

    @staticmethod
    def dynamic_data(song_ids):
        return json.dumps([["", 1], [song_ids]])
