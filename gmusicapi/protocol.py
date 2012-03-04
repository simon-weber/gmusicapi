#!/usr/bin/env python

#Copyright 2012 Simon Weber.

#This file is part of gmusicapi - the Unofficial Google Music API.

#Gmusicapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmusicapi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with gmusicapi.  If not, see <http://www.gnu.org/licenses/>.

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
#terse name; this is used all over.
from utils import type_to_schema as t2s 
from utils.apilogging import UsesLog


supported_filetypes = ("mp3")

class UnsupportedFiletype(exceptions.Exception):
    pass

class WC_Call:
    """An abstract class to hold the protocol for a web client call."""
    
    _base_url = 'https://music.google.com/music/'
    
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

class _Metadata():
    """An abstract class to hold expectations for a particular metadata entry."""

    #Can we change the value?
    mutable = True
    
    #Can the value change without us changing it?
    volatile = False

    #Is the value determined from another key's value? 
    dependent = False
    #The key we depend on.
    dependent_key = None 
    #A function that takes the dependent key's value
    # and returns our own.
    @classmethod
    def dependent_transformation(cls, value):
        raise NotImplementedError

    #Is this entry optional?
    optional = False
    
    
class WC_Protocol:
    """Holds the protocol for all suppported web client interactions."""


    #Metadata expectations:

    #These five dictionaries define all the metadata entries we know about,
    # dividing them up based on what kind of control we have over their values.

    #Entries that accept a limited set of values.
    #Metadata name -> list of values it can hold.
    #This needs to be investigated and fleshed out.
    limited_md = {
        "rating" : (0, 1, 5)
    }

    #Entries we have control of, and can change.
    #metadata name -> type
    # (this is just shorthand for building schemas,
    #  and may not be the type we get back)
    mutable_md = {'rating': int,
                  'disc':int,
                  'composer':str,
                  'year':int,
                  'album':str,
                  'albumArtist':str,
                  'track':int,
                  'totalTracks':int,
                  'genre':str,
                  'playCount':int,
                  'name':str,
                  'artist':str,
                  'totalDiscs':int,
                  'durationMillis':int}

    #Entries we cannot change.
    frozen_md = {'comment':str,
                 'id':str,
                 'deleted': bool,
                 'creationDate':int,
                 'albumArtUrl':str, #only present when there is album art
                 'type':int,
                 'beatsPerMinute':int,
                 'url':str,
                 'entryId':str #only present when the song is loaded from a playlist
                 }

    #Metadata whose value depends on another's.
    #Name -> ('depeds on', transformation)
    dependent_md = {
        'title': ('name', lambda x : x),
        'titleNorm': ('name', string.lower),
        'albumArtistNorm': ('albumArtist', string.lower),
        'albumNorm': ('album', string.lower),
        'artistNorm': ('artist', string.lower)}

    #Metadata that the server has complete control of.
    #We cannot change the value, and the server may change it without us knowing.
    server_md = {'lastPlayed':int} #likely an accessed timestamp in actuality?

    #Metadata that isn't always in a song.
    optional_md = set(("albumArtUrl",))

    #Shared response schemas.
    playlist_entry_schema = {"type": "object",
                             "properties":{
                               "playlistEntryId": {"type":"string"},
                               "songId": {"type":"string"}}
                             }


    #The song schema is built automatically from the above metadata expectations.

    #List of (md dictionary, transformation) pairs.
    #Transformations take a pair from the dictionary and return the expected type.
    direct_map = lambda name, ptype: ptype
    val_map = lambda name, vals: type(vals[0]) #assumes all possible values are of same type
    dependent_map = lambda name, depend_info: depend_info[0] #assumes the dependent key is already added.
    

    md_schema_transformations = (
        (mutable_md, name_type),
        (frozen_md, name_type),
        (server_md, name_type),
        (limited_md, name_vals),
        
        )

    md_prop_schema = {} #metadata properties


    

    for name, vals in limited_md.items():
        md_prop_schema[name] = t2s(type(vals[0]), name in optional_md) #assumes all possible values are of same type
       
    for md_dict in (mutable_md, frozen_md, server_md):

        #ptype == python type
        for name, ptype in md_dict.items():
            md_prop_schema[name] = t2s(ptype, name in optional_md)

    for name, depend_info in dependent_md.items():
        md_prop_schema[name] = md_prop_schema[depend_info[0]] #assumes the dependent key is already added.
        

    #ADDITIONAL PROPERTIES DON'T INCLUDE NAME! OF COURSE YOU'RE GOING TO GET AN ERROR HERE!
    #YOU SHOULD USE 'requred' INSTEAD OF ADDITIONALpROPERRTIES
    song_schema = {"type": "object",
                   "additionalProperties": [md_prop_schema]}


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
                        "success": {"type": "boolean"}
                        }}
                     

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
                        "songIds": {
                            "type": "array",
                            "items": WC_Protocol.playlist_entry_schema
                            }
                        }
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
                       }}
                     
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
                       }
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
                      "playlist":
                          {"type": "array",
                           "items": WC_Protocol.song_schema}
                    },
                   "additionalProperties":{
                       "continuationToken": {"type":"string"}}
                   }

            return (req, res)

    class loadplaylist(WC_Call):
        """Loads tracks from a playlist.
        Tracks include an entryId.
        """

        gets_logged = False

        @staticmethod
        def build_transaction(playlist_id):
            req = {"id": playlist_id}
            res = None
            return (req, res)
        
    
    class modifyentries(WC_Call, UsesLog):
        """Edit the metadata of songs."""

        @classmethod
        def build_transaction(cls, songs):
            """:param songs: a list of dictionary representations of songs."""
        

            #Warn about metadata changes that may cause problems.
            #If you change the interface in api, you can warn about changing bad categories, too.
            #Something like safelychange(song, entries) where entries are only those you want to change.

            for song_md in songs:
                for key in WC_Protocol.limited_md:
                    if key in song_md and song_md[key] not in WC_Protocol.limited_md[key]:
                        if not cls.log:
                            cls.init_class_logger()

                        cls.log.warning("setting id (%s)[%s] to a dangerous value. Check metadata expectations in protocol.py", song_md["id"], key)
                        

            req = {"entries": songs}
            res = None
            return (req, res)

    class multidownload(WC_Call):
        """Get download links and counts for songs."""

        @staticmethod
        def build_transaction(song_ids):
            """:param song_ids: a list of song ids."""
            req = {"songIds": song_ids}
            res = None
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
            res = None
            return (req, res)
        

    class search(WC_Call):
        """Search for songs, artists and albums.
        GM ignores punctuation."""
    
        @staticmethod
        def build_transaction(query):
            req = {"q": query}
            res = None
            return (req, res)


class MM_Protocol():

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
        """Returns (Metadata protobuff, dictionary mapping ClientId to filename) for the given filenames."""

        filemap = {} #this maps a generated ClientID with a filename

        metadata = self.make_pb("metadata_request")

        for filename in filenames:

            #Only mp3 supported right now.
            if not filename.split(".")[-1] in supported_filetypes:
                raise UnsupportedFiletype("only these filetypes are supported for uploading: " + str(supported_filetypes))


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
            
            #It looks like we can turn on/off rematching of tracks (in session request);
            # might be better to comply and then give the option.
            
            with open(filename) as f:
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
