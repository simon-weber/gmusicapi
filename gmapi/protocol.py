#!/usr/bin/env python

"""The protocol layer is a one-to-one mapping of calls to Google Music."""

from .utils import utils

from collections import namedtuple
import metadata_pb2
import exceptions

from uuid import getnode as getmac
from socket import gethostname

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

import string
import os
import random


class UnsupportedFiletype(exceptions.Exception):
    pass

class WC_Protocol:

    #Metadata expectations:

    #Entries that accept a limited set of values.
    #Metadata name -> list of values it can hold.
    #This needs to be investigated and fleshed out.
    limited_md = {
        "rating" : (0, 1, 5)
    }

    #Entries we have control of, and can change.
    mutable_md = ('rating', 'disc', 'composer', 'year', 'album', 'albumArtist',
              'track', 'totalTracks', 'genre', 'playCount', 'name',
              'artist', 'totalDiscs', 'durationMillis')

    #Entries we cannot change.
    frozen_md = ('comment', 'id', 'deleted', 'creationDate', 'albumArtUrl', 'type', 'beatsPerMinute',
                 'url')

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
    server_md = ('lastPlayed', ) #likely an accessed timestamp in actuality?


    @staticmethod
    def addplaylist(title): 
        """Creates a new playlist.

        :param title: the title of the playlist to create.
        """

        return {"title": title}


    @staticmethod
    def addtoplaylist(playlist_id, song_ids):
        """Adds songs to a playlist.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids
        """

        return {"playlistId": playlist_id, "songIds": song_ids} 


    @staticmethod
    def modifyplaylist(playlist_id, new_name):
        """Changes the name of a playlist.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """
        
        return {"playlistId": playlist_id, "playlistName": new_name}


    @staticmethod
    def deleteplaylist(playlist_id):
        """Deletes a playlist.

        :param playlist_id: id of the playlist to delete.
        """
        
        return {"id": playlist_id}

    @staticmethod
    def deletesong(song_ids):
        """Delete a song from the entire library.

        :param song_ids: a list of song ids
        """

        return {"songIds": song_ids, "entryIds":[""], "listId": "all"}

    @staticmethod
    def loadalltracks(cont_token = None):
        """Loads tracks from the library.
        Since libraries can have many tracks, GM gives them back in chunks.
        Chunks will send a continuation token to get the next chunk.
        The first request needs no continuation token.
        The last response will not send a token.
        
        :param cont_token: (optional) token to get the next library chunk.
        """

        if not cont_token:
            return {}
        else:
            return {"continuationToken": cont_token}

    @staticmethod
    def modifyentries(songs):
        """Edit the metadata for these songs.

        :param songs: a list of dictionary representations of songs.
        """

        return {"entries": songs}

    @staticmethod
    def multidownload(song_ids):
        """Get download links and counts for songs.

        :param song_ids: a list of song ids.
        """

        return {"songIds": song_ids}

    @staticmethod
    def search(query):
        """Searches for songs, artists and albums.
        GM ignores punctuation.

        :param query: the search query.
        """

        return {"q": query}



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
            if not filename.split(".")[-1] == "mp3":
                raise UnsupportedFiletype


            track = metadata.tracks.add()

            audio = MP3(filename, ID3 = EasyID3)


            #I have the feeling this is a hash, not random...
            id = ''.join(
                random.choice(string.ascii_letters + string.digits) 
                for i in range(20))

            filemap[id] = filename
            track.id = id

            filesize = os.path.getsize(filename)

            track.fileSize = filesize

            track.bitrate = audio.info.bitrate / 1000
            track.duration = int(audio.info.length * 1000)
            if "album" in audio: track.album = audio["album"][0]
            if "title" in audio: track.title = audio["title"][0]
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
            #print "preparing session for:", os.path.basename(filename)
            #if options.verbose: print upload

            inlined = {
                "title": "jumper-uploader-title-42",
                "ClientId": upload.id,
                "ClientTotalSongCount": len(server_response.response.uploads),
                "CurrentTotalUploadedCount": "0",
                "CurrentUploadingTrack": audio["title"][0], #there's an assumption here...
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
