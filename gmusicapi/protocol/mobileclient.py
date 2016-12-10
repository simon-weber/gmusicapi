#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Calls made by the mobile client."""
from __future__ import print_function, division, absolute_import, unicode_literals
from six import raise_from
from builtins import *  # noqa

import base64
import calendar
import copy
from datetime import datetime
from hashlib import sha1
import hmac
import time
from uuid import uuid1

import validictory

import json
from gmusicapi.exceptions import ValidationException, CallFailure
from gmusicapi.protocol.shared import Call, authtypes
from gmusicapi.utils import utils

# URL for sj service
sj_url = 'https://mclients.googleapis.com/sj/v2.5/'
sj_stream_url = 'https://mclients.googleapis.com/music/'

# shared schemas
sj_image_color_styles = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'primary': {'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'red': {'type': 'integer'},
                        'green': {'type': 'integer'},
                        'blue': {'type': 'integer'}
                    }},
        'scrim': {'type': 'object',
                  'additionalProperties': False,
                  'properties': {
                      'red': {'type': 'integer'},
                      'green': {'type': 'integer'},
                      'blue': {'type': 'integer'}
                  }},
        'accent': {'type': 'object',
                   'additionalProperties': False,
                   'properties': {
                       'red': {'type': 'integer'},
                       'green': {'type': 'integer'},
                       'blue': {'type': 'integer'}
                   }}
    }
}

sj_image = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'url': {'type': 'string'},
        'aspectRatio': {'type': 'string',
                        'required': False},
        'autogen': {'type': 'boolean',
                    'required': False},
        'colorStyles': sj_image_color_styles.copy()
    }
}

sj_image['properties']['colorStyles']['required'] = False

sj_video = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'id': {'type': 'string'},
        'title': {'type': 'string', 'required': False},
        'thumbnails': {'type': 'array',
                       'items': {'type': 'object', 'properties': {
                           'url': {'type': 'string'},
                           'width': {'type': 'integer'},
                           'height': {'type': 'integer'},
                       }}},
    }
}

sj_track = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'title': {'type': 'string'},
        'artist': {'type': 'string'},
        'album': {'type': 'string'},
        'albumArtist': {'type': 'string', 'blank': True},
        'trackNumber': {'type': 'integer'},
        'totalTrackCount': {'type': 'integer', 'required': False},
        'durationMillis': {'type': 'string'},
        'albumArtRef': {'type': 'array',
                        'items': {'type': 'object', 'properties': {'url': {'type': 'string'}}},
                        'required': False},
        'artistArtRef': {'type': 'array',
                         'items': {'type': 'object', 'properties': {'url': {'type': 'string'}}},
                         'required': False,
                         },
        'discNumber': {'type': 'integer'},
        'totalDiscCount': {'type': 'integer', 'required': False},
        'estimatedSize': {'type': 'string'},
        'trackType': {'type': 'string', 'required': False},
        'storeId': {'type': 'string', 'required': False},
        'albumId': {'type': 'string'},
        'artistId': {'type': 'array',
                     'items': {'type': 'string', 'blank': True}, 'required': False},
        'nid': {'type': 'string', 'required': False},
        'trackAvailableForPurchase': {'type': 'boolean', 'required': False},
        'albumAvailableForPurchase': {'type': 'boolean', 'required': False},
        'composer': {'type': 'string', 'blank': True},
        'playCount': {'type': 'integer', 'required': False},
        'year': {'type': 'integer', 'required': False},
        'rating': {'type': 'string', 'required': False},
        'genre': {'type': 'string', 'required': False},
        'trackAvailableForSubscription': {'type': 'boolean', 'required': False},
        'contentType': {'type': 'string'},
        # Only available when rating differs from '0'
        # when using :change_song_metadata:, specifying this value will cause all clients to
        # properly update (web/mobile). As value int(round(time.time() * 1000000)) works quite well
        'lastRatingChangeTimestamp': {'type': 'string', 'required': False},
        'primaryVideo': sj_video.copy(),
        'lastModifiedTimestamp': {'type': 'string', 'required': False},
        'explicitType': {'type': 'string', 'required': False},
        'contentType': {'type': 'string', 'required': False},
        'deleted': {'type': 'boolean', 'required': False},
        'creationTimestamp': {'type': 'string', 'required': False},
        'comment': {'type': 'string', 'required': False, 'blank': True},
        'beatsPerMinute': {'type': 'integer', 'required': False},
        'recentTimestamp': {'type': 'string', 'required': False},
        'clientId': {'type': 'string', 'required': False},
        'id': {'type': 'string', 'required': False}
    }
}
sj_track['properties']['primaryVideo']['required'] = False

