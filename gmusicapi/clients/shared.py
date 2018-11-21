# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals
from builtins import *  # noqa
from past.builtins import basestring

import logging
import os

from gmusicapi.utils import utils
from future.utils import with_metaclass
from oauth2client.client import OAuth2WebServerFlow
import oauth2client.file
import webbrowser


class _Base(with_metaclass(utils.DocstringInheritMeta, object)):
    """Factors out common client setup."""
    _session_class = utils.NotImplementedField

    num_clients = 0  # used to disambiguate loggers

    def __init__(self, logger_basename, debug_logging, validate, verify_ssl):
        """

        :param debug_logging: each Client has a ``logger`` member.
          The logger is named ``gmusicapi.<client class><client number>`` and
          will propogate to the ``gmusicapi`` root logger.

          If this param is ``True``, handlers will be configured to send
          this client's debug log output to disk,
          with warnings and above printed to stderr.
          `Appdirs <https://pypi.python.org/pypi/appdirs>`__
          ``user_log_dir`` is used by default. Users can run::

              from gmusicapi.utils import utils
              print utils.log_filepath

          to see the exact location on their system.

          If ``False``, no handlers will be configured;
          users must create their own handlers.

          Completely ignoring logging is dangerous and not recommended.
          The Google Music protocol can change at any time; if
          something were to go wrong, the logs would be necessary for
          recovery.

        :param validate: if False, do not validate server responses against
          known schemas. This helps to catch protocol changes, but requires
          significant cpu work.

          This arg is stored as ``self.validate`` and can be safely
          modified at runtime.

        :param verify_ssl: if False, exceptions will not be raised if there
          are problems verifying SSL certificates.
          Be wary of using this option; it's almost always better to
          fix the machine's SSL configuration than to ignore errors.
        """
        # this isn't correct if init is called more than once, so we log the
        # client name below to avoid confusion for people reading logs
        _Base.num_clients += 1

        logger_name = "gmusicapi.%s%s" % (logger_basename,
                                          _Base.num_clients)
        self._cache = {}
        self.logger = logging.getLogger(logger_name)
        self.validate = validate
        self._verify_ssl = verify_ssl

        def setup_session(s):
            s.verify = self._verify_ssl

        self.session = self._session_class(rsession_setup=setup_session)

        if debug_logging:
            utils.configure_debug_log_handlers(self.logger)

        self.logger.info("initialized")
        self.logout()

    def _make_call(self, protocol, *args, **kwargs):
        """Returns the response of a protocol.Call.

        args/kwargs are passed to protocol.perform.

        CallFailure may be raised."""

        return protocol.perform(self.session, self.validate, *args, **kwargs)

    def is_authenticated(self):
        """Returns ``True`` if the Api can make an authenticated request."""
        return self.session.is_authenticated

    def logout(self):
        """Forgets local authentication and cached properties in this Api instance.
        Returns ``True`` on success."""

        # note to clients: this will be called during __init__.

        self.session.logout()
        self._cache.clear()  # Clear the instance of all cached properties.
        self.logger.info("logged out")
        return True


class _OAuthClient(_Base):

    _path_sentinel = object()

    # the default path for credential storage
    OAUTH_FILEPATH = utils.NotImplementedField

    @classmethod
    def perform_oauth(cls, storage_filepath=_path_sentinel, open_browser=False):
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
          ``user_data_dir`` is used by default. Check the OAUTH_FILEPATH field
          on this class to see the exact location that will be used.

        :param open_browser: if True, attempt to open the auth url
          in the system default web browser. The url will be printed
          regardless of this param's setting.

        This flow is intentionally very simple.
        For complete control over the OAuth flow, pass an
        ``oauth2client.client.OAuth2Credentials``
        to :func:`login` instead.
        """
        if storage_filepath is cls._path_sentinel:
            storage_filepath = cls.OAUTH_FILEPATH

        flow = OAuth2WebServerFlow(**cls._session_class.oauth._asdict())

        auth_uri = flow.step1_get_authorize_url()
        print()
        print("Visit the following url:\n %s" % auth_uri)

        if open_browser:
            print()
            print('Opening your browser to it now...', end=' ')
            webbrowser.open(auth_uri)
            print('done.')
            print("If you don't see your browser, you can just copy and paste the url.")
            print()

        code = input("Follow the prompts, then paste the auth code here and hit enter: ")

        credentials = flow.step2_exchange(code)

        if storage_filepath is not None:
            if storage_filepath == cls.OAUTH_FILEPATH:
                utils.make_sure_path_exists(os.path.dirname(cls.OAUTH_FILEPATH), 0o700)
            storage = oauth2client.file.Storage(storage_filepath)
            storage.put(credentials)

        return credentials

    def _oauth_login(self, oauth_credentials):
        """Return True on success."""

        if isinstance(oauth_credentials, basestring):
            oauth_file = oauth_credentials
            if oauth_file == self.OAUTH_FILEPATH:
                utils.make_sure_path_exists(os.path.dirname(self.OAUTH_FILEPATH), 0o700)
            storage = oauth2client.file.Storage(oauth_file)

            oauth_credentials = storage.get()
            if oauth_credentials is None:
                self.logger.warning("could not retrieve oauth credentials from '%r'", oauth_file)
                return False

        if not self.session.login(oauth_credentials):
            self.logger.warning("failed to authenticate")
            return False

        self.logger.info("oauth successful")

        return True
