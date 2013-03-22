#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sessions handle the details of authentication and transporting requests.
"""

import httplib2  # included with oauth2client
import requests

from gmusicapi.exceptions import (
    AlreadyLoggedIn, NotLoggedIn, CallFailure
)
from gmusicapi.protocol.shared import ClientLogin
from gmusicapi.protocol import webclient


class _Base(object):
    def __init__(self):
        self._rsession = requests.Session()
        self.is_authenticated = False

    def _send_with_auth(self, req_kwargs, desired_auth):
        raise NotImplementedError

    def _send_without_auth(self, req_kwargs):
        """Send a request using a throwaway session."""
        # this shouldn't happen often (it loses out on connection-pooling)
        s = requests.Session()
        res = s.request(**req_kwargs)
        s.close()

        return res

    def login(self, *args, **kwargs):
        if self.is_authenticated:
            raise AlreadyLoggedIn

    def logout(self):
        """
        Reset the session to an unauthenticated, default state.
        """
        self._rsession.close()
        self.__init__()

    def send(self, req_kwargs, desired_auth):
        """Send a request from a Call using this session's auth.

        :param req_kwargs: kwargs for requests.Session.request
        :param desired_auth: protocol.shared.AuthTypes to attach
        """
        if not any(desired_auth):
            return self._send_without_auth(req_kwargs)

        else:
            if not self.is_authenticated:
                raise NotLoggedIn

            return self._send_with_auth(req_kwargs, desired_auth)


class Webclient(_Base):
    def __init__(self):
        super(Webclient, self).__init__()
        self._authtoken = None

    def login(self, email, password, *args, **kwargs):
        """
        Perform clientlogin then retrieve webclient cookies.

        :param email:
        :param password:
        """

        super(Webclient, self).login()

        res = ClientLogin.perform(self, email, password)

        if 'SID' not in res or 'Auth' not in res:
            return False

        self._authtoken = res['Auth']

        # Get webclient cookies.
        # They're stored automatically by requests on the webclient session.
        try:
            webclient.Init.perform(self)
        except CallFailure:
            # throw away clientlogin credentials
            self.logout()
        else:
            self.is_authenticated = True

        return self.is_authenticated

    def _send_with_auth(self, req_kwargs, desired_auth):
        if desired_auth.sso:
            req_kwargs['headers'] = req_kwargs.get('headers', {})

            # does this ever expire? would we have to perform clientlogin again?
            req_kwargs['headers']['Authorization'] = \
                'GoogleLogin auth=' + self._authtoken

        if desired_auth.xt:
            req_kwargs['params'] = req_kwargs.get('params', {})
            req_kwargs['params'].update({'u': 0, 'xt': self._rsession.cookies['xt']})

        return self._rsession.request(**req_kwargs)


class Musicmanager(_Base):
    def __init__(self):
        super(Musicmanager, self).__init__()
        self._oauth_creds = None

    def login(self, oauth_credentials, *args, **kwargs):
        """Store an already-acquired oauth2client.Credentials."""
        super(Musicmanager, self).login()

        self._oauth_creds = oauth_credentials
        self.is_authenticated = True

    def _send_with_auth(self, req_kwargs, desired_auth):
        if desired_auth.oauth:
            if self._oauth_creds.access_token_expired:
                self._oauth_creds.refresh(httplib2.Http())

            req_kwargs['headers'] = req_kwargs.get('headers', {})
            req_kwargs['headers']['Authorization'] = \
                'Bearer ' + self._oauth_creds.access_token

        return self._rsession.request(**req_kwargs)