sj_playlist = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'deleted': {'type': 'boolean',
                    'required': False},  # for public
        'type': {'type': 'string',
                 'pattern': r'MAGIC|SHARED|USER_GENERATED',
                 'required': False,
                 },
        'lastModifiedTimestamp': {'type': 'string',
                                  'required': False},  # for public
        'recentTimestamp': {'type': 'string',
                            'required': False},  # for public
        'shareToken': {'type': 'string'},
        'ownerProfilePhotoUrl': {'type': 'string', 'required': False},
        'ownerName': {'type': 'string',
                      'required': False},
        'accessControlled': {'type': 'boolean',
                             'required': False},  # for public
        'shareState': {'type': 'string',
                       'pattern': r'PRIVATE|PUBLIC',
                       'required': False},  # for public
        'creationTimestamp': {'type': 'string',
                              'required': False},  # for public
        'id': {'type': 'string',
               'required': False},  # for public
        'albumArtRef': {'type': 'array',
                        'items': {'type': 'object', 'properties': {'url': {'type': 'string'}}},
                        'required': False,
                        },
        'description': {'type': 'string',
                        'blank': True,
                        'required': False},
        'explicitType': {'type': 'string', 'required': False},
        'contentType': {'type': 'string', 'required': False}
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

sj_attribution = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'license_url': {'type': 'string', 'required': False},
        'license_title': {'type': 'string', 'required': False},
        'source_title': {'type': 'string', 'blank': True, 'required': False},
        'source_url': {'type': 'string', 'blank': True, 'required': False},
    }
}

sj_album = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'albumArtist': {'type': 'string'},
        'albumArtRef': {'type': 'string', 'required': False},
        'albumId': {'type': 'string'},
        'artist': {'type': 'string', 'blank': True},
        'artistId': {'type': 'array', 'items': {'type': 'string', 'blank': True}},
        'year': {'type': 'integer', 'required': False},
        'tracks': {'type': 'array', 'items': sj_track, 'required': False},
        'description': {'type': 'string', 'required': False},
        'description_attribution': sj_attribution.copy(),
        'explicitType': {'type': 'string', 'required': False},
        'contentType': {'type': 'string', 'required': False}
    }
}
sj_album['properties']['description_attribution']['required'] = False

sj_artist = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'artistArtRef': {'type': 'string', 'required': False},
        'artistArtRefs': {'type': 'array',
                          'items': sj_image,
                          'required': False},
        'artistBio': {'type': 'string', 'required': False},
        'artistId': {'type': 'string', 'blank': True, 'required': False},
        'albums': {'type': 'array', 'items': sj_album, 'required': False},
        'topTracks': {'type': 'array', 'items': sj_track, 'required': False},
        'total_albums': {'type': 'integer', 'required': False},
        'artist_bio_attribution': sj_attribution.copy(),
    }
}

sj_artist['properties']['artist_bio_attribution']['required'] = False
sj_artist['properties']['related_artists'] = {
    'type': 'array',
    'items': sj_artist,  # note the recursion
    'required': False
}

