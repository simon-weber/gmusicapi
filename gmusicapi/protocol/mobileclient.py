#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the mobile client."""

import base64
import copy
from hashlib import sha1
import hmac
import sys
import time


import validictory

from gmusicapi.compat import json
from gmusicapi.exceptions import ValidationException
from gmusicapi.protocol.shared import Call, authtypes
from gmusicapi.utils import utils

# URL for sj service
sj_url = 'https://www.googleapis.com/sj/v1/'

# shared schemas
sj_track = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'title': {'type': 'string'},
        'artist': {'type': 'string'},
        'album': {'type': 'string'},
        'albumArtist': {'type': 'string'},
        'trackNumber': {'type': 'integer'},
        'durationMillis': {'type': 'string'},
        'albumArtRef': {'type': 'array',
                        'items': {'type': 'object', 'properties': {'url': {'type': 'string'}}}},
        'discNumber': {'type': 'integer'},
        'estimatedSize': {'type': 'string'},
        'trackType': {'type': 'string'},
        'storeId': {'type': 'string'},
        'albumId': {'type': 'string'},
        'artistId': {'type': 'array', 'items': {'type': 'string'}},
        'nid': {'type': 'string'},
        'trackAvailableForPurchase': {'type': 'boolean'},
        'albumAvailableForPurchase': {'type': 'boolean'},
        'playCount': {'type': 'integer', 'required': False},
        'year': {'type': 'integer', 'required': False},
    }
}

sj_playlist = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'deleted': {'type': 'boolean'},
        'type': {'type': 'string', 'required': False},
        'lastModifiedTimestamp': {'type': 'string'},
        'recentTimestamp': {'type': 'string'},
        'shareToken': {'type': 'string'},
        'ownerProfilePhotoUrl': {'type': 'string'},
        'ownerName': {'type': 'string'},
        'accessControlled': {'type': 'boolean'},
        'creationTimestamp': {'type': 'string'},
        'id': {'type': 'string'},
        'albumArtRef': {'type': 'array',
                        'items': {'type': 'object', 'properties': {'url': {'type': 'string'}}},
                        'required': False,
                       },
    }
}

sj_album = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'albumArtist': {'type': 'string'},
        'albumArtRef': {'type': 'string'},
        'albumId': {'type': 'string'},
        'artist': {'type': 'string'},
        'artistId': {'type': 'array', 'items': {'type': 'string'}},
        'year': {'type': 'integer'},
        'tracks': {'type': 'array', 'items': sj_track, 'required': False}
    }
}

sj_artist = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'artistArtRef': {'type': 'string', 'required': False},
        'artistId': {'type': 'string'},
        'albums': {'type': 'array', 'items': sj_album, 'required': False},
        'topTracks': {'type': 'array', 'items': sj_track, 'required': False},
        'total_albums': {'type': 'integer', 'required': False},
    }
}

sj_artist['properties']['related_artists'] = {
    'type': 'array',
    'items': sj_artist,  # note the recursion
    'required': False
}

# Result definition may not contain any item.
sj_result = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'score': {'type': 'number'},
        'type': {'type': 'string'},
        'best_result': {'type': 'boolean', 'required': False},
        'artist': sj_artist.copy(),
        'album': sj_album.copy(),
        'track': sj_track.copy(),
    }
}

sj_result['properties']['artist']['required'] = False
sj_result['properties']['album']['required'] = False
sj_result['properties']['track']['required'] = False

sj_station_seed = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        # one of these will be present
        'albumId': {'type': 'string', 'required': False},
        'artistId': {'type': 'string', 'required': False},
        'genreId': {'type': 'string', 'required': False},
        'trackId': {'type': 'string', 'required': False},
        'trackLockerId': {'type': 'string', 'required': False},
    }
}

sj_station = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'imageUrl': {'type': 'string'},
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'deleted': {'type': 'boolean'},
        'lastModifiedTimestamp': {'type': 'string'},
        'recentTimestamp': {'type': 'string'},
        'clientId': {'type': 'string'},
        'seed': sj_station_seed,
        'id': {'type': 'string'},
        'description': {'type': 'string', 'required': False},
        'tracks': {'type': 'array', 'required': False, 'items': sj_track},
    }
}


class McCall(Call):
    """Abstract base for mobile client calls."""

    required_auth = authtypes(xt=False, sso=True)

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
        #TODO not sure if this is still valid for mc
        pass

        #if 'success' in msg and not msg['success']:
        #    raise CallFailure(
        #        "the server reported failure. This is usually"
        #        " caused by bad arguments, but can also happen if requests"
        #        " are made too quickly (eg creating a playlist then"
        #        " modifying it before the server has created it)",
        #        cls.__name__)

    @classmethod
    def parse_response(cls, response):
        return cls._parse_json(response.text)


class Search(McCall):
    """Search for All Access tracks."""
    static_method = 'GET'
    static_url = sj_url + 'query'

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'entries': {'type': 'array', 'items': sj_result}
        },
    }

    @staticmethod
    def dynamic_params(query, max_results):
        return {'q': query, 'max-results': max_results}


class GetLibraryTracks(McCall):
    """List tracks in the library."""
    static_method = 'POST'
    static_url = sj_url + 'trackfeed'
    static_headers = {'Content-Type': 'application/json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'nextPageToken': {'type': 'string', 'required': False},
            'data': {'type': 'object',
                     'items': {'type': 'array', 'items': sj_track},
                    },
        },
    }

    @staticmethod
    def dynamic_data(start_token=None, max_results=None):
        """
        :param start_token: nextPageToken from a previous response
        :param max_results: a positive int; if not provided, server defaults to 1000
        """
        data = {}

        if start_token is not None:
            data['start-token'] = start_token

        if max_results is not None:
            data['max-results'] = str(max_results)

        return json.dumps(data)

    @staticmethod
    def filter_response(msg):
        filtered = copy.deepcopy(msg)
        filtered['data']['items'] = ["<%s songs>" % len(filtered['data'].get('items', []))]
        return filtered


