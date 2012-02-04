#!/usr/bin/env python

"""Python client library for Google Music."""

import mechanize
import cookielib
import exceptions
import urllib
import urllib2
import os
import json
import warnings
import re

from urllib2  import *
from urlparse import *
from functools import wraps


class AlreadyLoggedIn(exceptions.Exception):
    pass
class NotLoggedIn(exceptions.Exception):
    pass


def wrap_single_string(item):
    """If item is a string, return [item]. Otherwise return item.

    :param item
    """

    return [item] if isinstance(item, basestring) else item

class Api:
    """ Contains abstractions of API calls."""

    def api_call(gm_service_name):
        """Decorator to add plumbing for API calls.
        Assumes all arguments are positional.

        :param gm_service_name: the part of the url that comes after /services/
        """

        def make_wrapped(json_builder):
        
            @wraps(json_builder) #Preserve docstrings.
            def wrapped(self = None, *args):
                res = self.wc_comm.make_request(gm_service_name, json_builder(*args))
                return json.loads(res.read())

            return wrapped
        return make_wrapped

    def __init__(self):
        self.wc_comm = WC_Communicator()

    def is_authenticated(self):
        """Returns whether the api is logged in."""

        return self.wc_comm.logged_in

    def login(self, email, password):
        return self.wc_comm.login(email, password)

    def logout(self):
        return self.wc_comm.logout()

    def get_download_info(self, song_id):
        """Returns a tuple of (download url, download_count).

        :param song_id: a single song id.
        """

        info = self.raw_download_info(song_ids)
        return (info["url"], info["downloadCounts"][song_id])

    def load_library(self):
        """Loads the entire library through calls to load_all_tracks.
        Returns a list of song dictionaries.
        """

        library = []

        lib_chunk = self.load_all_tracks()
    
        while 'continuationToken' in lib_chunk:
            library += lib_chunk['playlist'] #misleading name; this is the entire chunk
            
            lib_chunk = self.load_all_tracks(lib_chunk['continuationToken'])

        library += lib_chunk['playlist']

        return library
        

    def load_playlists(self):
        """Returns a dictionary of playlist_name: playlist_id for each playlist.
        """
        
        #Playlists are built in to the markup server-side.
        #There's a lot of html; rather than parse, it's easier to just cut
        # out the playlists ul, then use a regex.
        res = self.wc_comm.open_https_url("https://music.google.com/music/listen?u=0")
        markup = res.read()

        #Get the playlists ul.
        markup = markup[markup.index(r'<ul id="playlists" class="playlistContainer">'):]
        markup = markup[:markup.index(r'</ul>') + 5]


        id_name = re.findall(r'<li id="(.*?)" class="nav-item-container".*?title="(.*?)">', markup)
        
        playlists = {}
        
        for p_id, p_name in id_name:
            playlists[p_name] = p_id

        return playlists
        

    #Webclient API calls.

    #The body of the function builds the python representation of the json query, 
    # and the decorator handles the rest. 

    #The name of the function needs to be the same as it will be in the url.

    #Params should be included in the docstring, since the decorator won't preserve them.
    # The decorator module could fix this, but it seems like overkill.



    @api_call('addplaylist')
    def add_playlist(title): 
        """Creates a new playlist.

        :param title: the title of the playlist to create.
        """

        return {"title": title}

    @api_call("addtoplaylist")
    def add_to_playlist(playlist_id, song_ids):
        """Adds songs to a playlist.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """

        song_ids = wrap_single_string(song_ids)

        return {"playlistId": playlist_id, "songIds": song_ids} 

    @api_call("modifyplaylist")
    def change_playlist_name(playlist_id, new_title):
        """Changes the name of a playlist.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """
        
        return {"playlistId": playlist_id, "playlistName": new_title}

    @api_call("deleteplaylist")
    def delete_playlist(playlist_id):
        """Deletes a playlist.

        :param playlist_id: id of the playlist to delete.
        """
        
        return {"id": playlist_id}

    @api_call("deletesong")
    def delete_song(song_ids):
        """Delete a song from the entire library.

        :param song_ids: a list of song ids, or a single song id.
        """
        
        song_ids = wrap_single_string(song_ids)

        return {"songIds": song_ids, "entryIds":[""], "listId": "all"}

    @api_call("loadalltracks")
    def load_all_tracks(cont_token = None):
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

    @api_call("multidownload")
    def raw_download_info(song_ids):
        """Get download links and counts for songs.

        :param song_ids: a list of song ids, or a single song id.
        """

        song_ids = wrap_single_string(song_ids)

        return {"songIds": song_ids}

    @api_call("search")
    def search(query):
        """Searches for songs, artists and albums.
        GM ignores punctuation.

        :param query: the search query.
        """

        return {"q": query}