sj_genre = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'id': {'type': 'string'},
        'name': {'type': 'string'},
        'children': {
            'type': 'array',
            'required': False,
            'items': {'type': 'string'}
        },
        'parentId': {
            'type': 'string',
            'required': False,
        },
        'images': {
            'type': 'array',
            'required': False,
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'url': {'type': 'string'}
                }
            }
        }
    }
}

sj_station_metadata_seed = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        # one of these will be present
        'artist': {
            'type': sj_artist,
            'required': False
        },
        'genre': {
            'type': sj_genre,
            'required': False
        },
    }
}

sj_station_seed = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'seedType': {'type': 'string'},
        # one of these will be present
        'albumId': {'type': 'string', 'required': False},
        'artistId': {'type': 'string', 'required': False},
        'genreId': {'type': 'string', 'required': False},
        'trackId': {'type': 'string', 'required': False},
        'trackLockerId': {'type': 'string', 'required': False},
        'curatedStationId': {'type': 'string', 'required': False},
        'metadataSeed': {'type': sj_station_metadata_seed, 'required': False}
    }
}

sj_station = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'imageUrl': {'type': 'string', 'required': False},
        'kind': {'type': 'string'},
        'name': {'type': 'string'},
        'deleted': {'type': 'boolean',
                    'required': False},  # for public
        'lastModifiedTimestamp': {'type': 'string',
                                  'required': False},
        'recentTimestamp': {'type': 'string',
                            'required': False},  # for public
        'clientId': {'type': 'string',
                     'required': False},  # for public
        'skipEventHistory': {'type': 'array'},  # TODO: What's in this array?
        'seed': sj_station_seed,
        'stationSeeds': {'type': 'array',
                         'items': sj_station_seed},
        'id': {'type': 'string',
               'required': False},  # for public
        'description': {'type': 'string', 'required': False},
        'tracks': {'type': 'array', 'required': False, 'items': sj_track},
        'imageUrls': {'type': 'array',
                      'required': False,
                      'items': sj_image
                      },
        'compositeArtRefs': {'type': 'array',
                             'required': False,
                             'items': sj_image
                             },
        'contentTypes': {'type': 'array',
                         'required': False,
                         'items': {'type': 'string'}
                         },
        'byline': {'type': 'string', 'required': False}
    }
}

sj_listen_now_album = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'artist_metajam_id': {'type': 'string'},
        'artist_name': {'type': 'string'},
        'artist_profile_image': {
            'type': 'object',
            'url': {'type': 'string'}
        },
        'description': {
            'type': 'string',
            'blank': True
        },
        'description_attribution': {
            'type': sj_attribution,
            'required': False
        },
        'explicitType': {'type': 'string', 'required': False},
        'id': {
            'type': 'object',
            'properties': {
                'metajamCompactKey': {'type': 'string'},
                'artist': {'type': 'string'},
                'title': {'type': 'string'}
            }
        },
        'title': {'type': 'string'}
    }
}

sj_listen_now_station = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'highlight_color': {
            'type': 'string',
            'required': False
        },
        'id': {
            'type': 'object',
            'seeds': {
                'type': 'array',
                'items': {'type': sj_station_seed}
            }
        },
        'profile_image': {
            'type': 'object',
            'required': False,
            'url': {'type': 'string'}
        },
        'title': {'type': 'string'}
    }
}

sj_listen_now_item = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'kind': {'type': 'string'},
        'compositeArtRefs': {
            'type': 'array',
            'required': False,
            'items': {'type': sj_image}
        },
        'images': {
            'type': 'array',
            'items': {'type': sj_image},
            'required': False,
        },
        'suggestion_reason': {'type': 'string'},
        'suggestion_text': {'type': 'string'},
        'type': {'type': 'string'},
        'album': {
            'type': sj_listen_now_album,
            'required': False
        },
        'radio_station': {
            'type': sj_listen_now_station,
            'required': False
        }
    }
}

