#!/usr/bin/env python

#Copyright 2012 Simon Weber.

#This file is part of gmapi - the Unofficial Google Music API.

#Gmapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmapi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with gmapi.  If not, see <http://www.gnu.org/licenses/>.


"""Python api for Google Music."""

import json
import re
import string
import time
import urllib

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from gmapi.session import WC_Session, MM_Session
from gmapi.protocol import WC_Protocol, MM_Protocol
from gmapi.utils import utils
from gmapi.utils.apilogging import LogController

class Api:
    def __init__(self):
        self.wc_session = WC_Session()
        self.wc_protocol = WC_Protocol()

        self.mm_session = MM_Session()
        self.mm_protocol = MM_Protocol()

        self.log = LogController().get_logger(__name__ + "." + self.__class__.__name__)


    #---
    #   Authentication:
    #---

    def is_authenticated(self):
        """Returns whether the api is logged in."""

        return self.wc_session.logged_in and not (self.mm_session.sid == None)

    def login(self, email, password):
        """Authenticates the api with the given credentials.
        Returns True on success, False on failure.

        :param email: eg `test@gmail.com`
        :param password: plaintext password. It will not be stored and is sent over ssl."""

        self.wc_session.login(email, password)
        self.mm_session.login(email, password)


        if self.is_authenticated():
            #Need some extra init for upload authentication.
            self._mm_pb_call("upload_auth")
            self.log.info("logged in")
        else:
            self.log.info("failed to log in")

        return self.is_authenticated()

    def logout(self):
        """Logs out of the api.
        Returns True on success, False on failure."""

        self.wc_session.logout()
        self.mm_session.logout()

        self.log.info("logged out")

        return True


    #---
    #   Api features supported by the web client interface:
    #---



    @utils.accept_singleton(basestring, 2) #can also accept a single string in pos 2 (song_ids)
    def add_songs_to_playlist(self, playlist_id, song_ids):
        """Adds songs to a playlist.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """

        return self._wc_call("addtoplaylist", playlist_id, song_ids)

    def change_playlist_name(self, playlist_id, new_name):
        """Changes the name of a playlist.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """

        return self._wc_call("modifyplaylist", playlist_id, new_name)

    @utils.accept_singleton(dict)
    def change_song_metadata(self, songs):
        """Changes the metadata for songs.
        Songs are presumed to be in GM dictionary format.

        :param songs: a list of song dictionaries, or a single song dictionary.
        """

        return self._wc_call("modifyentries", songs)
        
    def create_playlist(self, name):
        """Creates a new playlist.

        :param title: the title of the playlist to create.
        """

        return self._wc_call("addplaylist", name)

    def delete_playlist(self, playlist_id):
        """Deletes a playlist.

        :param playlist_id: id of the playlist to delete.
        """

        return self._wc_call("deleteplaylist", playlist_id)

    @utils.accept_singleton(basestring)
    def delete_song(self, song_ids):
        """Deletes songs from the entire library.

        :param song_ids: a list of song ids, or a single song id.
        """

        return self._wc_call("deletesong", song_ids)

    def get_all_songs(self):
        """Returns a list of song dictionaries."""

        library = []

        lib_chunk = self._wc_call("loadalltracks")
    
        while 'continuationToken' in lib_chunk:
            library += lib_chunk['playlist'] #misleading name; this is the entire chunk
            
            lib_chunk = self._wc_call("loadalltracks", lib_chunk['continuationToken'])

        library += lib_chunk['playlist']

        return library

    def get_playlist_songs(self, playlist_id):
        """Returns a list of song dictionaries, which include entryIds keys for the given playlist.

        :param playlist_id: id of the playlist to load.
        """

        return self._wc_call("loadplaylist", playlist_id)["playlist"]

    def get_playlists(self):
        """Returns a dictionary which maps playlist name to id for all user-defined playlists.
        The dictionary does not include autoplaylists.
        """
        
        #Playlists are built in to the markup server-side.
        #There's a lot of html; rather than parse, it's easier to just cut
        # out the playlists ul, then use a regex.
        res = self.wc_session.open_https_url("https://music.google.com/music/listen?u=0")
        markup = res.read()

        #Get the playlists ul.
        markup = markup[markup.index(r'<ul id="playlists" class="playlistContainer">'):]
        markup = markup[:markup.index(r'</ul>') + 5]


        id_name = re.findall(r'<li id="(.*?)" class="nav-item-container".*?title="(.*?)">', markup)
        
        playlists = {}
        
        for p_id, p_name in id_name:
            playlists[p_name] = p_id

        return playlists

    def get_song_download_info(self, song_id):
        """Returns a tuple of (download url, download_count).
        GM allows 2 downloads per song.

        :param song_id: a single song id.
        """

        #The protocol expects a list of songs - could extend with accept_singleton
        info = self._wc_call("multidownload", [song_id])

        return (info["url"], info["downloadCounts"][song_id])

    def get_stream_url(self, song_id):
        """Returns a url that points to the audio file for this song. Reading the file does not require authentication.
        *This is only intended for streaming*. The streamed audio does not contain metadata. Use :func:`get_song_download_info` to download complete files.
        
        :param song_id: a single song id.
        """

        #This call is strange. The body is empty, and the songid is passed in the querystring.
        res = self._wc_call("play", query_args={'songid': song_id})
        
        return res['url']
        

    @utils.accept_singleton(basestring)
    def remove_song_from_playlist(self, song_ids, playlist_id):
        """Removes songs from a playlist.

        :param song_ids: a list of song ids, or a single song id.
        """

        #Not as easy as just calling deletesong with the playlist;
        # we need the entryIds for the songs with the playlist as well.

        playlist_tracks = self.get_playlist_songs(playlist_id)

        entry_ids = []

        for sid in song_ids:
            matched_eids = [t["playlistEntryId"] for t in playlist_tracks if t["id"] == sid]
            
            if len(matched_eids) < 1:
                self.log.warning("could not match song id %s to any entryIds")
            else:
                entry_ids.extend(matched_eids)


        return self._wc_call("deletesong", song_ids, entry_ids, playlist_id)

    def search(self, query):
        """Searches for songs, artists and albums.
        GM ignores punctuation.

        :param query: the search query.
        """

        return self._wc_call("search", query)


    def _wc_call(self, service_name, *args, **kw):
        """Returns the response of a web client call.
        :param service_name: the name of the call, eg ``search``
        additional positional arguments are passed to ``build_body``for the retrieved protocol.
        if a 'query_args' key is present in kw, it is assumed to be a dictionary of additional key/val pairs to append to the query string.
        """

        #TODO check if we're logged in!
        protocol = getattr(self.wc_protocol, service_name)

        if protocol.gets_logged:
            self.log.debug("wc_call: %s(%s)", service_name, str(args))
        
        url_builder = protocol.build_url
        body = protocol.build_body(*args)
        

        #Encode the body. It might be None (empty).
        #This should probably be done in protocol, and an encoded body grabbed here.
        if body != None: #body can be {}, which is different from None. {} is falsey.
            body = "json=" + urllib.quote_plus(json.dumps(body))

        extra_query_args = None
        if 'query_args' in kw:
            extra_query_args = kw['query_args']

        res = self.wc_session.open_https_url(url_builder, extra_query_args, body)
        
        res = json.loads(res.read())

        if protocol.gets_logged:
            self.log.debug("wc_call response: %s", res)

        return res


    #---
    #   Api features supported by the Music Manager interface:
    #---


    #This works, but the protocol isn't quite right.
    #For now, you're better off just taking len(get_all_songs)
    # to get a count of songs in the library.

    # def get_quota(self):
    #     """Returns a tuple of (allowed number of tracks, total tracks, available tracks)."""

    #     quota = self._mm_pb_call("client_state").quota

    #     #protocol incorrect here...
    #     return (quota.maximumTracks, quota.totalTracks, quota.availableTracks)

    @utils.accept_singleton(basestring)
    def upload(self, filenames):
        """Uploads the MP3s stored in the given filenames.
        Returns a mapping of filename: GM song id for each successful upload.
        Returns an empty dictionary if all uploads fail.

        :param filenames: a list of filenames, or a single filename
        """

        #filename -> GM song id
        fn_sid_map = {}

        #Form and send the metadata request.
        metadata_request, cid_map = self.mm_protocol.make_metadata_request(filenames)
        metadataresp = self._mm_pb_call("metadata", metadata_request)

        #Form upload session requests (for songs GM wants).
        session_requests = self.mm_protocol.make_upload_session_requests(cid_map, metadataresp)

    
        for filename, server_id, payload in session_requests:

            post_data = json.dumps(payload)

            success = False
            attempts = 0
            while not success and attempts < 3:
                
                #Pull this out with the below call when it makes sense to.
                res = json.loads(
                    self.mm_session.jumper_post(
                        "/uploadsj/rupio", 
                        post_data).read())

                if 'sessionStatus' in res:
                    self.log.info("got a session. full response: %s", str(res))
                    success = True
                    break
                
                elif 'errorMessage' in res:
                    self.log.warning("got an error from the GM upload server. full response: %s", str(res))
                else:
                    self.log.warning("could not interpret upload session resonse. full response: %s", str(res))
                    
                    
                    
                time.sleep(3)
                self.log.info("trying again for a session.")
                attempts += 1
                
                #print "Waiting for servers to sync..."

            if success:
                #Got a session; upload the actual file.
                up = res['sessionStatus']['externalFieldTransfers'][0]
                self.log.info("uploading file. sid: %s", server_id)
                #print "Uploading a file... this may take a while"

                res = json.loads(
                    self.mm_session.jumper_post( 
                        up['putInfo']['url'], 
                        open(filename), 
                        {'Content-Type': up['content_type']}).read())


                #if options.verbose: print res
                if res['sessionStatus']['state'] == 'FINALIZED':
                    fn_sid_map[filename] = server_id
                    self.log.info("successfully uploaded sid %s", server_id)
            else:
                self.log.warning("could not get an upload session for sid %s", server_id)


        
        return fn_sid_map


    def _mm_pb_call(self, service_name, req = None):
        """Returns the protobuff response of a call to a predefined Music Manager protobuff service."""

        self.log.debug("mm_pb_call: %s(%s)", service_name, str(req))

        res = self.mm_protocol.make_pb(service_name + "_response")

        if not req:
            try:
                req = self.mm_protocol.make_pb(service_name + "_request")
            except AttributeError:
                req = self.mm_protocol.make_pb(service_name) #some request types don't have _request appended.

        url = self.mm_protocol.pb_services[service_name]

        res.ParseFromString(self.mm_session.protopost(url, req))

        self.log.debug("mm_pb_call response: [%s]", str(res))

        return res
