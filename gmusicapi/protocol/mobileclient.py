#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the mobile client."""

import base64
import copy
from datetime import datetime
from hashlib import sha1
import hmac
import sys
import time
from uuid import uuid1

import validictory

from gmusicapi.compat import json
from gmusicapi.exceptions import ValidationException, CallFailure
from gmusicapi.protocol.shared import Call, authtypes
from gmusicapi.utils import utils

# URL for sj service
sj_url = 'https://www.googleapis.com/sj/v1.1/'

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
        'artistArtRef': {'type': 'array',
                         'items': {'type': 'object', 'properties': {'url': {'type': 'string'}}},
                         'required': False,
                       },
        'discNumber': {'type': 'integer'},
        'estimatedSize': {'type': 'string'},
        'trackType': {'type': 'string'},
        'storeId': {'type': 'string'},
        'albumId': {'type': 'string'},
        'artistId': {'type': 'array',
                     'items': {'type': 'string', 'blank': True}, 'required': False},
        'nid': {'type': 'string'},
        'trackAvailableForPurchase': {'type': 'boolean'},
        'albumAvailableForPurchase': {'type': 'boolean'},
        'composer': {'type': 'string', 'blank': True},
        'playCount': {'type': 'integer', 'required': False},
        'year': {'type': 'integer', 'required': False},
        'rating': {'type': 'string', 'required': False},
        'genre': {'type': 'string', 'required': False},
    }
}

sj_playlist = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'deleted': {'type': 'boolean'},
        'type': {'type': 'string',
                 'pattern': r'MAGIC|SHARED|USER_GENERATED',
                 'required': False,
                 },
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

sj_plentry = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'id': {'type': 'string'},
        'clientId': {'type': 'string'},
        'playlistId': {'type': 'string'},
        'absolutePosition': {'type': 'string'},
        'trackId': {'type': 'string'},
        'creationTimestamp': {'type': 'string'},
        'lastModifiedTimestamp': {'type': 'string'},
        'deleted': {'type': 'boolean'},
        'source': {'type': 'string'},
        'track': sj_track.copy()
    },
}

sj_plentry['properties']['track']['required'] = False


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
        'artistId': {'type': 'array', 'items': {'type': 'string', 'blank': True}},
        'year': {'type': 'integer'},
        'tracks': {'type': 'array', 'items': sj_track, 'required': False},
        'description': {'type': 'string', 'required': False},
    }
}

sj_artist = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'artistArtRef': {'type': 'string', 'required': False},
        'artistBio': {'type': 'string', 'required': False},
        'artistId': {'type': 'string', 'blank': True},
        'albums': {'type': 'array', 'items': sj_album, 'required': False},
        'topTracks': {'type': 'array', 'items': sj_track, 'required': False},
        'total_albums': {'type': 'integer', 'required': False},
        'artistBio': {'type': 'string', 'required': False},
    }
}

sj_artist['properties']['related_artists'] = {
    'type': 'array',
    'items': sj_artist,  # note the recursion
    'required': False
}

sj_result = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'score': {'type': 'number'},
        'type': {'type': 'string'},
        'best_result': {'type': 'boolean', 'required': False},
        'navigational_result': {'type': 'boolean', 'required': False},
        'navigational_confidence': {'type': 'number', 'required': False},
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


class McListCall(McCall):
    """Abc for calls that list a resource."""
    # concrete classes provide:
    item_schema = utils.NotImplementedField
    filter_text = utils.NotImplementedField

    static_headers = {'Content-Type': 'application/json'}
    static_params = {'alt': 'json', 'include-tracks': 'true'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'nextPageToken': {'type': 'string', 'required': False},
            'data': {'type': 'object',
                     'items': {'type': 'array', 'items': item_schema},
                     'required': False,
                    },
        },
    }

    @classmethod
    def dynamic_params(cls, updated_after=None, start_token=None, max_results=None):
        """
        :param updated_after: datetime.datetime; defaults to epoch
        """

        if updated_after is None:
            microseconds = 0
        else:
            microseconds = utils.datetime_to_microseconds(updated_after)

        return {'updated-min': microseconds}

    @classmethod
    def dynamic_data(cls, updated_after=None, start_token=None, max_results=None):
        """
        :param updated_after: ignored
        :param start_token: nextPageToken from a previous response
        :param max_results: a positive int; if not provided, server defaults to 1000
        """
        data = {}

        if start_token is not None:
            data['start-token'] = start_token

        if max_results is not None:
            data['max-results'] = str(max_results)

        return json.dumps(data)

    @classmethod
    def parse_response(cls, response):
        # empty results don't include the data key
        # make sure it's always there
        res = cls._parse_json(response.text)
        if 'data' not in res:
            res['data'] = {'items': []}

        return res

    @classmethod
    def filter_response(cls, msg):
        filtered = copy.deepcopy(msg)
        filtered['data']['items'] = ["<%s %s>" % (len(filtered['data']['items']),
                                                  cls.filter_text)]
        return filtered