class GetStreamUrl(McCall):
    static_method = 'GET'
    static_url = 'https://android.clients.google.com/music/mplay'
    static_verify = False

    # this call will redirect to the mp3
    static_allow_redirects = False

    _s1 = base64.b64decode('VzeC4H4h+T2f0VI180nVX8x+Mb5HiTtGnKgH52Otj8ZCGDz9jRW'
                           'yHb6QXK0JskSiOgzQfwTY5xgLLSdUSreaLVMsVVWfxfa8Rw==')
    _s2 = base64.b64decode('ZAPnhUkYwQ6y5DdQxWThbvhJHN8msQ1rqJw0ggKdufQjelrKuiG'
                           'GJI30aswkgCWTDyHkTGK9ynlqTkJ5L4CiGGUabGeo8M6JTQ==')

    # bitwise and of _s1 and _s2 ascii, converted to string
    _key = ''.join([chr(ord(c1) ^ ord(c2)) for (c1, c2) in zip(_s1, _s2)])

    @classmethod
    def get_signature(cls, song_id, salt=None):
        """Return a (sig, salt) pair for url signing."""

        if salt is None:
            salt = str(int(time.time() * 1000))

        mac = hmac.new(cls._key, song_id, sha1)
        mac.update(salt)
        sig = base64.urlsafe_b64encode(mac.digest())[:-1]

        return sig, salt

    @staticmethod
    def dynamic_headers(song_id, device_id):
        return {'X-Device-ID': device_id}

    @classmethod
    def dynamic_params(cls, song_id, device_id):
        sig, salt = cls.get_signature(song_id)

        #TODO which of these should get exposed?
        params = {'opt': 'hi',
                  'net': 'wifi',
                  'pt': 'e',
                  'slt': salt,
                  'sig': sig,
                 }
        if song_id[0] == 'T':
            # all access
            params['mjck'] = song_id
        else:
            params['songid'] = song_id

        return params

    @staticmethod
    def parse_response(response):
        return response.headers['location']  # ie where we were redirected

    @classmethod
    def validate(cls, response, msg):
        pass


class ListPlaylists(McCall):
    static_method = 'POST'
    static_url = sj_url + 'playlistfeed'
    static_headers = {'Content-Type': 'application/json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'nextPageToken': {'type': 'string', 'required': False},
            'data': {'type': 'object',
                     'items': {'type': 'array', 'items': sj_playlist},
                    },
        },
    }

    @staticmethod
    def dynamic_data(start_token=None, max_results=None):
        """
        :param start_token: nextPageToken from a previous response
        :param max_results: a positive int; if not provided, server defaults to 1000
        """
        data = {}

        if start_token is not None:
            data['start-token'] = start_token

        if max_results is not None:
            data['max-results'] = str(max_results)

        return json.dumps(data)

    @staticmethod
    def filter_response(msg):
        filtered = copy.deepcopy(msg)
        filtered['data']['items'] = ["<%s playlists>" % len(filtered['data'].get('items', []))]
        return filtered


class ListStations(McCall):
    static_method = 'POST'
    static_url = sj_url + 'radio/station'
    static_headers = {'Content-Type': 'application/json'}
    static_params = {'alt': 'json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'nextPageToken': {'type': 'string', 'required': False},
            'data': {'type': 'object',
                     'items': {'type': 'array', 'items': sj_station},
                    },
        },
    }

    @staticmethod
    def dynamic_params(updated_after=None, start_token=None, max_results=None):
        """
        :param updated_after: datetime.datetime; defaults to epoch
        """

        if updated_after is None:
            microseconds = 0
        else:
            microseconds = utils.datetime_to_microseconds(updated_after)

        return {'updated-min': microseconds}

    @staticmethod
    def dynamic_data(updated_after=None, start_token=None, max_results=None):
        """
        :param updated_after: ignored
        :param start_token: nextPageToken from a previous response
        :param max_results: a positive int; if not provided, server defaults to 1000

        args/kwargs are ignored.
        """
        data = {}

        if start_token is not None:
            data['start-token'] = start_token

        if max_results is not None:
            data['max-results'] = str(max_results)

        return json.dumps(data)

    @staticmethod
    def filter_response(msg):
        filtered = copy.deepcopy(msg)
        filtered['data']['items'] = ["<%s stations>" % len(filtered['data'].get('items', []))]
        return filtered


#TODO below here
class GetArtist(McCall):
    static_method = 'GET'
    static_url = sj_url + 'fetchartist'
    static_params = {'alt': 'json'}

    _res_schema = sj_artist

    @staticmethod
    def dynamic_params(artist_id, include_albums, num_top_tracks, num_rel_artist):
        return {'nid': artist_id,
                'include-albums': include_albums,
                'num-top-tracks': num_top_tracks,
                'num-related-artists': num_rel_artist,
               }


class GetAlbum(McCall):
    static_method = 'GET'
    _res_schema = sj_album

    @staticmethod
    def dynamic_url(albumid, tracks=True):
        ret = sj_url + 'fetchalbum?alt=json'
        ret += '&nid=%s' % albumid
        ret += '&include-tracks=%r' % tracks
        return ret


class GetTrack(McCall):
    static_method = 'GET'
    _res_schema = sj_track

    @staticmethod
    def dynamic_url(trackid):
        ret = sj_url + 'fetchtrack?alt=json'
        ret += '&nid=%s' % trackid
        return ret
