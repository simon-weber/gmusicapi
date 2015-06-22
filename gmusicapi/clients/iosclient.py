import os
import webbrowser

from oauth2client.client import OAuth2WebServerFlow
import oauth2client.file

from gmusicapi.utils import utils
from gmusicapi.protocol import iosclient
from gmusicapi.compat import my_appdirs
from gmusicapi.clients.shared import _Base
from gmusicapi import session

OAUTH_FILEPATH = os.path.join(my_appdirs.user_data_dir, 'ios.oauth.cred')


class IOSClient(_Base):

    _session_class = session.Musicmanager

    @staticmethod
    def perform_oauth(storage_filepath=OAUTH_FILEPATH, open_browser=False):
        """Provides a series of prompts for a user to follow to authenticate.
        Returns ``oauth2client.client.OAuth2Credentials`` when successful.

        In most cases, this should only be run once per machine to store
        credentials to disk, then never be needed again.

        If the user refuses to give access,
        ``oauth2client.client.FlowExchangeError`` is raised.

        :param storage_filepath: a filepath to write the credentials to,
          or ``None``
          to not write the credentials to disk (which is not recommended).

          `Appdirs <https://pypi.python.org/pypi/appdirs>`__
          ``user_data_dir`` is used by default. Users can run::

              import gmusicapi.clients
              print gmusicapi.clients.OAUTH_FILEPATH

          to see the exact location on their system.

        :param open_browser: if True, attempt to open the auth url
          in the system default web browser. The url will be printed
          regardless of this param's setting.

        This flow is intentionally very simple.
        For complete control over the OAuth flow, pass an
        ``oauth2client.client.OAuth2Credentials``
        to :func:`login` instead.
        """

        flow = OAuth2WebServerFlow(*iosclient.oauth)

        auth_uri = flow.step1_get_authorize_url()
        print
        print "Visit the following url:\n %s" % auth_uri

        if open_browser:
            print
            print 'Opening your browser to it now...',
            webbrowser.open(auth_uri)
            print 'done.'
            print "If you don't see your browser, you can just copy and paste the url."
            print

        code = raw_input("Follow the prompts,"
                         " then paste the auth code here and hit enter: ")

        credentials = flow.step2_exchange(code)

        if storage_filepath is not None:
            if storage_filepath == OAUTH_FILEPATH:
                utils.make_sure_path_exists(os.path.dirname(OAUTH_FILEPATH), 0o700)
            storage = oauth2client.file.Storage(storage_filepath)
            storage.put(credentials)

        return credentials

    def __init__(self, debug_logging=True, validate=True, verify_ssl=True):
        super(IOSClient, self).__init__(self.__class__.__name__,
                                        debug_logging,
                                        validate,
                                        verify_ssl)
        self.request_num = 0

    def login(self, oauth_credentials=OAUTH_FILEPATH,
              uploader_id=None, uploader_name=None):
        """Authenticates the Music Manager using OAuth.
        Returns ``True`` on success, ``False`` on failure.

        Unlike the :class:`Webclient`, OAuth allows authentication without
        providing plaintext credentials to the application.

        In most cases, the default parameters should be acceptable. Users on
        virtual machines will want to provide `uploader_id`.

        :param oauth_credentials: ``oauth2client.client.OAuth2Credentials`` or the path to a
          ``oauth2client.file.Storage`` file. By default, the same default path used by
          :func:`perform_oauth` is used.

          Endusers will likely call :func:`perform_oauth` once to write
          credentials to disk and then ignore this parameter.

          This param
          is mostly intended to allow flexibility for developers of a
          3rd party service who intend to perform their own OAuth flow
          (eg on their website).

        :param uploader_id: a unique id as a MAC address, eg ``'00:11:22:33:AA:BB'``.
          This should only be provided in cases where the default
          (host MAC address incremented by 1) will not work.

          Upload behavior is undefined if a Music Manager uses the same id, especially when
          reporting bad matches.

          ``ValueError`` will be raised if this is provided but not in the proper form.

          ``OSError`` will be raised if this is not provided and a real MAC could not be
          determined (most common when running on a VPS).

          If provided, use the same id on all future runs for this machine,
          because of the upload device limit explained below.

        :param uploader_name: human-readable non-unique id; default is
          ``"<hostname> (gmusicapi-{version})"``.

          This doesn't appear to be a part of authentication at all.
          Registering with (id, name = X, Y) and logging in with
          (id, name = X, Z) works, and does not change the server-stored
          uploader_name.

        There are hard limits on how many upload devices can be registered; refer to `Google's
        docs <http://support.google.com/googleplay/bin/answer.py?hl=en&answer=1230356>`__. There
        have been limits on deauthorizing devices in the past, so it's smart not to register
        more devices than necessary.
        """

        return self._oauth_login(oauth_credentials)

    def _oauth_login(self, oauth_credentials):
        """Auth ourselves to the MM oauth endpoint.

        Return True on success; see :py:func:`login` for params.
        """

        if isinstance(oauth_credentials, basestring):
            oauth_file = oauth_credentials
            if oauth_file == OAUTH_FILEPATH:
                utils.make_sure_path_exists(os.path.dirname(OAUTH_FILEPATH), 0o700)
            storage = oauth2client.file.Storage(oauth_file)

            oauth_credentials = storage.get()
            if oauth_credentials is None:
                self.logger.warning("could not retrieve oauth credentials from '%s'", oauth_file)
                return False

        if not self.session.login(oauth_credentials):
            self.logger.warning("failed to authenticate")
            return False

        self.logger.info("oauth successful")

        return True

    def list_config(self):
        self.request_num += 1
        return self._make_call(iosclient.ConfigList, self.request_num)