class McBatchMutateCall(McCall):
    """Abc for batch mutation calls."""

    static_headers = {'Content-Type': 'application/json'}
    static_params = {'alt': 'json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'mutate_response': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string', 'required': False},
                        'client_id': {'type': 'string', 'blank': True,
                                      'required': False},
                        'response_code': {'type': 'string'},
                    },
                },
            }
        },
    }

    @staticmethod
    def dynamic_data(mutations):
        """
        :param mutations: list of mutation dictionaries
        """

        return json.dumps({'mutations': mutations})

    @classmethod
    def check_success(cls, response, msg):
        if ('error' in msg or
            not all([d.get('response_code', None) in ('OK', 'CONFLICT')
                     for d in msg.get('mutate_response', [])])):
            raise CallFailure('The server reported failure while'
                              ' changing the requested resource.'
                              " If this wasn't caused by invalid arguments"
                              ' or server flakiness,'
                              ' please open an issue.',
                              cls.__name__)


class Search(McCall):
    """Search for All Access tracks."""
    static_method = 'GET'
    static_url = sj_url + 'query'

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'entries': {'type': 'array',
                        'items': sj_result,
                        'required': False}
        },
    }

    @staticmethod
    def dynamic_params(query, max_results):
        return {'q': query, 'max-results': max_results}


class ListTracks(McListCall):
    item_schema = sj_track
    filter_text = 'tracks'

    static_method = 'POST'
    static_url = sj_url + 'trackfeed'


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


class ListPlaylists(McListCall):
    item_schema = sj_playlist
    filter_text = 'playlists'

    static_method = 'POST'
    static_url = sj_url + 'playlistfeed'


class ListPlaylistEntries(McListCall):
    item_schema = sj_plentry
    filter_text = 'plentries'

    static_method = 'POST'
    static_url = sj_url + 'plentryfeed'


class ListSharedPlaylistEntries(McListCall):
    shared_plentry = sj_plentry.copy()
    del shared_plentry['properties']['playlistId']
    del shared_plentry['properties']['clientId']

    item_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'shareToken': {'type': 'string'},
            'responseCode': {'type': 'string'},
            'playlistEntry': {
                'type': 'array',
                'items': shared_plentry,
                'required': False,
            }
        }
    }
    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'entries': {'type': 'array',
                        'items': item_schema,
                       },
        },
    }
    filter_text = 'shared plentries'

    static_method = 'POST'
    static_url = sj_url + 'plentries/shared'

    # odd: this request has an additional level of nesting compared to others,
    # and changes the data/entry schema to entries/playlistEntry.
    # Those horrible naming choices make this even harder to understand.

    @classmethod
    def dynamic_params(cls, share_token, updated_after=None, start_token=None, max_results=None):
        return super(ListSharedPlaylistEntries, cls).dynamic_params(
            updated_after, start_token, max_results)

    @classmethod
    def dynamic_data(cls, share_token, updated_after=None, start_token=None, max_results=None):
        """
        :param share_token: from a shared playlist
        :param updated_after: ignored
        :param start_token: nextPageToken from a previous response
        :param max_results: a positive int; if not provided, server defaults to 1000
        """
        data = {}

        data['shareToken'] = share_token

        if start_token is not None:
            data['start-token'] = start_token

        if max_results is not None:
            data['max-results'] = str(max_results)

        return json.dumps({'entries': [data]})

    @classmethod
    def parse_response(cls, response):
        res = cls._parse_json(response.text)
        if 'playlistEntry' not in res['entries'][0]:
            res['entries'][0]['playlistEntry'] = []

        return res

    @classmethod
    def filter_response(cls, msg):
        filtered = copy.deepcopy(msg)
        filtered['entries'][0]['playlistEntry'] = ["<%s %s>" %
                                                   (len(filtered['entries'][0]['playlistEntry']),
                                                    cls.filter_text)]
        return filtered


