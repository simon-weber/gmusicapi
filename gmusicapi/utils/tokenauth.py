#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

class TokenAuth(object):
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
