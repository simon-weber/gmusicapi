#!/usr/bin/env python

import mechanize
import cookielib
import exceptions
import urllib
import urllib2
import os
import json
import inspect

from urllib2  import *
from urlparse import *
from functools import wraps

from prompt import prompt #For dropping into a prompt when debugging

#Self explanatory exceptions.
class AlreadyLoggedIn(exceptions.Exception):
    pass
class NotLoggedIn(exceptions.Exception):
    pass


class GM_API:
    """ Contains functional abstractions of API calls."""

    def __init__(self):
        self.comm = GM_Communicator()

    def login(self, email, password):
        return self.comm.login(email, password)

    def logout(self):
        return self.comm.logout()

    def api_call(json_builder):
        """Decorator for building API calls."""

        @wraps(json_builder) #Preserve docstrings.
        def wrapped(self = None, *args):
            res = self.comm.make_request(json_builder.__name__, json_builder(*args))
            return json.loads(res.read())

        return wrapped

    def load_library(self):
        """Loads the entire library through one or more calls to loadalltracks.
        returns a list of song key-value pairs."""

        library = []

        lib_chunk = self.loadalltracks()
    
        while 'continuationToken' in lib_chunk:
            library += lib_chunk['playlist'] #misleading name; this is the entire chunk
            
            lib_chunk = self.loadalltracks(lib_chunk['continuationToken'])

        library += lib_chunk['playlist']

        return library
        
        

    #API calls.
    #Calls added properly here should be automatically supported. The body of the function simply builds the python representation of the json query, and the decorator handles the rest. The name of the function needs to be the same as it will be in the url.
    #They should also have params in the docstring, since args (presently) won't be preserved by the decorator. The decorator module fixes this, but I'd rather not introduce another dependency.
    @api_call
    def search(query):
        """Search for songs, artists and albums.
        query: the search query."""

        return {"q": query}

    @api_call
    def addplaylist(title): 
        """Create a new playlist.
        title: the title of the playlist to create."""

        return {"title": title}

    @api_call
    def addtoplaylist(playlist_id, song_ids):
        """Add songs to a playlist.
        playlist_id: id of the playlist to add to.
        song_ids:    a list of song ids, or a single song id."""

        #We require a list. If a string is passed, wrap it in a list.
        if isinstance(song_ids, basestring):
            song_ids = [song_ids]

        return {"playlistId": playlist_id, "songIds": song_ids} 

    @api_call
    def loadalltracks(cont_token = None):
        """Load tracks from the library.
        cont_token: a continuation token from a previous request chunk

        Since libraries can have many tracks, GM gives them back in chunks.
        If after a request, no continuation token comes back, the entire library has been sent.
        The first request has no continuation token.
        """

        if not cont_token:
            return {}
        else:
            return {"continuationToken":cont_token}
        

class GM_Communicator:
    """ Enables low level communication with Google Music."""

    _base_url = 'https://music.google.com/music/services/'
    _user_agent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.6) Gecko/20061201 Firefox/2.0.0.6 (Ubuntu-feisty)"
    

    def __init__(self):
        #This cookie jar holds our session.
        self._cookie_jar = cookielib.LWPCookieJar()
        self.logged_in = False

    def login(self, email, password):
        if self.logged_in:
            raise AlreadyLoggedIn

        #Faking Google auth is tricky business, and it's easiest just to emulate a browser; there are fields filled in by javascript when a user submits, for example.

        #This code modified from here: http://stockrt.github.com/p/emulating-a-browser-in-python-with-mechanize/

        br = mechanize.Browser()
        br.set_cookiejar(self._cookie_jar)

        # Browser options
        br.set_handle_equiv(True)
        br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but doesn't hang on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # Google auth requires a common user-agent.
        br.addheaders = [('User-agent', self._user_agent)]

        r = br.open('https://music.google.com')
        auth_page = r.read()

        br.select_form(nr=0)

        br.form['Email']=email
        br.form['Passwd']=password
        br.submit()

        self.logged_in = True if self.get_cookie("SID") else False

        return self.logged_in

    def logout(self):
        self._cookie_jar = cookielib.CookieJar()
        self.logged_in = False
    
    def make_request(self, call, data):
        """Make a single request to Google Music and return the response for reading.
        call: the name of the service, eg 'search'
        data: Python representation of the json query"""

        if not self.logged_in:
            raise NotLoggedIn

        xt_val = self.get_cookie("xt").value

        #The url passes u=0 and the xt cookie's value. Not sure what the u is for.
        url = self._base_url + call + '?u=0&xt=' + xt_val

        #GM needs the input to be named json.
        encoded_data = "json=" + urllib.quote_plus(json.dumps(data))
        
        return self.open_https_url(url, encoded_data)


    def open_https_url(self, target_url, encoded_data = None):
        """Open an https url using our Google session.
        target_url: full https url to open
        encoded_data: optional, encoded POST data"""

        #Code adapted from: http://code.google.com/p/gdatacopier/source/browse/tags/gdatacopier-1.0.2/gdatacopier.py

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self._cookie_jar))

        opener.addheaders = [('User-agent', self._user_agent)]
        
        response = None
        if encoded_data:
            response = opener.open(target_url, encoded_data)
        else:
            response = opener.open(target_url)
            
        return response

    def get_cookie(self, name):
        """Find a cookie by name from the cookie jar."""

        for cookie in self._cookie_jar:
            if cookie.name == name:
                return cookie

        return None