class BatchMutatePlaylists(McBatchMutateCall):
    static_method = 'POST'
    static_url = sj_url + 'playlistbatch'

    #TODO is it possible to mutate name through this?

    @staticmethod
    def build_playlist_deletes(playlist_ids):
        #TODO can probably pull this up one
        """
        :param playlist_ids
        """
        return [{'delete': id} for id in playlist_ids]

    @staticmethod
    def build_playlist_updates(pl_id_name_pairs):
        """
        :param pl_id_name_pairs: [(playlist_id, new_name)]
        """
        return [{'update': {'id': pl_id, 'name': new_name}} for
                (pl_id, new_name) in pl_id_name_pairs]

    @staticmethod
    def build_playlist_adds(names):
        """
        :param names
        """

        return [{'create': {
            'creationTimestamp': '-1',
            'deleted': False,
            'lastModifiedTimestamp': '0',
            'name': name,
            'type': 'USER_GENERATED'
        }} for name in names]


class BatchMutatePlaylistEntries(McBatchMutateCall):
    filter_text = 'plentries'
    item_schema = sj_plentry

    static_method = 'POST'
    static_url = sj_url + 'plentriesbatch'

    @staticmethod
    def build_plentry_deletes(entry_ids):
        """
        :param entry_ids
        """
        return [{'delete': id} for id in entry_ids]

    @staticmethod
    def build_plentry_reorder(plentry, preceding_cid, following_cid):
        """
        :param plentry: plentry that is moving
        :param preceding_cid: clientid of entry that will be before the moved entry
        :param following_cid: "" that will be after the moved entry
        """

        mutation = copy.deepcopy(plentry)
        keys_to_keep = set(['clientId', 'creationTimestamp', 'deleted', 'id',
                            'lastModifiedTimestamp', 'playlistId',
                            'source', 'trackId'])

        for key in mutation.keys():
            if key not in keys_to_keep:
                del mutation[key]

        # horribly misleading key names; these are _clientids_
        # using entryids works sometimes, but with seemingly random results
        if preceding_cid:
            mutation['precedingEntryId'] = preceding_cid

        if following_cid:
            mutation['followingEntryId'] = following_cid

        return {'update': mutation}

    @staticmethod
    def build_plentry_adds(playlist_id, song_ids):
        """
        :param playlist_id
        :param song_ids
        """

        mutations = []

        prev_id, cur_id, next_id = None, str(uuid1()), str(uuid1())

        for i, song_id in enumerate(song_ids):
            m_details = {
                'clientId': cur_id,
                'creationTimestamp': '-1',
                'deleted': False,
                'lastModifiedTimestamp': '0',
                'playlistId': playlist_id,
                'source': 1,
                'trackId': song_id,
            }

            if song_id.startswith('T'):
                m_details['source'] = 2  # AA track

            if i > 0:
                m_details['precedingEntryId'] = prev_id
            if i < len(song_ids) - 1:
                m_details['followingEntryId'] = next_id

            mutations.append({'create': m_details})
            prev_id, cur_id, next_id = cur_id, next_id, str(uuid1())

        return mutations


class ListStations(McListCall):
    item_schema = sj_station
    filter_text = 'stations'

    static_method = 'POST'
    static_url = sj_url + 'radio/station'


class ListStationTracks(McListCall):
    # this isn't really proper usage of the abc:
    #  * there is no paging (assumed, not proven)
    #  * the query interface is totally different

    # clients.Mobileclient will
    # just have to wire up the call itself

    item_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'radioId': {'type': 'string'},
            'tracks': {'type': 'array', 'required': False, 'items': sj_track},
        }
    }

    filter_text = 'stations'

    static_method = 'POST'
    static_url = sj_url + 'radio/stationfeed'

    @staticmethod
    def dynamic_params(*args, **kwargs):
        # override the parent (which has params for paging support)
        return {}

    @staticmethod
    def dynamic_data(station_id, num_entries, recently_played):
        """
        :param station_id
        :param num_entries: maximum number of tracks to return
        :param recently_played: a list of...song ids? never seen an example
        """
        #TODO
        # clearly, this supports more than one at a time,
        # but then that might introduce paging?
        # I'll leave it for someone else

        return json.dumps({'contentFilter': 1,
                           'stations': [
                               {
                                   'numEntries': num_entries,
                                   'radioId': station_id,
                                   'recentlyPlayed': recently_played
                               }
                           ]})

    @staticmethod
    def filter_response(msg):
        filtered = copy.deepcopy(msg)
        if 'tracks' in filtered['data']['items']:
            filtered['data']['items']['tracks'] = \
                    ["<%s tracks>" % len(filtered['data']['items']['tracks'])]
        return filtered


