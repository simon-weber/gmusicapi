import requests

from gmusicapi.exceptions import (
    AlreadyLoggedIn, NotLoggedIn, CallFailure
)
from gmusicapi.protocol.shared import ClientLogin
from gmusicapi.protocol import webclient


class PlaySession(object):
    """A PlaySession handles authentication."""

    def __init__(self):
        """Init an unauthenticated session."""
        self.webclient = requests.Session()
        self.musicmanager = requests.Session()
        self.is_authenticated = False

    def login(self, email, password):
        """
        Attempt to login. Return ``True`` if the login was successful.
        Raise AlreadyLoggedIn if the session is already authenticated.

        :param email:
        :param password:
        """
        if self.is_authenticated:
            raise AlreadyLoggedIn

        # Perform ClientLogin.
        res = ClientLogin.perform(self, email, password)

        if 'SID' not in res or 'Auth' not in res:
            return False

        self.webclient.headers['Authorization'] = 'GoogleLogin auth=' + res['Auth']
        self.musicmanager.cookies['SID'] = res['SID']

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

    def logout(self):
        """
        Resets the session to an unauthenticated default state.
        """
        self.webclient.close()
        self.musicmanager.close()
        self.__init__()

    def send(self, req_kwargs, auth):
        """Send a request from a Call using this session's auth.

        :param req_kwargs: filled requests.req_kwargs.
        :param auth: 3-tuple of bools (xt, clientlogin, sso) (ie Call.get_auth()).
        """
        if any(auth) and not self.is_authenticated:
            raise NotLoggedIn

        send_xt, send_clientlogin, send_sso = auth

        # webclient is used by default -> SSO sent
        # hopefully nobody is using this to make requests of other places?
        session = self.webclient
        if send_clientlogin:
            session = self.musicmanager

        # webclient doesn't imply xt, eg /listen
        if send_xt:
            if 'params' not in req_kwargs:
                req_kwargs['params'] = {}
            req_kwargs['params']['u'] = 0
            req_kwargs['params']['xt'] = session.cookies.get('xt')

        res = session.request(**req_kwargs)

        return res
