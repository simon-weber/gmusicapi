#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the web client."""

import binascii
import hmac
import random
import string
import sys
from hashlib import sha1

import validictory

from gmusicapi.exceptions import CallFailure, ValidationException
from gmusicapi.protocol.shared import Call, authtypes
from gmusicapi.utils import utils

# URL for sj service
sj_url = 'https://www.googleapis.com/sj/v1/'

# Data schema for sj service. Might be incomplete
sj_track = {
        'type':'object',
        'properties':{
                'kind':{'type':'string'},
                'title':{'type':'string'},
                'artist':{'type':'string'},
                'album':{'type':'string'},
                'albumArtist':{'type':'string'},
                'trackNumber':{'type':'integer'},
                'durationMillis':{'type':'string'},
                'albumArtRef':{'type':'array', 'items':{'type':'object', 'properties':{'url':{'type':'string'}}}},
                'discNumber':{'type':'integer'},
                'estimatedSize':{'type':'string'},
                'trackType':{'type':'string'},
                'storeId':{'type':'string'},
                'albumId':{'type':'string'},
                'artistId':{'type':'array', 'items':{'type':'string'}},
                'nid':{'type':'string'},
                'trackAvailableForPurchase':{'type':'boolean'},
                'albumAvailableForPurchase':{'type':'boolean'},
            }
    }

sj_album = {
        'type':'object',
        'properties':{
                'kind':{'type':'string'},
                'name':{'type':'string'},
                'albumArtist':{'type':'string'},
                'albumArtRef':{'type':'string'},
                'albumId':{'type':'string'},
                'artist':{'type':'string'},
                'artistId':{'type':'array', 'items':{'type':'string'}},
                'year': {'type': 'integer'},
                'tracks': {'type':'array', 'items':sj_track}
            }
    }

sj_artist = {
        'type':'object',
        'properties':{
                'kind':{'type':'string'},
                'name':{'type':'string'},
                'artistArtRef':{'type':'string'},
                'artistId':{'type':'string'},
                'albums:':{'type':'array', 'items':sj_album, 'required':False},
                'topTracks':{'type':'array', 'items':sj_track, 'required':False},
            }
    }

sj_artist['related_artists']= {'type':'array', 'items':sj_artist, 'required':False}
# Result definition may not contain any item.
sj_result = {
        "type":"object",
        "properties":{
                'score':{"type":"number"},
                'artists':sj_artist,
                'album': sj_album,
                'track': sj_track
            }
    }

sj_result['properties']['artists']['required']=False
sj_result['properties']['album']['required']=False
sj_result['properties']['track']['required']=False

class MCall(Call):
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


class Search(MCall):
    """Search for All Access tracks."""

    static_method = 'GET'

    _res_schema = {
            "type": "object",
            "properties": {
                "kind":{"type":"string"},
                "entries": {'type':'array', 'items': sj_result}
            },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_url(query, max_ret):
        return  sj_url + 'query?q=%s&max-results=%d' % (query, max_ret)

class GetArtist(MCall):
    static_method = 'GET'
    _res_schema = sj_artist

    @staticmethod
    def dynamic_url(artistid, albums=True, top_tracks=0, rel_artist=0):
        ret = sj_url + 'fetchartist?alt=json'
        ret += '&nid=%s' % artistid
        ret += '&include-albums=%r' % albums
        ret += '&num-top-tracks=%d' % top_tracks
        ret += '&num-related-artists=%d' % rel_artist
        return ret

class GetAlbum(MCall):
    static_method = 'GET'
    _res_schema = sj_album

    @staticmethod
    def dynamic_url(albumid, tracks=True):
        ret = sj_url + 'fetchalbum?alt=json'
        ret += '&nid=%s' % albumid
        ret += '&include-tracks=%r' % tracks
        return ret

class GetTrack(MCall):
    static_method = 'GET'
    _res_schema = sj_track

    @staticmethod
    def dynamic_url(trackid):
        ret = sj_url + 'fetchtrack?alt=json'
        ret += '&nid=%s' % trackid
        return ret

class GetStreamUrl(MCall):
    """Used to request a streaming link of a track."""

    static_method = 'GET'
    static_url =  'https://play.google.com/music/play'  # note use of base_url, not service_url

    required_auth = authtypes(sso=True)  # no xt required

    _res_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "required": False},
            "urls": {"type": "array", "required": False}
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_params(song_id):

        # https://github.com/simon-weber/Unofficial-Google-Music-API/issues/137
        # there are three cases when streaming:
        #   | track type              | guid songid? | slt/sig needed? |
        #    user-uploaded              yes            no
        #    AA track in library        yes            yes
        #    AA track not in library    no             yes

        # without the track['type'] field we can't tell between 1 and 2, but
        # include slt/sig anyway; the server ignores the extra params.
        key = '27f7313e-f75d-445a-ac99-56386a5fe879'
        salt = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(12))
        sig = binascii.b2a_base64(hmac.new(key, (song_id + salt), sha1).digest())[:-1]
        urlsafe_b64_trans = string.maketrans("+/=", "-_.")
        sig = sig.translate(urlsafe_b64_trans)

        params = {
            'u': 0,
            'pt': 'e',
            'slt': salt,
            'sig': sig
        }

        # TODO match guid instead, should be more robust
        if song_id[0] == 'T':
            # all access
            params['mjck'] = song_id
        else:
            params['songid'] = song_id
        return params