sj_podcast_genre = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'id': {'type': 'string'},
        'displayName': {'type': 'string'}
    }
}

sj_podcast_genre['properties']['subgroups'] = {
    'type': 'array',
    'required': False,
    'items': sj_podcast_genre
}

sj_podcast_episode = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'art': {
            'type': 'array',
            'required': False,
            'items': sj_image
        },
        'author': {
            'type': 'string',
            'required': False
        },
        'deleted': {
            'type': 'string',
            'required': False
        },
        'description': {
            'type': 'string',
            'required': False
        },
        'durationMillis': {'type': 'string'},
        'episodeId': {'type': 'string'},
        'explicitType': {'type': 'string'},
        'fileSize': {'type': 'string'},
        'playbackPositionMillis': {
            'type': 'string',
            'required': False
        },
        'publicationTimestampMillis': {
            'type': 'string',
            'required': False
        },
        'seriesId': {'type': 'string'},
        'seriesTitle': {'type': 'string'},
        'title': {'type': 'string'}
    },
}

sj_podcast_series = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'art': {
            'type': 'array',
            'required': False,
            'items': sj_image
        },
        'author': {'type': 'string'},
        'continuationToken': {
            'type': 'string',
            'required': False,
            'blank': True
        },
        'copyright': {
            'type': 'string',
            'required': False
        },
        'description': {
            'type': 'string',
            'required': False
        },
        'episodes': {
            'type': 'array',
            'required': False,
            'items': sj_podcast_episode
        },
        'explicitType': {'type': 'string'},
        'link': {
            'type': 'string',
            'required': False
        },
        'seriesId': {'type': 'string'},
        'title': {'type': 'string'},
        'totalNumEpisodes': {'type': 'integer'},
        'userPreferences': {
            'type': 'object',
            'required': False,
            'properties': {
                'autoDownload': {
                    'type': 'boolean',
                    'required': False
                },
                'notifyOnNewEpisode': {
                    'type': 'boolean',
                    'required': False
                },
                'subscribed': {'type': 'boolean'}
            }
        }
    }
}

sj_situation = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'description': {'type': 'string'},
        'id': {'type': 'string'},
        'imageUrl': {'type': 'string', 'required': False},
        'title': {'type': 'string'},
        'wideImageUrl': {'type': 'string', 'required': False},
        'stations': {'type': 'array',
                     'required': False,
                     'items': sj_station
                     }
    }
}

sj_situation['properties']['situations'] = {
    'type': 'array',
    'required': False,
    'items': sj_situation
}

sj_search_result = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'score': {'type': 'number', 'required': False},
        'type': {'type': 'string'},
        'best_result': {'type': 'boolean', 'required': False},
        'navigational_result': {'type': 'boolean', 'required': False},
        'navigational_confidence': {'type': 'number', 'required': False},
        'artist': sj_artist.copy(),
        'album': sj_album.copy(),
        'track': sj_track.copy(),
        'playlist': sj_playlist.copy(),
        'series': sj_podcast_series.copy(),
        'station': sj_station.copy(),
        'situation': sj_situation.copy(),
        'youtube_video': sj_video.copy()
    }
}

sj_search_result['properties']['artist']['required'] = False
sj_search_result['properties']['album']['required'] = False
sj_search_result['properties']['track']['required'] = False
sj_search_result['properties']['playlist']['required'] = False
sj_search_result['properties']['series']['required'] = False
sj_search_result['properties']['station']['required'] = False
sj_search_result['properties']['situation']['required'] = False
sj_search_result['properties']['youtube_video']['required'] = False


class McCall(Call):
    """Abstract base for mobile client calls."""

    required_auth = authtypes(oauth=True)

    # validictory schema for the response
    _res_schema = utils.NotImplementedField

    @classmethod
    def validate(cls, response, msg):
        """Use validictory and a static schema (stored in cls._res_schema)."""
        try:
            return validictory.validate(msg, cls._res_schema)
        except ValueError as e:
            raise_from(ValidationException(str(e)), e)

    @classmethod
    def check_success(cls, response, msg):
        # TODO not sure if this is still valid for mc
        pass

        # if 'success' in msg and not msg['success']:
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
            microseconds = -1
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


