#!/user/bin/env python

#Copyright 2012 Darryl Pogue.

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

from __future__ import print_function
try:
    # These are for python3 support
    from urllib.request import HTTPCookieProcessor, Request, build_opener
    from urllib.error import HTTPError
    from urllib.parse import urlencode
    from http.cookiejar import LWPCookieJar
    unistr = str
except ImportError:
    # Fallback to python2
    from urllib2 import HTTPCookieProcessor, Request, build_opener
    from urllib2 import HTTPError
    from urllib import urlencode
    from cookielib import LWPCookieJar
    unistr = unicode

class TokenAuth:
    """
    A Google ClientLogin to web session converter.
    """

    # This is the URL used to get a short-lived AuthToken
    ISSUE_URL = 'https://www.google.com/accounts/IssueAuthToken'

    # This is the URL used to get redeem that token for web cookies
    AUTH_URL = 'https://www.google.com/accounts/TokenAuth'

    def __init__(self, service, redirect, source=None):
        self.cookiejar = LWPCookieJar()

        self.service = service
        self.redirect = redirect
        self.source = source


    def _make_request(self, url, data=None, headers={}):
        if not data:
            data = None
        else:
            data = urlencode(data)
            data = data.encode('utf8')

        req = Request(url, data, headers)
        err = None

        handler = build_opener(HTTPCookieProcessor(self.cookiejar))

        try:
            resp_obj = handler.open(req)
        except HTTPError as e:
            err = e.code
            return err, e.read()
        resp = resp_obj.read()
        resp_obj.close()
        return None, unistr(resp, encoding='utf8')


    def authenticate(self, clientlogin):
        body =  {
            'SID':      clientlogin.get_sid_token(),
            'LSID':     clientlogin.get_lsid_token(),
            'service':  'gaia'
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
            # Request is refused unless MM is user agent
            'User-Agent':   'Music Manager (1, 0, 24, 7712 - Windows)'
        }

        # Get the auth token
        err, resp = self._make_request(self.ISSUE_URL, body, headers)
        if err is not None:
            raise "HTTP Error %d" % err

        token = resp.rstrip() #resp[:-1]

        data = {
            'auth':     token,
            'service':  self.service,
            'continue': self.redirect
        }
        if self.source is not None:
            data['source'] = self.source

        params = urlencode(data)
        url = '%s?%s' % (self.AUTH_URL, params)

        # Get the session cookies
        err, resp = self._make_request(url, None, headers)
        if err is not None:
            raise "HTTP Error %d" % err

    def get_cookies(self):
        return self.cookiejar
