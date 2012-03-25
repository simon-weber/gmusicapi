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

"""
The session layer allows for authentication and the making of authenticated
requests through the MusicManager API (protocol buffers), Web client requests,
and the Skyjam client API.
"""

import json
from utils.clientlogin import ClientLogin
from utils.tokenauth import TokenAuth

try:
    # These are for python3 support
    from urllib.request import HTTPCookieProcessor, Request, build_opener
    from urllib.error import HTTPError
    from urllib.parse import urlencode, quote_plus
    from http.client import HTTPConnection, HTTPSConnection
    unistr = str
except ImportError:
    # Fallback to python2
    from urllib2 import HTTPCookieProcessor, Request, build_opener
    from urllib2 import HTTPError
    from urllib import urlencode, quote_plus
    from httplib import HTTPConnection, HTTPSConnection
    unistr = unicode


class AlreadyLoggedIn(Exception):
    pass

class NotLoggedIn(Exception):
    pass

class PlaySession(object):
    """
    A Google Play Music session.
    """

    # The URL for authenticating against Google Play Music
    PLAY_URL = 'https://play.google.com/music/listen?u=0&hl=en'

    # Common User Agent used for web requests
    _user_agent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.6) Gecko/20061201 Firefox/2.0.0.6 (Ubuntu-feisty)"

    def __init__(self):
        """
        Initializes a default unauthenticated session.
        """
        self.client = None
        self.cookies = None
        self.logged_in = False

        # Wish there were better names for these
        self.android = HTTPSConnection('android.clients.google.com')
        self.jumper  = HTTPConnection('uploadsj.clients.google.com')


    def _get_cookies(self):
        """
        Gets cookies needed for web and media streaming access.
        Returns True if the necessary cookies are found, False otherwise.
        """
        if self.logged_in:
            raise AlreadyLoggedIn

        handler = build_opener(HTTPCookieProcessor(self.cookies))
        req = Request(self.PLAY_URL, None, {}) #header)
        resp_obj = handler.open(req)

        return  (
                    self.get_cookie('sjsaid') is not None and
                    self.get_cookie('xt') is not None
                )


    def get_cookie(self, name):
        """
        Finds the value of a cookie by name, returning None on failure.

        :param name: The name of the cookie to find.
        """
        for cookie in self.cookies:
            if cookie.name == name:
                return cookie.value

        return None


    def login(self, email, password):
        """
        Attempts to create an authenticated session using the email and
        password provided.
        Return True if the login was successful, False otherwise.
        Raises AlreadyLoggedIn if the session is already authenticated.

        :param email: The email address of the account to log in.
        :param password: The password of the account to log in.
        """
        if self.logged_in:
            raise AlreadyLoggedIn

        self.client = ClientLogin(email, password, 'sj')
        tokenauth = TokenAuth('sj', self.PLAY_URL, 'jumper')

        if self.client.get_auth_token() is None:
            return False

        tokenauth.authenticate(self.client)
        self.cookies = tokenauth.get_cookies()

        self.logged_in = self._get_cookies()

        return self.logged_in


    def logout(self):
        """
        Resets the session to an unauthenticated default state.
        """
        self.__init__()


    def open_web_url(self, url_builder, extra_args=None, data=None, ua=None):
        """
        Opens an https url using the current session and returns the response.
        Code adapted from:
        http://code.google.com/p/gdatacopier/source/browse/tags/gdatacopier-1.0.2/gdatacopier.py

        :param url_builder: the url, or a function to receieve a dictionary of querystring arg/val pairs and return the url.
        :param extra_args: (optional) key/val querystring pairs.
        :param data: (optional) encoded POST data.
        :param ua: (optional) The User Age to use for the request.
        """
        # I couldn't find a case where we don't need to be logged in
        if not self.logged_in:
            raise NotLoggedIn

        if isinstance(url_builder, basestring):
            url = url_builder
        else:
            url = url_builder({'xt':self.get_cookie("xt")})

        #Add in optional pairs to the querystring.
        if extra_args:
            #Assumes that a qs has already been started (ie we don't need to put a ? first)
            assert (url.find('?') >= 0)

            extra_url_args = ""
            for name, val in extra_args.iteritems():
                extra_url_args += "&{0}={1}".format(name, val)

            url += extra_url_args

        opener = build_opener(HTTPCookieProcessor(self.cookies))

        if not ua:
            ua = self._user_agent

        opener.addheaders = [('User-agent', ua)]

        if data:
            response = opener.open(url, data)
        else:
            response = opener.open(url)

        return response


    def post_protobuf(self, path, protobuf):
        """
        Returns the response from encoding and posting the given data.

        :param path: the name of the service url
        :param proto: data to be encoded with protobuff
        """
        if not self.logged_in:
            raise NotLoggedIn

        urlpath = '/upsj/' + path
        self.android.request('POST', urlpath, protobuf.SerializeToString(), {
            'Cookie':       'SID=%s' % self.client.get_sid_token(),
            'Content-Type': 'application/x-google-protobuf'
        })

        resp = self.android.getresponse()

        return resp.read()


    def post_jumper(self, url, encoded_data, headers=None):
        """
        Returns the response of a post to the MusicManager jumper service.
        """
        if not self.logged_in:
            raise NotLoggedIn

        if not headers:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cookie':       'SID=%s' % self.client.get_sid_token()
            }

        self.jumper.request('POST', url, encoded_data, headers)
        return self.jumper.getresponse()
