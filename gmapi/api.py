#!/usr/bin/env python

"""Python api for Google Music."""

import json
import re

from gmapi.session import *
from gmapi.protocol import *

class Api:
    """ Contains abstractions of API calls."""


    def __init__(self):
        self.wc_session = WC_Session()
        self.mm_session = MM_Session()

        self.wc_protocol = WC_Protocol()
        #Consider using a named tuple to keep these in one place?


    def is_authenticated(self):
        """Returns whether the api is logged in."""

        return self.wc_session.logged_in and self.mm_session.sid

    def login(self, email, password):
        """Authenticates the api with the given credentials.
        Returns True on success, False on failure.

        :param email: eg test@gmail.com
        :param password
        """

        self.wc_session.login(email, password)
        self.mm_session.login(email, password)

        return self.is_authenticated()

    def logout(self):
        """Log out of the Api.
        Returns True on success, False on failure."""

        self.wc_session.logout()
        #TODO: logout for mm_communicator

        return True


    #Api features supported by the web client interface.

    def add_playlist(self, name):
        """Creates a new playlist.

        :param title: the title of the playlist to create.
        """

        return self.wc_call("addplaylist", name)

    def add_to_playlist(self, playlist_id, song_ids):
        """Adds songs to a playlist.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """

        return self.wc_call("addtoplaylist", playlist_id, song_ids)

    def change_playlist_name(self, playlist_id, new_name):
        """Changes the name of a playlist.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """

        return self.wc_call("modifyplaylist", playlist_id, new_name)

    def delete_playlist(self, playlist_id):
        """Deletes a playlist.

        :param playlist_id: id of the playlist to delete.
        """

        return self.wc_call("deleteplaylist", playlist_id)

    def delete_song(self, song_ids):
        """Delete a song from the entire library.

        :param song_ids: a list of song ids, or a single song id.
        """

        return self.wc_call("deletesong", song_ids)

    def get_library_track_metadata(self):
        """Returns a list of song metadata dictionaries.
        """

        library = []

        lib_chunk = self.wc_call("loadalltracks")
    
        while 'continuationToken' in lib_chunk:
            library += lib_chunk['playlist'] #misleading name; this is the entire chunk
            
            lib_chunk = self.wc_call("loadalltracks", lib_chunk['continuationToken'])

        library += lib_chunk['playlist']

        return library

    def get_playlist_ids(self):
        """Returns a dictionary mapping playlist name to id for all user playlists.
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

    def get_track_download_info(self, song_id):
        """Returns a tuple of (download url, download_count).

        :param song_id: a single song id.
        """

        info = self.wc_call("multidownload", song_ids)
        return (info["url"], info["downloadCounts"][song_id])


    def search(self, query):
        """Searches for songs, artists and albums.
        GM ignores punctuation.

        :param query: the search query.
        """

        return self.wc_call("search", query)


    #Utility function to make calls with the web client, using the session and protocol.
    def wc_call(self, service_name, *args, **kw):
        """Make a call with the web client session and protocol."""

        protocol_builder = getattr(self.wc_protocol, service_name)

        res = self.wc_session.make_request(service_name, 
                                           protocol_builder(*args, **kw))
        return json.loads(res.read())
