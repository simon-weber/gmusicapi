#!/usr/bin/env python

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

from decorator import decorator
import mechanize

from gmapi.utils.apilogging import LogController


class AlreadyLoggedIn(exceptions.Exception):
    pass
class NotLoggedIn(exceptions.Exception):
    pass


class WC_Session():
    """A session for the GM web client."""


    #The wc requires a common user agent.
    _user_agent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.6) Gecko/20061201 Firefox/2.0.0.6 (Ubuntu-feisty)"


    def __init__(self):
        self._cookie_jar = cookielib.LWPCookieJar() #to hold the session
        self.logged_in = False

        self.log = LogController().get_logger(__name__ + "." + self.__class__.__name__)

    def logout(self):
        self.__init__() #discard our session

    def open_https_url(self, url_builder, extra_url_args=None, encoded_data = None):
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

        opener.addheaders = [('User-agent', self._user_agent)]
        
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

        br.open('https://music.google.com')

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

        first = r.split("\n")[0]

        #Bad auth will return Error=BadAuthentication\n

        if first.split("=")[0] == "SID":
            self.sid = first
            #self.uauthresp.ParseFromString(self.protopost("upauth", self.uauth))
            #self.clientstateresp.ParseFromString(self.protopost("clientstate", self.clientstate))
            return True
        else:
            return False


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


