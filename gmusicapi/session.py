import requests

from gmusicapi.exceptions import (
    AlreadyLoggedIn, NotLoggedIn
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

        self.webclient.headers.update(
            {'Authorization': 'GoogleLogin auth=' + res['Auth']}
        )
        self.musicmanager.cookies.update(
            {'SID': res['SID']}
        )

        # Get webclient cookies.
        res = webclient.Init(self)

        if res.status_code == 403:
            # throw away ClientLogin auth
            self.logout()
        else:
            self.is_authenticated = True

        return self.is_authenticated

    def logout(self):
        """
        Resets the session to an unauthenticated default state.
        """
        self.__init__()

    def send(self, request, auth, session_options):
        """Send a request from a Call using this session's auth.

        :param request: filled requests.Request.
        :param auth: 3-tuple of bools (xt, clientlogin, sso) (ie Call.get_auth()).
        :param session_options: dict of kwargs to pass to requests.Session.send.
        """
        if any(auth) and not self.is_authenticated:
            raise NotLoggedIn

        send_xt, send_clientlogin, send_sso = auth

        # webclient is used by default -> SSO sent
        # hopefully nobody is using this to make requests of other places?
        session = self.webclient
        if send_clientlogin:
            session = self.musicmanager

        # webclient doesn't imply xt
        if send_xt:
            #request.params['u'] = 0
            request.params['xt'] = session.cookies.get('xt')

        prepped = request.prepare()

        res = session.send(prepped, **session_options)
        return res
