#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the web client."""

import copy
import sys

import validictory

from gmusicapi.compat import json
from gmusicapi.exceptions import CallFailure, ValidationException
from gmusicapi.protocol.metadata import md_expectations
from gmusicapi.protocol.shared import Call, authtypes
from gmusicapi.utils import utils

base_url = 'https://play.google.com/music/'
service_url = base_url + 'services/'

#Shared response schemas, built to include metadata expectations.
song_schema = {
    "type": "object",
    "properties": dict(
        (name, expt.get_schema()) for
        name, expt in md_expectations.items()
    ),
    #don't allow metadata not in expectations
    "additionalProperties": False
}

song_array = {
    "type": "array",
    "items": song_schema
}

pl_schema = {
    "type": "object",
    "properties": {
        "continuation": {"type": "boolean"},
        "playlist": song_array,
        "playlistId": {"type": "string"},
        "unavailableTrackCount": {"type": "integer"},
        #only appears when loading multiple playlists
        "title": {"type": "string", "required": False},
        "continuationToken": {"type": "string", "required": False}
    },
    "additionalProperties": False
}

pl_array = {
    "type": "array",
    "items": pl_schema
}


class Init(Call):
    """Called after login and once before any other webclient call.
    This gathers the cookies we need (specifically xt); it's the call that
    creates the webclient DOM."""

    static_method = 'HEAD'
    static_url = base_url + 'listen'

    required_auth = authtypes(sso=True)

    #This call doesn't actually request/return anything useful aside from cookies.
    @staticmethod
    def parse_response(response):
        return response.text

    @classmethod
    def check_success(cls, response, msg):
        if response.status_code != 200:
            raise CallFailure(('status code %s != 200' % response.status_code), cls.__name__)
        if 'xt' not in response.cookies:
            raise CallFailure('did not receieve xt cookies', cls.__name__)


class WcCall(Call):
    """Abstract base for web client calls."""

    required_auth = authtypes(xt=True, sso=True)

    #validictory schema for the response
    _res_schema = utils.NotImplementedField

    @classmethod
    def validate(cls, response, msg):
        """Use validictory and a static schema (stored in cls._res_schema)."""
        try:
            return validictory.validate(msg, cls._res_schema)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ValidationException(str(e)), None, trace

    @classmethod
    def check_success(cls, response, msg):
        #Failed responses always have a success=False key.
        #Some successful responses do not have a success=True key, however.
        #TODO remove utils.call_succeeded

        if 'success' in msg and not msg['success']:
            raise CallFailure(
                "the server reported failure. This is usually"
                " caused by bad arguments, but can also happen if requests"
                " are made too quickly (eg creating a playlist then"
                " modifying it before the server has created it)",
                cls.__name__)

    @classmethod
    def parse_response(cls, response):
        return cls._parse_json(response.text)


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

    @staticmethod
    def filter_response(msg):
        filtered = copy.copy(msg)
        filtered['songIds'] = ["<%s songs>" % len(filtered.get('songIds', []))]
        return filtered


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
        """
        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """
        return {
            'json': json.dumps(
                {"playlistId": playlist_id, "playlistName": new_name}
            )
        }