class Communicator:
    """ Abstract class to handle common low-level operations when communicating with Google Music.
    Implement:

    _base_url
    _user_agent

    login - store session in _cookie_jar
    make_request - 
    """

    @property
    def NotImplementedField(self):
        raise NotImplementedError

    #### Implement these:
    _base_url = NotImplementedField
    _user_agent = NotImplementedField

    
    def login(self, email, password):
        raise NotImplementedError
    
    def make_request(self, call, data):
        raise NotImplementedError
    ####



    def __init__(self):
        self._cookie_jar = cookielib.LWPCookieJar() #to hold the session
        self.logged_in = False

    def logout(self):
        self.__init__() #discard our session
        
    def open_https_url(self, target_url, encoded_data = None):
        """Opens an https url using the current session and returns the response.
        Code adapted from: http://code.google.com/p/gdatacopier/source/browse/tags/gdatacopier-1.0.2/gdatacopier.py

        :param target_url: full https url to open.
        :param encoded_data: (optional) encoded POST data.
        """

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self._cookie_jar))

        opener.addheaders = [('User-agent', self._user_agent)]
        
        if encoded_data:
            response = opener.open(target_url, encoded_data)
        else:
            response = opener.open(target_url)
            
        return response

    def get_cookie(self, name):
        """Finds a cookie by name from the cookie jar.
        Returns None on failure.

        :param name:
        """

        for cookie in self._cookie_jar:
            if cookie.name == name:
                return cookie

        return None    
    
class WC_Communicator(Communicator):
    """ A Communicator that emulates the GM web client."""

    _base_url = 'https://music.google.com/music/services/'

    #The wc requires a common user agent.
    _user_agent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.6) Gecko/20061201 Firefox/2.0.0.6 (Ubuntu-feisty)"

    def login(self, email, password, mm_session=None):
        """Attempts to login with the given credentials.
        Returns True on success, False on failure.
        
        :param email:
        :param password:
        :param mm_session: an authenticated MM_Communicator to bump to web auth
        """

        if self.logged_in:
            raise AlreadyLoggedIn

        #It's easiest just to emulate a browser; some fields are filled by javascript.
        #This code adapted from: http://stockrt.github.com/p/emulating-a-browser-in-python-with-mechanize/

        br = mechanize.Browser()
        br.set_cookiejar(self._cookie_jar)

        # Browser options
        br.set_handle_equiv(True)
        
        #Suppress warning that gzip support is experimental.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            br.set_handle_gzip(True) 

        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but doesn't hang on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # Google auth requires a common user-agent.
        br.addheaders = [('User-agent', self._user_agent)]

        r = br.open('https://music.google.com')

        br.select_form(nr=0)

        br.form['Email']=email
        br.form['Passwd']=password
        br.submit()

        self.logged_in = True if self.get_cookie("SID") else False

        return self.logged_in
    
    def make_request(self, call, data):
        """Sends a request to Google Music; returns the response.

        :param call: the name of the service, eg 'search'.
        :param data: Python representation of the json query.
        """

        if not self.logged_in:
            raise NotLoggedIn

        xt_val = self.get_cookie("xt").value

        #The url passes u=0 and the xt cookie's value. Not sure what the u is for.
        url = self._base_url + call + '?u=0&xt=' + xt_val

        #GM needs the input to be named json.
        encoded_data = "json=" + urllib.quote_plus(json.dumps(data))
        
        return self.open_https_url(url, encoded_data)