class BatchMutateStations(McBatchMutateCall):
    static_method = 'POST'
    static_url = sj_url + 'radio/editstation'

    @staticmethod
    def build_deletes(station_ids):
        """
        :param station_ids
        """
        return [{'delete': id, 'includeFeed': False, 'numEntries': 0}
                for id in station_ids]

    @staticmethod
    def build_add(name, seed, include_tracks, num_tracks, recent_datetime=None):
        """
        :param name: the title
        :param seed: a dict with a single pair, {'itemId': id}
        :param include_tracks: if True, return `num_tracks` tracks in the response
        :param num_tracks:
        :param recent_datetime: purpose unknown. defaults to now.
        """

        if recent_datetime is None:
            recent_datetime = datetime.now()

        recent_timestamp = utils.datetime_to_microseconds(recent_datetime)

        return {
            "create": {
                "clientId": str(uuid1()),
                "deleted": False,
                "imageType": 1,
                "lastModifiedTimestamp": "-1",
                "name": name,
                "recentTimestamp": str(recent_timestamp),
                "seed": seed,
                "tracks": []
            },
            "includeFeed": include_tracks,
            "numEntries": num_tracks,
            "params":
            {
                "contentFilter": 1
            }
        }


class BatchMutateTracks(McBatchMutateCall):
    static_method = 'POST'
    static_url = sj_url + 'trackbatch'

    # utility functions to build the mutation dicts
    @staticmethod
    def build_track_deletes(track_ids):
        """
        :param track_ids
        """
        return [{'delete': id} for id in track_ids]

    @staticmethod
    def build_track_add(store_track_info):
        """
        :param store_track_info: sj_track
        """
        track_dict = copy.deepcopy(store_track_info)
        for key in ('kind', 'trackAvailableForPurchase',
                    'albumAvailableForPurchase', 'albumArtRef',
                    'artistId',
                   ):
            del track_dict[key]

        for key, default in {
            'playCount': 0,
            'rating': '0',
            'genre': '',
            'lastModifiedTimestamp': '0',
            'deleted': False,
            'beatsPerMinute': -1,
            'composer': '',
            'creationTimestamp': '-1',
            'totalDiscCount': 0,
        }.items():
            track_dict.setdefault(key, default)

        # TODO unsure about this
        track_dict['trackType'] = 8

        return {'create': track_dict}


class GetStoreTrack(McCall):
    #TODO does this accept library ids, too?
    static_method = 'GET'
    static_url = sj_url + 'fetchtrack'
    static_headers = {'Content-Type': 'application/json'}
    static_params = {'alt': 'json'}

    _res_schema = sj_track

    @staticmethod
    def dynamic_params(track_id):
        return {'nid': track_id}


class GetGenres(McCall):
    static_method = 'GET'
    static_url = sj_url + 'explore/genres'
    static_params = {'alt': 'json'}

    genre_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'name': {'type': 'string'},
            'id': {'type': 'string'},
            'kind': {'type': 'string'},
            'images': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'url': {'type': 'string'}
                    },
                }
            },
            'children': {
                'type': 'array',
                'items': {'type': 'string'},
                'required': False,
            }
        }
    }

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'genres': {
                'type': 'array',
                'items': genre_schema,
            }
        }
    }


class GetArtist(McCall):
    static_method = 'GET'
    static_url = sj_url + 'fetchartist'
    static_params = {'alt': 'json'}

    _res_schema = sj_artist

    @staticmethod
    def dynamic_params(artist_id, include_albums, num_top_tracks, num_rel_artist):
        """
        :param include_albums: bool
        :param num_top_tracks: int
        :param num_rel_artist: int
        """

        return {'nid': artist_id,
                'include-albums': include_albums,
                'num-top-tracks': num_top_tracks,
                'num-related-artists': num_rel_artist,
               }


class GetAlbum(McCall):
    static_method = 'GET'
    static_url = sj_url + 'fetchalbum'
    static_params = {'alt': 'json'}

    _res_schema = sj_album

    @staticmethod
    def dynamic_params(album_id, tracks):
        return {'nid': album_id, 'include-tracks': tracks}