class ChangePlaylistOrder(WcCall):
    """Reorder existing tracks in a playlist."""

    static_method = 'POST'
    static_url = service_url + 'changeplaylistorder'

    _res_schema = {
        "type": "object",
        "properties": {
            "afterEntryId": {"type": "string", "blank": True},
            "playlistId": {"type": "string"},
            "movedSongIds": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(playlist_id, song_ids_moving, entry_ids_moving,
                     after_entry_id=None, before_entry_id=None):
        """
        :param playlist_id: id of the playlist getting reordered.
        :param song_ids_moving: a list of consecutive song ids. Matches entry_ids_moving.
        :param entry_ids_moving: a list of consecutive entry ids to move. Matches song_ids_moving.
        :param after_entry_id: the entry id to place these songs after. Default first position.
        :param before_entry_id: the entry id to place these songs before. Default last position.
        """

        # empty string means first/last position
        if after_entry_id is None:
            after_entry_id = ""
        if before_entry_id is None:
            before_entry_id = ""

        return {
            'json': json.dumps(
                {
                    "playlistId": playlist_id,
                    "movedSongIds": song_ids_moving,
                    "movedEntryIds": entry_ids_moving,
                    "afterEntryId": after_entry_id,
                    "beforeEntryId": before_entry_id
                }
            )
        }

    @staticmethod
    def filter_response(msg):
        filtered = copy.copy(msg)
        filtered['movedSongIds'] = ["<%s songs>" % len(filtered.get('movedSongIds', []))]
        return filtered


class DeletePlaylist(WcCall):
    """Delete a playlist."""

    static_method = 'POST'
    static_url = service_url + 'deleteplaylist'

    _res_schema = {
        "type": "object",
        "properties": {
            "deleteId": {"type": "string"}
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(playlist_id):
        """
        :param playlist_id: id of the playlist to delete.
        """
        return {
            'json': json.dumps(
                {"id": playlist_id}
            )
        }


class DeleteSongs(WcCall):
    """Delete a song from the entire library or a single playlist."""

    static_method = 'POST'
    static_url = service_url + 'deletesong'

    _res_schema = {
        "type": "object",
        "properties": {
            "listId": {"type": "string"},
            "deleteIds":
            {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(song_ids, playlist_id='all', entry_ids=None):
        """
        :param song_ids: a list of song ids.
        :param playlist_id: playlist id to delete from, or 'all' for deleting from library.
        :param entry_ids: when deleting from playlists, corresponding list of entry ids.
        """

        if entry_ids is None:
            #this is strange, but apparently correct
            entry_ids = [''] * len(song_ids)

        return {
            'json': json.dumps(
                {"songIds": song_ids, "entryIds": entry_ids, "listId": playlist_id}
            )
        }

    @staticmethod
    def filter_response(msg):
        filtered = copy.copy(msg)
        filtered['deleteIds'] = ["<%s songs>" % len(filtered.get('deleteIds', []))]
        return filtered


class GetLibrarySongs(WcCall):
    """Loads tracks from the library.

    Libraries can have many tracks, so GM gives them back in chunks.

    Chunks will send a continuation token to get the next chunk.

    The first request needs no continuation token.
    The last response will not send a token.
    """

    static_method = 'POST'
    static_url = service_url + 'loadalltracks'

    _res_schema = {
        "type": "object",
        "properties": {
            "continuation": {"type": "boolean"},
            "differentialUpdate": {"type": "boolean"},
            "playlistId": {"type": "string"},
            "requestTime": {"type": "integer"},
            "playlist": song_array,
        },
        "additionalProperties": {
            "continuationToken": {"type": "string"}}
    }

    @staticmethod
    def dynamic_data(cont_token=None):
        """:param cont_token: (optional) token to get the next library chunk."""
        if not cont_token:
            req = {}
        else:
            req = {"continuationToken": cont_token}

        return {'json': json.dumps(req)}

    @staticmethod
    def filter_response(msg):
        """Only log the number of songs."""
        filtered = copy.copy(msg)
        filtered['playlist'] = ["<%s songs>" % len(filtered.get('playlist', []))]

        return filtered


class GetPlaylistSongs(WcCall):
    """Loads tracks from a playlist.
    Tracks include playlistEntryIds.
    """

    static_method = 'POST'
    static_url = service_url + 'loadplaylist'

    @classmethod
    def dynamic_data(cls, playlist_id):
        """
        :param playlist_id: id to retrieve from, or 'all' to get all playlists.
        """

        #This call has a dynamic response schema based on the request.

        if playlist_id == 'all':
            cls._res_schema = {
                "type": "object",
                "properties": {
                    "playlists": pl_array,
                },
                "additionalProperties": False
            }

            return {'json': json.dumps({})}

        else:
            cls._res_schema = pl_schema
            return {'json': json.dumps({'id': playlist_id})}

    @staticmethod
    def filter_response(msg):
        """Log number of songs/playlists."""
        filtered = copy.copy(msg)

        if 'playlists' in msg:
            filtered['playlists'] = ["<%s playlists>" % len(filtered['playlists'])]

        else:
            filtered['playlist'] = ["<%s songs>" % len(filtered['playlist'])]

        return filtered


class ChangeSongMetadata(WcCall):
    """Edit the metadata of songs."""

    static_method = 'POST'
    static_url = service_url + 'modifyentries'

    _res_schema = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "songs": song_array
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(songs):
        """
        :param songs: a list of dictionary representations of songs
        """
        return {'json': json.dumps({'entries': songs})}

    @staticmethod
    def filter_response(msg):
        filtered = copy.copy(msg)
        filtered['songs'] = ["<%s songs>" % len(filtered.get('songs', []))]
        return filtered

    @staticmethod
    def validate(response, msg):
        """The data that comes back doesn't follow normal metadata rules,
        and is meaningless anyway; it'll lie about results."""
        pass


class GetDownloadInfo(WcCall):
    """Get download links and counts for songs."""

    static_method = 'POST'
    static_url = service_url + 'multidownload'

    _res_schema = {
        "type": "object",
        "properties": {
            "downloadCounts": {
                "type": "object",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"}
                    }
                }
            },
            "url": {"type": "string"}
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(song_ids):
        """
        :param: (list) song_ids
        """
        return {'json': json.dumps({'songIds': song_ids})}


class GetStreamUrl(WcCall):
    """Used to request a streaming link of a track."""

    static_method = 'GET'
    static_url = base_url + 'play'  # note use of base_url, not service_url

    required_auth = authtypes(sso=True)  # no xt required

    _res_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"}
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_params(song_id):
        return {
            'u': 0,  # select first user of logged in; probably shouldn't be hardcoded
            'pt': 'e',  # unknown
            'songid': song_id,
        }


class Search(WcCall):
    """Fuzzily search for songs, artists and albums.
    Not needed for most use-cases; local search is usually faster and more flexible"""

    static_method = 'POST'
    static_url = service_url + 'search'

    _res_schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "object",
                "properties": {
                    "artists": song_array,  # hits on artists
                    "songs": song_array,    # hits on tracks
                    "albums": {             # hits on albums; no track info returned
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "artistName": {"type": "string", "blank": True},
                                "imageUrl": {"type": "string", "required": False},
                                "albumArtist": {"type": "string", "blank": True},
                                "albumName": {"type": "string"},
                            }
                        }
                    }
                }
            }
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(query):
        return {'json': json.dumps({'q': query})}


class ReportBadSongMatch(WcCall):
    """Request to signal the uploader to reupload a matched track."""

    static_method = 'POST'
    static_url = service_url + 'fixsongmatch'
    static_params = {'format': 'jsarray'}

    #This no longer holds.
    expected_response = [[0], []]

    @classmethod
    def validate(cls, response, msg):
        pass
        #if msg != cls.expected_response:
        #    raise ValidationException("response != %r" % cls.expected_response)

    @staticmethod
    def dynamic_data(song_ids):
        return json.dumps([["", 1], [song_ids]])


class UploadImage(WcCall):
    """Upload an image for use as album art."""

    static_method = 'POST'
    static_url = service_url + 'imageupload'
    static_params = {'zx': '',  # ??
                     'u': 0}

    _res_schema = {
        'type': 'object',
        'properties': {
            'imageUrl': {'type': 'string', 'blank': False},
            'imageDisplayUrl': {'type': 'string', 'blank': False},
        },
        'additionalProperties': False
    }

    @staticmethod
    def dynamic_files(image_filepath):
        """
        :param image_filepath: path to an image
        """
        with open(image_filepath, 'rb') as f:
            contents = f.read()

        return {'albumArt': (image_filepath, contents)}
