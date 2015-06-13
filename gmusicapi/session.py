# -*- coding: utf-8 -*-

"""
Sessions handle the details of authentication and transporting requests.
"""
from contextlib import closing
import cookielib

import gpsoauth
import oauth2client
import httplib2  # included with oauth2client
import requests

from gmusicapi.exceptions import (
    AlreadyLoggedIn, NotLoggedIn, CallFailure
)
from gmusicapi.protocol.shared import ClientLogin
from gmusicapi.protocol import webclient
from gmusicapi.utils import utils

log = utils.DynamicClientLogger(__name__)


class _Base(object):
    def __init__(self, rsession_setup=None):
        """
        :param rsession_setup: a callable that will be called with
          the backing requests.Session to delegate config to callers.
        """
        self._rsession = requests.Session()

        if rsession_setup is None:
            rsession_setup = lambda x: x  # noqa
        self._rsession_setup = rsession_setup
        self._rsession_setup(self._rsession)

        self.is_authenticated = False

    def _send_with_auth(self, req_kwargs, desired_auth, rsession):
        raise NotImplementedError

    def _send_without_auth(self, req_kwargs, rsession):
        return rsession.request(**req_kwargs)

    def login(self, *args, **kwargs):
        # subclasses extend / use super()
        if self.is_authenticated:
            raise AlreadyLoggedIn

    def logout(self):
        """
        Reset the session to an unauthenticated, default state.
        """
        self._rsession.close()

        self._rsession = requests.Session()
        self._rsession_setup(self._rsession)

        self.is_authenticated = False

    def send(self, req_kwargs, desired_auth, rsession=None):
        """Send a request from a Call using this session's auth.

        :param req_kwargs: kwargs for requests.Session.request
        :param desired_auth: protocol.shared.AuthTypes to attach
        :param rsession: (optional) a requests.Session to use
          (default ``self._rsession`` - this is exposed for test purposes)
        """
        res = None

        if not any(desired_auth):
            if rsession is None:
                # use a throwaway session to ensure it's clean
                with closing(requests.Session()) as new_session:
                    self._rsession_setup(new_session)
                    res = self._send_without_auth(req_kwargs, new_session)
            else:
                res = self._send_without_auth(req_kwargs, rsession)

        else:
            if not self.is_authenticated:
                raise NotLoggedIn

            if rsession is None:
                rsession = self._rsession

            res = self._send_with_auth(req_kwargs, desired_auth, rsession)

        return res


class Webclient(_Base):
    def __init__(self, *args, **kwargs):
        super(Webclient, self).__init__(*args, **kwargs)
        self._authtoken = None

    def login(self, email, password, *args, **kwargs):
        """
        Perform clientlogin then retrieve webclient cookies.

        :param email:
        :param password:
        """

        super(Webclient, self).login()

        try:
            res = ClientLogin.perform(self, True, email, password)
        except CallFailure:
            self.logout()
            return self.is_authenticated

        if 'SID' not in res or 'Auth' not in res:
            return False

        self._authtoken = res['Auth']

        self.is_authenticated = True

        # Get webclient cookies.
        # They're stored automatically by requests on the webclient session.
        try:
            webclient.Init.perform(self, True)
        except CallFailure:
            # throw away clientlogin credentials
            self.logout()

        return self.is_authenticated

    def _send_with_auth(self, req_kwargs, desired_auth, rsession):
        if desired_auth.sso:
            req_kwargs.setdefault('headers', {})

            # does this ever expire? would we have to perform clientlogin again?
            req_kwargs['headers']['Authorization'] = \
                'GoogleLogin auth=' + self._authtoken

        if desired_auth.xt:
            req_kwargs.setdefault('params', {})

            req_kwargs['params'].update({'u': 0, 'xt': rsession.cookies['xt']})

        return rsession.request(**req_kwargs)


class Mobileclient(_Base):
    def __init__(self, *args, **kwargs):
        super(Mobileclient, self).__init__(*args, **kwargs)
        self._master_token = None
        self._authtoken = None

    def login(self, email, password, android_id, *args, **kwargs):
        """
        Get a master token, then use it to get a skyjam OAuth token.

        :param email:
        :param password:
        :param android_id:
        """

        super(Mobileclient, self).login(email, password, android_id, *args, **kwargs)

        res = gpsoauth.perform_master_login(email, password, android_id)
        if 'Token' not in res:
            return False
        self._master_token = res['Token']

        res = gpsoauth.perform_oauth(
            email, self._master_token, android_id,
            service='sj', app='com.google.android.music',
            client_sig='38918a453d07199354f8b19af05ec6562ced5788')
        if 'Auth' not in res:
            return False
        self._authtoken = res['Auth']

        self.is_authenticated = True

        return True

    def _send_with_auth(self, req_kwargs, desired_auth, rsession):
        if desired_auth.oauth:
            req_kwargs.setdefault('headers', {})

            # does this expire?
            req_kwargs['headers']['Authorization'] = \
                'GoogleLogin auth=' + self._authtoken

        return rsession.request(**req_kwargs)


class Musicmanager(_Base):
    def __init__(self, *args, **kwargs):
        super(Musicmanager, self).__init__(*args, **kwargs)
        self._oauth_creds = None

    def login(self, oauth_credentials, *args, **kwargs):
        """Store an already-acquired oauth2client.Credentials."""
        super(Musicmanager, self).login()

        try:
            # refresh the token right away to check auth validity
            oauth_credentials.refresh(httplib2.Http())
        except oauth2client.client.Error:
            log.exception("error when refreshing oauth credentials")

        if oauth_credentials.access_token_expired:
            log.info("could not refresh oauth credentials")
            return False

        self._oauth_creds = oauth_credentials
        self.is_authenticated = True

        return self.is_authenticated

    def _send_with_auth(self, req_kwargs, desired_auth, rsession):
        if desired_auth.oauth:
            if self._oauth_creds.access_token_expired:
                self._oauth_creds.refresh(httplib2.Http())

            req_kwargs['headers'] = req_kwargs.get('headers', {})
            req_kwargs['headers']['Authorization'] = \
                'Bearer ' + self._oauth_creds.access_token

        return rsession.request(**req_kwargs)
