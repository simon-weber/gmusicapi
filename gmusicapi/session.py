# -*- coding: utf-8 -*-

"""
Sessions handle the details of authentication and transporting requests.
"""
from __future__ import print_function, division, absolute_import, unicode_literals
from builtins import *  # noqa

from contextlib import closing

import gpsoauth
import httplib2  # included with oauth2client
import mechanicalsoup
import oauth2client
import requests

from gmusicapi.exceptions import (
    AlreadyLoggedIn, NotLoggedIn, CallFailure
)
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
    def login(self, email, password, *args, **kwargs):
        """
        Perform serviceloginauth then retrieve webclient cookies.

        :param email:
        :param password:
        """
        super(Webclient, self).login()

        # Google's login form has a bunch of hidden fields I'd rather not deal with manually.
        browser = mechanicalsoup.Browser(soup_config={"features": "html.parser"})

        login_page = browser.get('https://accounts.google.com/ServiceLoginAuth',
                                 params={'service': 'sj',
                                         'continue': 'https://play.google.com/music/listen'})
        form_candidates = login_page.soup.select("form")
        if len(form_candidates) > 1:
            log.error("Google login form dom has changed; there are %s candidate forms:\n%s",
                      len(form_candidates), form_candidates)
            return False

        form = form_candidates[0]
        form.select("#Email")[0]['value'] = email

        response = browser.submit(form, 'https://accounts.google.com/AccountLoginInfo')

        try:
            response.raise_for_status()
        except requests.HTTPError:
            log.exception("submitting login form failed")
            return False

        form_candidates = response.soup.select("form")
        if len(form_candidates) > 1:
            log.error("Google login form dom has changed; there are %s candidate forms:\n%s",
                      len(form_candidates), form_candidates)
            return False

        form = form_candidates[0]
        form.select("#Passwd")[0]['value'] = password

        response = browser.submit(form, 'https://accounts.google.com/ServiceLoginAuth')

        try:
            response.raise_for_status()
        except requests.HTTPError:
            log.exception("submitting login form failed")
            return False

        # We can't use in without .keys(), since international users will see a
        # CookieConflictError.
        if 'SID' not in list(browser.session.cookies.keys()):
            # Invalid auth.
            return False

        self._rsession.cookies.update(browser.session.cookies)
        self.is_authenticated = True

        # Get webclient cookies.
        # They're stored automatically by requests on the webclient session.
        try:
            webclient.Init.perform(self, True)
        except CallFailure:
            log.exception("unable to initialize webclient cookies")
            self.logout()

        return self.is_authenticated

    def _send_with_auth(self, req_kwargs, desired_auth, rsession):
        if desired_auth.xt:
            req_kwargs.setdefault('params', {})

            req_kwargs['params'].update({'u': 0, 'xt': rsession.cookies['xt']})

        return rsession.request(**req_kwargs)


class Mobileclient(_Base):
    def __init__(self, *args, **kwargs):
        super(Mobileclient, self).__init__(*args, **kwargs)
        self._master_token = None
        self._authtoken = None
        self._locale = None
        self._is_subscribed = None

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
            # Default to English (United States) if no locale given.
            if not self._locale:
                self._locale = 'en_US'

            # Set locale for all Mobileclient calls.
            req_kwargs.setdefault('params', {})
            req_kwargs['params'].update({'hl': self._locale})

            # As of API v2.5, dv is a required parameter for all calls.
            # The dv value is part of the Android app version number,
            # but setting this to 0 works fine.
            req_kwargs['params'].update({'dv': 0})

            if self._is_subscribed:
                req_kwargs['params'].update({'tier': 'aa'})
            else:
                req_kwargs['params'].update({'tier': 'fr'})

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
