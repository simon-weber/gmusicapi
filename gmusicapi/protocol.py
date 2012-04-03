#!/usr/bin/env python

# Copyright (c) 2012, Simon Weber
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of the contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""The protocol layer is a one-to-one mapping of calls to Google Music."""


import string
import os
import random
from collections import namedtuple
import exceptions
from uuid import getnode as getmac
from socket import gethostname
import base64
import hashlib

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

import metadata_pb2
from utils import utils
from utils.apilogging import LogController #TODO this is a hack


class WC_Call(object):
    """An abstract class to hold the protocol for a web client call."""
    
    _base_url = 'https://play.google.com/music/'
    
    #Added to the url after _base_url. Most calls are made to /music/services/<call name>
    #Expected to end with a forward slash.
    _suburl = 'services/'

    #Should the response to this call be logged?
    #The request is always logged, currently.
    gets_logged = True

    #Do we need to be logged in before making the call?
    requires_login = True
    
    #Most calls will send u=0 and the xt cookie in the querystring.
    @classmethod
    def build_url(cls, query_string=None):
        """Return the url to make the call at."""

        #Most calls send u=0 and xt=<cookie value>
        qstring = '?u=0&xt={0}'.format(query_string['xt'])

        return cls._base_url + cls._suburl + cls.__name__ + qstring

    #Calls all have different request and response formats.
    @staticmethod
    def build_transaction():
        """Return a tuple of (filled request, response schemas)."""
        raise NotImplementedError


class _DefinesNameMetaclass(type):
    """A metaclass to create a 'name' attribute for _Metadata that respects
    any necessary name mangling."""

    def __new__(cls, name, bases, dct):
        dct['name'] = name.split('gm_')[-1]
        return super(_DefinesNameMetaclass, cls).__new__(cls, name, bases, dct)

class _Metadata_Expectation(object):
    """An abstract class to hold expectations for a particular metadata entry.

    Its default values are correct for most entries."""

    __metaclass__ = _DefinesNameMetaclass

    #Most keys have the same expectations.
    #In most cases, overriding val_type is all that is needed.

    #The validictory type we expect to see.
    #Possible values are:
        # "string" - str and unicode objects
        # "integer" - ints
        # "number" - ints and floats
        # "boolean" - bools
        # "object" - dicts
        # "array" - lists and tuples
        # "null" - None
        # "any" - any type is acceptable
    val_type = "string"

    #Can we change the value?
    mutable = True

    #A list of allowed values, or None for no restriction.
    allowed_values = None
    
    #Can the value change without us changing it?
    volatile = False

    #The name of the Metadata class our value depends on, or None.
    depends_on = None 

    #A function that takes the dependent key's value
    # and returns our own. Only implemented for dependent keys.
    @staticmethod
    def dependent_transformation(value):
        raise NotImplementedError

    #Is this entry optional?
    optional = False

    @classmethod
    def get_schema(cls):
        """Return the schema to validate this class with."""
        schema = {}
        schema["type"] = cls.val_type
        if cls.val_type == "string":
            schema["blank"] = True #Allow blank strings.
        if cls.optional:
            schema["required"] = False

        return schema
    
class UnknownExpectation(_Metadata_Expectation):
    """A flexible expectation intended to be given when we know nothing about a key."""
    val_type = "any"
    mutable = False
    

class Metadata_Expectations(object):
    """Holds expectations about metadata."""

    #Class names are GM response keys.
    #Clashes are prefixed with a gm_ (eg gm_type).

    @classmethod
    def get_expectation(cls, key, warn_on_unknown=True):
        """Get the Expectation associated with the given key name.
        If no Expectation exists for that name, an immutable Expectation of any type is returned."""

        mangle = False
        if not hasattr(cls,key):
            mangle = True

        expt_name = "gm_" + key if mangle else key

        try:
            expt = getattr(cls,expt_name)
            if not issubclass(expt, _Metadata_Expectation):
                raise TypeError
            return expt
        except (AttributeError, TypeError):
            if warn_on_unknown: LogController.get_logger("get_expectation").warning("unknown metadata type '%s'", key)

            return UnknownExpectation


    @classmethod
    def get_all_expectations(cls):
        """Return a dictionary mapping key name to Expectation for all known keys."""

        expts = {}

        for name in dir(cls):
            member = cls.get_expectation(name, warn_on_unknown=False)
            if member is not UnknownExpectation: expts[member.name]=member
        
        return expts

    #Mutable metadata:
    class rating(_Metadata_Expectation):
        val_type = "integer"
        #0 = no thumb
        #1 = down thumb
        #5 = up thumb
        allowed_values = (0, 1, 5) 

    #strings (the default value for val_type
    class composer(_Metadata_Expectation):
        pass
    class album(_Metadata_Expectation):
        pass
    class albumArtist(_Metadata_Expectation):
        pass
    class genre(_Metadata_Expectation):
        pass
    class name(_Metadata_Expectation):
        pass
    class artist(_Metadata_Expectation):
        pass

    #integers
    class disc(_Metadata_Expectation):
        optional = True
        val_type = "integer"
    class year(_Metadata_Expectation):
        optional = True
        val_type = "integer"
    class track(_Metadata_Expectation):
        optional = True
        val_type = "integer"
    class totalTracks(_Metadata_Expectation):
        optional = True
        val_type = "integer"
    class playCount(_Metadata_Expectation):
        val_type = "integer"
    class totalDiscs(_Metadata_Expectation):
        optional = True
        val_type = "integer"



    #Immutable metadata:
    class durationMillis(_Metadata_Expectation):
        mutable = False #you can change this, but probably don't want to.
        val_type = "integer"
    class comment(_Metadata_Expectation):
        mutable = False
    class id(_Metadata_Expectation):
        mutable = False
    class deleted(_Metadata_Expectation):
        mutable = False
        val_type = "boolean"
    class creationDate(_Metadata_Expectation):
        mutable = False
        val_type = "integer"
    class albumArtUrl(_Metadata_Expectation):
        mutable = False
        optional = True #only seen when there is album art.
    class gm_type(_Metadata_Expectation):
        mutable = False
        val_type = "integer"
    class beatsPerMinute(_Metadata_Expectation):
        mutable = False
        val_type = "integer"
    class url(_Metadata_Expectation):
        mutable = False
    class playlistEntryId(_Metadata_Expectation):
        mutable = False
        optional = True #only seen when songs are in the context of a playlist.
    class subjectToCuration(_Metadata_Expectation):
        mutable = False
        val_type = "boolean"
    class metajamId(_Metadata_Expectation):
        mutable = False
        
    
    #Dependent metadata:
    class title(_Metadata_Expectation):
        depends_on = "name"
        
        @staticmethod
        def dependent_transformation(other_value):
            return other_value #nothing changes

    class titleNorm(_Metadata_Expectation):
        depends_on = "name"

        @staticmethod
        def dependent_transformation(other_value):
            return string.lower(other_value)

    class albumArtistNorm(_Metadata_Expectation):
        depends_on = "albumArtist"

        @staticmethod
        def dependent_transformation(other_value):
            return string.lower(other_value)

    class albumNorm(_Metadata_Expectation):
        depends_on = "album"

        @staticmethod
        def dependent_transformation(other_value):
            return string.lower(other_value)    

    class artistNorm(_Metadata_Expectation):
        depends_on = "artist"

        @staticmethod
        def dependent_transformation(other_value):
            return string.lower(other_value)

    
    #Metadata we have no control over:
    class lastPlayed(_Metadata_Expectation):
        mutable = False
        volatile = True
        val_type = "integer"

    
class WC_Protocol(object):
    """Holds the protocol for all suppported web client interactions."""

    #Shared response schemas.
    song_schema = {"type": "object",

                   #filled out next
                   "properties":{},

                   #don't allow metadata not in expectations
                   "additionalProperties":False} 

    for name, expt in Metadata_Expectations.get_all_expectations().items():
        song_schema["properties"][name] = expt.get_schema()

    song_array = {"type":"array",
                  "items": song_schema}        

    pl_schema = {"type":"object",
                 "properties":{
                     "continuation":{"type":"boolean"},
                     "playlist":song_array,
                     "playlistId":{"type":"string"},
                     "unavailableTrackCount":{"type":"integer"},
                     "title":{"type":"string", "required":False}, #not seen when loading a single playlist
                     "continuationToken":{"type":"string", "required":False}
                     },
                 "additionalProperties":False
                 }

    pl_array = {"type":"array",
                "items":pl_schema}

    #All api calls are named as they appear in the request.

    class addplaylist(WC_Call):
        """Creates a new playlist."""

        @staticmethod
        def build_transaction(title): 
            """
            :param title: the title of the playlist to create.
            """
            
            req = {"title": title}

            #{"id":"<new playlist id>","title":"<name>","success":true}
            res = {"type": "object",
                   "properties":{
                       "id": {"type":"string"},
                       "title": {"type": "string"},
                       "success": {"type": "boolean"},
                        },
                   "additionalProperties":False}

            return (req, res)


    class addtoplaylist(WC_Call):
        """Adds songs to a playlist."""

        @staticmethod
        def build_transaction(playlist_id, song_ids):
            """
            :param playlist_id: id of the playlist to add to.
            :param song_ids: a list of song ids
            """

            req = {"playlistId": playlist_id, "songIds": song_ids} 
                                      
            #{"playlistId":"<same as above>","songIds":[{"playlistEntryId":"<new id>","songId":"<same as above>"}]}
            res = {"type": "object",
                      "properties":{
                        "playlistId": {"type":"string"},
                        "songIds":{
                            "type":"array",
                            "items":{
                                "type":"object",
                                "properties":{
                                    "songId":{"type":"string"},
                                    "playlistEntryId":{"type":"string"}
                                    }
                                }
                            }
                        },
                   "additionalProperties":False
                   }
                   
                    
            return (req, res)


    class modifyplaylist(WC_Call):
        """Changes the name of a playlist."""

        @staticmethod
        def build_transaction(playlist_id, new_name):
            """
            :param playlist_id: id of the playlist to rename.
            :param new_title: desired title.
            """
        
            req = {"playlistId": playlist_id, "playlistName": new_name}

            #{}
            res = {"type": "object",
                   "properties":{},
                   "additionalProperties": False}

            return (req, res)

    class changeplaylistorder(WC_Call):
        """Reorders songs currently in a playlist."""
        
        @staticmethod
        def build_transaction(playlist_id, song_ids_moving, entry_ids_moving, 
                              after_entry_id="", before_entry_id=""):
            """
            :param playlist_id: id of the playlist getting reordered
            :param song_ids_moving: a list of consecutive song ids to move, corresponds with entry_ids_moving
            :param entry_ids_moving: a list of consecutive entry ids to move, corresponds with song_ids_moving
            :param after_entry_id: the entry id to place these songs after. Empty string for first position.
            :param before_entry_id: the entry id to place these songs before. Empty string for last position.
            """

            req = {"playlistId": playlist_id,
                   "movedSongIds": song_ids_moving,
                   "movedEntryIds": entry_ids_moving,
                   "afterEntryId": after_entry_id,
                   "beforeEntryId": before_entry_id}

            res = {"type": "object",
                   "properties":{
                       "afterEntryId": {"type":"string", "blank":True},
                       "playlistId": {"type":"string"},
                       "movedSongIds":{
                           "type":"array",
                           "items": {"type":"string"}
                           }
                       },
                   "additionalProperties":False
                   }
 
            return (req, res)
    
    class deleteplaylist(WC_Call):
        """Deletes a playlist."""

        @staticmethod
        def build_transaction(playlist_id):
            """
            :param playlist_id: id of the playlist to delete.
            """
            
            req = {"id": playlist_id}

            #{"deleteId": "<id>"}
            res = {"type": "object",
                   "properties":{
                       "deleteId": {"type":"string"}
                       },
                   "additionalProperties":False
                   }
                     
            return (req, res)
        

    class deletesong(WC_Call):
        """Delete a song from the library or a playlist."""

        @staticmethod
        def build_transaction(song_ids, entry_ids = [""], playlist_id = "all"):
            """
            :param song_ids: a list of song ids
            :param entry_ids: for deleting from playlists
            :param list_id: for deleteing from playlists
            """
            req = {"songIds": song_ids, "entryIds":entry_ids, "listId": playlist_id}

            #{"listId":"<playlistId>","deleteIds":["<id1>"]}
            #playlistId might be "all" - meaning deletion from the library
            res = {"type": "object",
                   "properties":{
                       "listId": {"type":"string"},
                       "deleteIds":
                           {"type": "array",
                            "items": {"type": "string"}
                            }
                       },
                   "additionalProperties":False
                   }
            return (req, res)

    class loadalltracks(WC_Call):
        """Loads tracks from the library.
        Since libraries can have many tracks, GM gives them back in chunks.
        Chunks will send a continuation token to get the next chunk.
        The first request needs no continuation token.
        The last response will not send a token.
        """

        gets_logged = False

        @staticmethod
        def build_transaction(cont_token = None):
            """:param cont_token: (optional) token to get the next library chunk."""
            if not cont_token:
                req = {}
            else:
                req = {"continuationToken": cont_token}


            res = {"type": "object",
                   "properties":{
                      "continuation": {"type":"boolean"},
                      "differentialUpdate": {"type":"boolean"},
                      "playlistId": {"type": "string"},
                      "requestTime": {"type": "integer"},
                      "playlist": WC_Protocol.song_array
                      },
                   "additionalProperties":{
                       "continuationToken": {"type":"string"}}
                   }

            return (req, res)

    class loadplaylist(WC_Call):
        """Loads tracks from a playlist.
        Tracks include playlistEntryIds.
        """

        gets_logged = False

        @staticmethod
        def build_transaction(playlist_id):

            #Special call with empty body loads all instant/user playlists (but not auto).
            if playlist_id == "all":
                req = {}
                res = {"type":"object",
                       "properties":{
                           "magicPlaylists": WC_Protocol.pl_array,
                           "playlists": WC_Protocol.pl_array,
                           },
                       "additionalProperties":False
                       }
                        
            else:
                req = {"id": playlist_id}
                res = WC_Protocol.pl_schema
                           
            return (req, res)
        
    
    class modifyentries(WC_Call):
        """Edit the metadata of songs."""

        @classmethod
        def build_transaction(cls, songs):
            """:param songs: a list of dictionary representations of songs."""
        
            #Warn about metadata changes that may cause problems.
            #If you change the interface in api, you can warn about changing bad categories, too.
            #Something like safelychange(song, entries) where entries are only those you want to change.

            for song in songs:
                for key in song:
                    allowed_values = Metadata_Expectations.get_expectation(key).allowed_values
                    if allowed_values and song[key] not in allowed_values:
                        LogController.get_logger("modifyentries").warning("setting key {0} to unallowed value {1} for id {2}. Check metadata expectations in protocol.py".format(key, song[key], song["id"]))
                        

            req = {"entries": songs}

            res = {"type": "object",
                   "properties":{
                       "success": {"type":"boolean"},
                       "songs":WC_Protocol.song_array
                       },
                   "additionalProperties":False
                   }
            return (req, res)

    class multidownload(WC_Call):
        """Get download links and counts for songs."""

        @staticmethod
        def build_transaction(song_ids):
            """:param song_ids: a list of song ids."""
            req = {"songIds": song_ids}

            #This hasn't been tested yet.
            res = {"type":"object",
                   "properties":{
                       "downloadCounts":{
                           "type":"array",
                           "items":{
                               "type":"object",
                               "properties":{
                                   "id":{"type":"integer"}
                                   }
                               }
                           },
                       "url":{"type":"string"}
                       },
                   "additionalProperties":False
                   }
            return (req, res)

    class play(WC_Call):
        """Get a url that holds a file to stream."""

        #play is strange, it doesn't use music/services/play, just music/play
        _suburl = ''

        @classmethod
        def build_url(cls, query_string):
            #xt is not sent for play.
            #Instead, the songid is sent in the querystring, along with pt=e, for unknown reasons.
            qstring = '?u=0&pt=e'
            return cls._base_url + cls._suburl + cls.__name__ + qstring

        @staticmethod
        def build_transaction():
            req = None #body is completely empty.
            res = {"type":"object",
                   "properties":{
                       "url":{"type":"string"}
                       },
                   "additionalProperties":False
                   }
            res = None
            return (req, res)
        

    class search(WC_Call):
        """Search for songs, artists and albums.
        GM ignores punctuation."""
    
        @staticmethod
        def build_transaction(query):
            req = {"q": query}

            res = {"type":"object",
                   "properties":{
                       "results":{
                           "type":"object",
                           "properties":{
                               "artists": WC_Protocol.song_array,
                               "songs": WC_Protocol.song_array,
                               #albums are different; they don't return songs, but albums.
                               "albums":{
                                   "type":"array",
                                   "items":{
                                       "type":"object",
                                       "properties":{
                                           "artistName":{"type":"string", "blank":True},
                                           "imageUrl":{"type":"string", "required":False},
                                           "albumArtist":{"type":"string", "blank":True},
                                           "albumName":{"type":"string"},
                                           }
                                       }
                                   }       
                               }
                           }
                       },
                   "additionalProperties":False
                   }
                                  
                    
            return (req, res)


class MM_Protocol(object):

    def __init__(self):

        #Mac and hostname are used to identify our client.
        self.mac = hex(getmac())[2:-1]
        self.mac = ':'.join([self.mac[x:x+2] for x in range(0, 10, 2)])

        hostname = gethostname()

        #Pre-filled protobuff instances.
        #These are used to fill in new instances.
        #Named scheme is '[protocol name]_filled'

        self.upload_auth_filled = metadata_pb2.UploadAuth()
        self.upload_auth_filled.address = self.mac
        self.upload_auth_filled.hostname = hostname

        self.client_state_filled = metadata_pb2.ClientState()
        self.client_state_filled.address = self.mac

        self.upload_auth_response_filled = metadata_pb2.UploadAuthResponse()

        self.client_state_response_filled = metadata_pb2.ClientStateResponse()

        self.metadata_request_filled = metadata_pb2.MetadataRequest()
        self.metadata_request_filled.address = self.mac

        self.metadata_response_filled = metadata_pb2.MetadataResponse()
        
        #Service name mapped to url.
        self.pb_services = {
            "upload_auth" : 'upauth',
            "client_state": 'clientstate',
            "metadata": 'metadata?version=1'}

    
    def make_pb(self, pb_name):
        """Makes a new instance of a protobuff protocol.
        Client identifying fields are pre-filled.
        
        :pb_name: the name of the protocol
        """
        
        #eg: for "upload_auth", pb gets metadata_pb2.UploadAuth()
        pb = getattr(metadata_pb2,
                     utils.to_camel_case(pb_name))()

        #copy prefilled fields
        pb.CopyFrom(getattr(self, pb_name + "_filled"))

        return pb


    def make_metadata_request(self, filenames):
        """Returns (Metadata protobuff, dictionary mapping ClientId to filename) for the given mp3s."""

        filemap = {} #this maps a generated ClientID with a filename

        metadata = self.make_pb("metadata_request")

        for filename in filenames:

            if not filename.split(".")[-1] == "mp3":
                self.log.error("Cannot upload '%s' because it is not an mp3.")

            track = metadata.tracks.add()

            #Eventually pull this to supported_filetypes
            audio = MP3(filename, ID3 = EasyID3)


            #The id is a 22 char hash of the file. It is found by:
            # stripping tags
            # getting an md5 sum
            # converting sum to base64
            # removing trailing ===

            #My implementation is _not_ the same hash the music manager will send;
            # they strip tags first. But files are differentiated across accounts,
            # so this shouldn't cause problems.

            #This will reupload files if their tags change.
            
            with open(filename, mode="rb") as f:
                file_contents = f.read()
            
            h = hashlib.md5(file_contents).digest()
            h = base64.encodestring(h)[:-3]
            id = h

            filemap[id] = filename
            track.id = id

            filesize = os.path.getsize(filename)

            track.fileSize = filesize

            track.bitrate = audio.info.bitrate / 1000
            track.duration = int(audio.info.length * 1000)

            #GM requires at least a title.
            track.title = audio["title"][0] if "title" in audio else filename.split(r'/')[-1]

            if "album" in audio: track.album = audio["album"][0]
            if "artist" in audio: track.artist = audio["artist"][0]
            if "composer" in audio: track.composer = audio["composer"][0]

            #albumartist is 'performer' according to this guy: 
            # https://github.com/plexinc-plugins/Scanners.bundle/commit/95cc0b9eeb7fa8fa77c36ffcf0ec51644a927700

            if "performer" in audio: track.albumArtist = audio["performer"][0]
            if "genre" in audio: track.genre = audio["genre"][0]
            if "date" in audio: track.year = int(audio["date"][0].split("-")[0]) #this looks like an assumption
            if "bpm" in audio: track.beatsPerMinute = int(audio["bpm"][0])

            #think these are assumptions:
            if "tracknumber" in audio: 
                tracknumber = audio["tracknumber"][0].split("/")
                track.track = int(tracknumber[0])
                if len(tracknumber) == 2:
                    track.totalTracks = int(tracknumber[1])

            if "discnumber" in audio:
                discnumber = audio["discnumber"][0].split("/")
                track.disc = int(discnumber[0])
                if len(discnumber) == 2:
                    track.totalDiscs = int(discnumber[1])

        return (metadata, filemap)


    def make_upload_session_requests(self, filemap, server_response):
        """Returns a list of (filename, serverid, json) to request upload sessions.
        If no sessions are created, returns an empty list.
        
        :param filemap: maps ClientID to filename
        :param server_response: the MetadataResponse that preceded these requests
        """

        sessions = []

        for upload in server_response.response.uploads:
            filename = filemap[upload.id]
            audio = MP3(filename, ID3 = EasyID3)
            upload_title = audio["title"] if "title" in audio else filename.split(r'/')[-1]

            inlined = {
                "title": "jumper-uploader-title-42",
                "ClientId": upload.id,
                "ClientTotalSongCount": len(server_response.response.uploads),
                "CurrentTotalUploadedCount": "0",
                "CurrentUploadingTrack": upload_title,
                "ServerId": upload.serverId,
                "SyncNow": "true",
                "TrackBitRate": audio.info.bitrate,
                "TrackDoNotRematch": "false",
                "UploaderId": self.mac
            }
            payload = {
              "clientId": "Jumper Uploader",
              "createSessionRequest": {
                "fields": [
                    {
                        "external": {
                      "filename": os.path.basename(filename),
                      "name": os.path.abspath(filename),
                      "put": {},
                      "size": os.path.getsize(filename)
                    }
                    }
                ]
              },
              "protocolVersion": "0.8"
            }
            for key in inlined:
                payload['createSessionRequest']['fields'].append({
                    "inlined": {
                        "content": str(inlined[key]),
                        "name": key
                    }
                })

            sessions.append((filename, upload.serverId, payload))

        return sessions