class McStreamCall(McCall):
    # this call will redirect to the mp3
    static_allow_redirects = False

    _s1 = bytes(base64.b64decode('VzeC4H4h+T2f0VI180nVX8x+Mb5HiTtGnKgH52Otj8ZCGDz9jRW'
                                 'yHb6QXK0JskSiOgzQfwTY5xgLLSdUSreaLVMsVVWfxfa8Rw=='))
    _s2 = bytes(base64.b64decode('ZAPnhUkYwQ6y5DdQxWThbvhJHN8msQ1rqJw0ggKdufQjelrKuiG'
                                 'GJI30aswkgCWTDyHkTGK9ynlqTkJ5L4CiGGUabGeo8M6JTQ=='))

    # bitwise and of _s1 and _s2 ascii, converted to string
    _key = ''.join([chr(c1 ^ c2) for (c1, c2) in zip(_s1, _s2)]).encode("ascii")

    @classmethod
    def get_signature(cls, item_id, salt=None):
        """Return a (sig, salt) pair for url signing."""

        if salt is None:
            salt = str(int(time.time() * 1000))

        mac = hmac.new(cls._key, item_id.encode("utf-8"), sha1)
        mac.update(salt.encode("utf-8"))
        sig = base64.urlsafe_b64encode(mac.digest())[:-1]

        return sig, salt

    @staticmethod
    def dynamic_headers(item_id, device_id, quality):
        return {'X-Device-ID': device_id}

    @classmethod
    def dynamic_params(cls, item_id, device_id, quality):
        sig, salt = cls.get_signature(item_id)

        params = {'opt': quality,
                  'net': 'mob',
                  'pt': 'e',
                  'slt': salt,
                  'sig': sig,
                  }
        if item_id.startswith(('T', 'D')):
            # Store track or podcast episode.
            params['mjck'] = item_id
        else:
            # Library track.
            params['songid'] = item_id

        return params

    @staticmethod
    def parse_response(response):
        return response.headers['location']  # ie where we were redirected

    @classmethod
    def validate(cls, response, msg):
        pass


class Config(McCall):
    static_method = 'GET'
    static_url = sj_url + 'config'

    item_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'key': {'type': 'string'},
            'value': {'type': 'string'}
        }
    }

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'data': {'type': 'object',
                     'entries': {'type': 'array', 'items': item_schema},
                     }
        }
    }


