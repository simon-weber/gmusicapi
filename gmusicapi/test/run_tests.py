from functools import partial, update_wrapper
from getpass import getpass
import logging
import os
import sys
from types import MethodType

from proboscis import TestProgram

from gmusicapi.clients import Webclient, Musicmanager
from gmusicapi.protocol.musicmanager import credentials_from_refresh_token
from gmusicapi.test import local_tests, server_tests
from gmusicapi.test.utils import NoticeLogging

travis_id = 'E9:40:01:0E:51:7A'
travis_name = "Travis-CI (gmusicapi)"

# pretend to use test modules to appease flake8
# these need to be imported for implicit test discovery
_, _ = local_tests, server_tests


def freeze_login_details():
    """Searches the environment for credentials, and freezes them to
    client.login if found.

    If no auth is present in the env, the user is prompted. OAuth is read from
    the default path.

    If running on Travis, the prompt will never be fired; sys.exit is called
    if the envvars are not present.
    """

    #Attempt to get auth from environ.
    user, passwd, refresh_tok = [os.environ.get(name) for name in
                                 ('GM_USER',
                                  'GM_PASS',
                                  'GM_OAUTH')]

    on_travis = os.environ.get('TRAVIS')

    mm_kwargs = {}
    wc_kwargs = {}

    has_env_auth = user and passwd and refresh_tok

    if not has_env_auth and on_travis:
        print 'on Travis but could not read auth from environ; quitting.'
        sys.exit(1)

    if os.environ.get('TRAVIS'):
        #Travis runs on VMs with no "real" mac - we have to provide one.
        mm_kwargs.update({'uploader_id': travis_id,
                          'uploader_name': travis_name})

    if has_env_auth:
        wc_kwargs.update({'email': user, 'password': passwd})

        # mm expects a full OAuth2Credentials object
        credentials = credentials_from_refresh_token(refresh_tok)
        mm_kwargs.update({'oauth_credentials': credentials})

    else:
        # no travis, no credentials

        # we need to login here to verify their credentials.
        # the authenticated api is then thrown away.

        wclient = Webclient()
        valid_auth = False

        print ("These tests will never delete or modify your music."
               "\n\n"
               "If the tests fail, you *might* end up with a test"
               " song/playlist in your library, though."
               "You must have oauth credentials stored at the default"
               " path by Musicmanager.perform_oauth prior to running.")

        while not valid_auth:
            print
            email = raw_input("Email: ")
            passwd = getpass()

            valid_auth = wclient.login(email, passwd)

        wc_kwargs.update({'email': email, 'password': passwd})

    # globally freeze our params in place.
    # they can still be overridden manually; they're just the defaults now.
    Musicmanager.login = MethodType(
        update_wrapper(partial(Musicmanager.login, **mm_kwargs), Musicmanager.login),
        None, Musicmanager
    )

    Webclient.login = MethodType(
        update_wrapper(partial(Webclient.login, **wc_kwargs), Webclient.login),
        None, Webclient
    )


def main():
    if '--group=local' not in sys.argv:
        freeze_login_details()

    root_logger = logging.getLogger('gmusicapi')
    # using DynamicClientLoggers eliminates the need for root handlers
    # configure_debug_log_handlers(root_logger)

    # warnings typically signal a change in protocol,
    # so fail the build if anything >= warning are sent,

    noticer = NoticeLogging()
    noticer.setLevel(logging.WARNING)
    root_logger.addHandler(noticer)

    # proboscis does not have an exit=False equivalent,
    # so SystemExit must be caught instead (we need
    # to check the log noticer)
    try:
        TestProgram().run_and_exit()
    except SystemExit as e:
        print
        if noticer.seen_message:
            print '(failing build due to log warnings)'
            sys.exit(1)

        if e.code is not None:
            sys.exit(e.code)

if __name__ == '__main__':
    main()
