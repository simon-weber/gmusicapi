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

"""The session layer allows for authentication and the making of authenticated requests."""

import cookielib
import exceptions
import urllib
import urllib2
import os
import json
import warnings
from urllib2  import *
from urlparse import *
import httplib

try:
    from decorator import decorator
except ImportError:
    from utils.utils import mock_decorator as decorator

import mechanize

from utils.apilogging import UsesLog


class AlreadyLoggedIn(exceptions.Exception):
    pass
class NotLoggedIn(exceptions.Exception):
    pass


class WC_Session(UsesLog):
    """A session for the GM web client."""


    #The wc requires a common user agent.
    _user_agent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.6) Gecko/20061201 Firefox/2.0.0.6 (Ubuntu-feisty)"


    def __init__(self):
        self._cookie_jar = cookielib.LWPCookieJar() #to hold the session
        self.logged_in = False

        self.init_logger()

    def logout(self):
        self.__init__() #discard our session


    def open_authed_https_url(self, url_builder, extra_url_args=None, encoded_data = None):
        """Same as open_https_url, but raises an exception if the session isn't logged in."""
        if not self.logged_in:
            raise NotLoggedIn

        return self.open_https_url(url_builder, extra_url_args, encoded_data)

    def open_https_url(self, url_builder, extra_url_args=None, encoded_data = None, user_agent=None):
        """Opens an https url using the current session and returns the response.
        Code adapted from: http://code.google.com/p/gdatacopier/source/browse/tags/gdatacopier-1.0.2/gdatacopier.py
        :param url_builder: the url, or a function to receieve a dictionary of querystring arg/val pairs and return the url.
        :extra_url_args: (optional) key/val querystring pairs.
        :param encoded_data: (optional) encoded POST data.
        """

        if isinstance(url_builder, basestring):
            url = url_builder
        else:
            url = url_builder({'xt':self.get_cookie("xt").value})
        
        #Add in optional pairs to the querystring.
        if extra_url_args:
            #Assumes that a qs has already been started (ie we don't need to put a ? first)
            assert (url.find('?') >= 0)

            extra_args = ""
            for name, val in extra_url_args.iteritems():
                extra_args += "&{0}={1}".format(name, val)

            url += extra_args
        
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self._cookie_jar))

        if not user_agent:
            user_agent = self._user_agent

        opener.addheaders = [('User-agent', user_agent)]
        
        if encoded_data:
            response = opener.open(url, encoded_data)
        else:
            response = opener.open(url)
            
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

    def sid_login(self, sid, lsid):
        """Attempts to bump an existing session to a full web client session.
        Returns True on success, False on failure.

        :param sid:
        
        This method is used by Music Manager when "go to Google Music" is clicked.
        """

        if self.logged_in:
            raise AlreadyLoggedIn

        body = "SID={}&LSID={}&service=gaia".format(urllib.quote_plus(sid), urllib.quote_plus(lsid))

        #Get authtoken.
        res = self.open_https_url("https://www.google.com/accounts/IssueAuthToken", encoded_data=body, user_agent="Music Manager (1, 0, 24, 7712 - Windows)")
        authtoken = res.read()[:-1]

        #Use authtoken to get session cookies.
        res = self.open_https_url("https://accounts.google.com/TokenAuth?auth={}%0A&service=sj&continue=http%3A%2F%2Fmusic.google.com%2Fmusic%2Flisten%3Fhl%3Den&source=jumper".format(authtoken))
        
        #Hit listen to get xt.
        res = self.open_https_url("https://play.google.com/music/listen?hl=en&u=0")
        
        self.logged_in = True if (self.get_cookie("SID") and self.get_cookie("xt")) else False
        return self.logged_in

    def login(self, email, password):
        """Attempts to login with the given credentials.
        Returns True on success, False on failure.
        
        :param email:
        :param password:
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

        br.open('https://play.google.com/music')

        br.select_form(nr=0)

        br.form['Email']=email
        br.form['Passwd']=password
        br.submit()

        self.logged_in = True if self.get_cookie("SID") else False

        return self.logged_in


class MM_Session:    
    """A session for the Music Manager."""

    @decorator
    def require_auth(f, self = None, *args, **kw):
        """Decorator to check for auth before running a function.
        Assumes that the function is a member of this class.
        """

        if not self.sid:
            raise NotLoggedIn

        return f(self, *args, **kw)

    def __init__(self):
        self.sid = None
        self.lsid = None
        self.auth = None

        self.android = httplib.HTTPSConnection("android.clients.google.com")
        self.jumper = httplib.HTTPConnection('uploadsj.clients.google.com')

    def login(self, email, password):

        if self.sid:
            raise AlreadyLoggedIn

        payload = {
            'Email': email,
            'Passwd': password,
            'service': 'sj',
            'accountType': 'GOOGLE'
        }
        r = urllib.urlopen("https://google.com/accounts/ClientLogin", 
                            urllib.urlencode(payload)).read()

        return_pairs = dict([e.split("=") for e in r.split("\n") if len(e) > 0])
        if "Error" in return_pairs:
            return False

        for key, val in return_pairs.iteritems():
            setattr(self, str.lower(key), key+"="+val)

        return self.sid != None

    def logout(self):
        self.sid = None
        #There's got to be more to do...

    @require_auth
    def protopost(self, path, proto):
        """Returns the response from encoding and posting the given data.
        
        :param path: the name of the service url
        :param proto: data to be encoded with protobuff
        """

        self.android.request("POST", "/upsj/"+path, proto.SerializeToString(), {
            "Cookie": self.sid,
            "Content-Type": "application/x-google-protobuf"
        })
        r = self.android.getresponse()

        return r.read()

    @require_auth
    def jumper_post(self, url, encoded_data, headers=None):
        """Returns the response of a post to the MM jumper service."""

        if not headers:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded", #? shouldn't it be json? but that's what the google client sends
                "Cookie": self.sid}

        self.jumper.request("POST", url, encoded_data, headers)

        return self.jumper.getresponse()