class Search(McCall):
    """Search for All Access tracks."""
    static_method = 'GET'
    static_url = sj_url + 'query'

    # The result types returned are requested in the `ct` parameter.
    # Free account search is restricted so may not contain hits for all result types.
    # 1: Song, 2: Artist, 3: Album, 4: Playlist, 6: Station, 7: Situation, 8: Video
    # 9: Podcast Series
    static_params = {'ct': '1,2,3,4,6,7,8,9'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'clusterOrder': {'type': 'array',
                             'items': {'type': 'string'},
                             'required': False},
            'entries': {'type': 'array',
                        'items': sj_search_result,
                        'required': False},
            'suggestedQuery': {'type': 'string', 'required': False}
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


class GetStreamUrl(McStreamCall):
    static_method = 'GET'
    static_url = sj_stream_url + 'mplay'


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

    @staticmethod
    def build_playlist_deletes(playlist_ids):
        # TODO can probably pull this up one
        """
        :param playlist_ids:
        """
        return [{'delete': id} for id in playlist_ids]

    @staticmethod
    def build_playlist_updates(pl_updates):
        """
        :param pl_updates: [{'id': '', name': '', 'description': '', 'public': ''}]
        """
        return [{'update': {
            'id': pl_update['id'],
            'name': pl_update['name'],
            'description': pl_update['description'],
            'shareState': pl_update['public']
        }} for pl_update in pl_updates]

    @staticmethod
    def build_playlist_adds(pl_descriptions):
        """
        :param pl_descriptions: [{'name': '', 'description': '','public': ''}]
        """

        return [{'create': {
            'creationTimestamp': '-1',
            'deleted': False,
            'lastModifiedTimestamp': '0',
            'name': pl_desc['name'],
            'description': pl_desc['description'],
            'type': 'USER_GENERATED',
            'shareState': pl_desc['public'],
        }} for pl_desc in pl_descriptions]


class BatchMutatePlaylistEntries(McBatchMutateCall):
    filter_text = 'plentries'
    item_schema = sj_plentry

    static_method = 'POST'
    static_url = sj_url + 'plentriesbatch'

    @staticmethod
    def build_plentry_deletes(entry_ids):
        """
        :param entry_ids:
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
        keys_to_keep = {'clientId', 'creationTimestamp', 'deleted', 'id', 'lastModifiedTimestamp',
                        'playlistId', 'source', 'trackId'}

        for key in list(mutation.keys()):
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
        :param playlist_id:
        :param song_ids:
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


class GetDeviceManagementInfo(McCall):
    """Get registered device information."""

    static_method = 'GET'
    static_url = sj_url + "devicemanagementinfo"
    static_params = {'alt': 'json'}

    _device_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'id': {'type': 'string'},
            'friendlyName': {'type': 'string', 'blank': True},
            'type': {'type': 'string'},
            'lastAccessedTimeMs': {'type': 'integer'},

            # only for mobile devices
            'smartPhone': {'type': 'boolean', 'required': False},
        }
    }

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'data': {'type': 'object',
                     'items': {'type': 'array', 'items': _device_schema},
                     'required': False,
                     },
        },
    }


class DeauthDevice(McCall):
    """Deauthorize a device from devicemanagementinfo."""

    static_method = 'DELETE'
    static_url = sj_url + "devicemanagementinfo"

    @staticmethod
    def dynamic_params(device_id):
        return {'delete-id': device_id}


class ListPromotedTracks(McListCall):
    item_schema = sj_track
    filter_text = 'tracks'

    static_method = 'POST'
    static_url = sj_url + 'ephemeral/top'


class ListListenNowItems(McCall):
    static_method = 'GET'
    static_url = sj_url + "listennow/getlistennowitems"
    static_params = {'alt': 'json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'listennow_items': {
                'type': 'array',
                'items': {'type': sj_listen_now_item}
            }
        }
    }

    @staticmethod
    def filter_response(msg):
        filtered = copy.deepcopy(msg)
        if 'listennow_items' in filtered:
            filtered['listennow_items'] = \
                    ["<%s listennow_items>" % len(filtered['listennow_items'])]


class ListListenNowSituations(McCall):
    static_method = 'POST'
    static_url = sj_url + 'listennow/situations'
    static_headers = {'Content-Type': 'application/json'}
    static_params = {'alt': 'json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'distilledContextWrapper': {'type': 'object',
                                        'distilledContextToken': {'type': 'string'},
                                        'required': False},
            'primaryHeader': {'type': 'string'},
            'subHeader': {'type': 'string'},
            'situations': {'type': 'array',
                           'items': sj_situation,
                           },
        },
    }

    @classmethod
    def dynamic_data(cls):
        tz_offset = calendar.timegm(time.localtime()) - calendar.timegm(time.gmtime())

        return json.dumps({
            'requestSignals': {'timeZoneOffsetSecs': tz_offset}
        })

    @staticmethod
    def filter_response(msg):
        filtered = copy.deepcopy(msg)
        if 'situations' in filtered.get('data', {}):
            filtered['data']['situations'] = \
                    ["<%s situations>" % len(filtered['data']['situations'])]

        return filtered


class GetBrowsePodcastHierarchy(McCall):
    static_method = 'GET'
    static_url = sj_url + 'podcast/browsehierarchy'
    static_params = {'alt': 'json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'groups': {
                'type': 'array',
                'required': False,  # Only on errors
                'items': sj_podcast_genre
            }
        }
    }


class ListBrowsePodcastSeries(McCall):
    static_method = 'GET'
    static_url = sj_url + 'podcast/browse'
    static_params = {'alt': 'json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'series': {
                'type': 'array',
                'items': {'type': sj_podcast_series}
            }
        }
    }

    @classmethod
    def dynamic_params(cls, id=None):
        return {'id': id}

    @staticmethod
    def filter_response(msg):
        filtered = copy.deepcopy(msg)
        if 'series' in filtered:
            filtered['series'] = \
                    ["<%s podcasts>" % len(filtered['series'])]


class BatchMutatePodcastSeries(McBatchMutateCall):
    static_method = 'POST'
    static_url = sj_url + 'podcastseries/batchmutate'

    @staticmethod
    def build_podcast_updates(updates):
        """
        :param updates:
          [
            {'seriesId': '', 'subscribed': '', 'userPreferences': {
             'notifyOnNewEpisode': '', 'subscrubed': ''}}...
          ]
        """

        return [{'update': update} for update in updates]


# The podcastseries and podcastepisode list calls are strange in that they require a device
# ID and pass updated-min, max-results, and start-token as params.
# The start-token param is required, even if not given, to get a result for more than one
# call in a session.
class ListPodcastSeries(McListCall):
    item_schema = sj_podcast_series
    filter_text = 'podcast series'

    static_method = 'GET'
    static_url = sj_url + 'podcastseries'

    @staticmethod
    def dynamic_headers(device_id, updated_after=None, start_token=None, max_results=None):
        return {'X-Device-ID': device_id}

    @classmethod
    def dynamic_params(cls, device_id=None, updated_after=None, start_token=None, max_results=None):
        params = {}

        if updated_after is None:
            microseconds = -1
        else:
            microseconds = utils.datetime_to_microseconds(updated_after)

        params['updated-min'] = microseconds

        params['start-token'] = start_token

        if max_results is not None:
            params['max-results'] = str(max_results)

        return params

    @classmethod
    def dynamic_data(cls, device_id=None, updated_after=None, start_token=None, max_results=None):
        pass


# The podcastseries and podcastepisode list calls are strange in that they require a device
# ID and pass updated-min, max-results, and start-token as params.
# The start-token param is required, even if not given, to get a result for more than one
# call in a session.
class ListPodcastEpisodes(McListCall):
    item_schema = sj_podcast_episode
    filter_text = 'podcast episodes'

    static_method = 'GET'
    static_url = sj_url + 'podcastepisode'

    @staticmethod
    def dynamic_headers(device_id, updated_after=None, start_token=None, max_results=None):
        return {'X-Device-ID': device_id}

    @classmethod
    def dynamic_params(cls, device_id=None, updated_after=None, start_token=None, max_results=None):
        params = {}

        if updated_after is None:
            microseconds = -1
        else:
            microseconds = utils.datetime_to_microseconds(updated_after)

        params['updated-min'] = microseconds

        params['start-token'] = start_token

        if max_results is not None:
            params['max-results'] = str(max_results)

        return params

    @classmethod
    def dynamic_data(cls, device_id=None, updated_after=None, start_token=None, max_results=None):
        pass


class GetPodcastEpisodeStreamUrl(McStreamCall):
    static_method = 'GET'
    static_url = sj_stream_url + 'fplay'


class ListStations(McListCall):
    item_schema = sj_station
    filter_text = 'stations'

    static_method = 'POST'
    static_url = sj_url + 'radio/station'


class ListStationTracks(McCall):
    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'data': {'type': 'object',
                     'stations': {'type': 'array', 'items': sj_station},
                     'required': False,
                     },
        },
    }

    static_headers = {'Content-Type': 'application/json'}
    static_params = {'alt': 'json', 'include-tracks': 'true'}
    static_method = 'POST'
    static_url = sj_url + 'radio/stationfeed'

    @staticmethod
    def dynamic_data(station_id, num_entries, recently_played):
        """
        :param station_id:
        :param num_entries: maximum number of tracks to return
        :param recently_played: a list of...song ids? never seen an example
        """
        # TODO
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
        if 'stations' in filtered.get('data', {}):
            filtered['data']['stations'] = \
                    ["<%s stations>" % len(filtered['data']['stations'])]
        return filtered


class BatchMutateStations(McBatchMutateCall):
    static_method = 'POST'
    static_url = sj_url + 'radio/editstation'

    @staticmethod
    def build_deletes(station_ids):
        """
        :param station_ids:
        """
        return [{'delete': id, 'includeFeed': False, 'numEntries': 0}
                for id in station_ids]

    @staticmethod
    def build_add(name, seed, include_tracks, num_tracks, recent_datetime=None):
        """
        :param name: the title
        :param seed: a dict {'itemId': id, 'seedType': int}
        :param include_tracks: if True, return `num_tracks` tracks in the response
        :param num_tracks:
        :param recent_datetime: purpose unknown. defaults to now.
        """

        if recent_datetime is None:
            recent_datetime = datetime.now()

        recent_timestamp = utils.datetime_to_microseconds(recent_datetime)

        return {
            "createOrGet": {
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
        :param track_ids:
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
            if key in track_dict:
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


class GetPodcastSeries(McCall):
    static_method = 'GET'
    static_url = sj_url + 'podcast/fetchseries'
    static_headers = {'Content-Type': 'application/json'}
    static_params = {'alt': 'json'}

    _res_schema = sj_podcast_series

    @staticmethod
    def dynamic_params(podcast_series_id, num_episodes):
        return {
            'nid': podcast_series_id,
            'num': num_episodes}


class GetPodcastEpisode(McCall):
    static_method = 'GET'
    static_url = sj_url + 'podcast/fetchepisode'
    static_headers = {'Content-Type': 'application/json'}
    static_params = {'alt': 'json'}

    _res_schema = sj_podcast_episode

    @staticmethod
    def dynamic_params(podcast_episode_id):
        return {'nid': podcast_episode_id}


class GetStoreTrack(McCall):
    # TODO does this accept library ids, too?
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

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'kind': {'type': 'string'},
            'genres': {
                'type': 'array',
                'items': sj_genre,
                'required': False,  # only on errors
            }
        }
    }

    @staticmethod
    def dynamic_params(parent_genre_id):
        return {'parent-genre': parent_genre_id}


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


class IncrementPlayCount(McCall):
    static_method = 'POST'
    static_url = sj_url + 'trackstats'
    static_params = {'alt': 'json'}
    static_headers = {'Content-Type': 'application/json'}

    _res_schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'responses': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'id': {'type': 'string',
                               'required': False},  # not provided for AA tracks?
                        'response_code': {'type': 'string'},
                    }
                }
            }
        }
    }

    @staticmethod
    def dynamic_data(sid, plays, playtime):
        # TODO this can support multiple tracks at a time

        play_timestamp = utils.datetime_to_microseconds(playtime)
        event = {
            'context_type': 1,
            'event_timestamp_micros': str(play_timestamp),
            'event_type': 2,
            # This can also send a context_id which is the album/artist id
            # the song was found from.
        }

        return json.dumps({'track_stats': [{
            'id': sid,
            'incremental_plays': plays,
            'last_play_time_millis': str(play_timestamp // 1000),
            'type': 2 if sid.startswith('T') else 1,
            'track_events': [event] * plays,
        }]})
