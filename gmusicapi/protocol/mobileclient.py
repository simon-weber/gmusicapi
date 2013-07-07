#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the web client."""

import sys

import validictory

from gmusicapi.exceptions import CallFailure, ValidationException
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
        'artistArtRef': {'type': 'string'},
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
    static_method = 'GET'
    static_url = sj_url + 'tracks'

    _res_schema = {}


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
