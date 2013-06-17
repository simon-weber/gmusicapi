#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import namedtuple
from functools import partial, update_wrapper
from getpass import getpass
import logging
import os
import sys
from types import MethodType

from proboscis import TestProgram

from gmusicapi.clients import Webclient, Musicmanager, OAUTH_FILEPATH
from gmusicapi.protocol.musicmanager import credentials_from_refresh_token
from gmusicapi.test import local_tests, server_tests  # noqa
from gmusicapi.test.utils import NoticeLogging

EnvArg = namedtuple('EnvArg', 'envarg kwarg description')

wc_envargs = (
    EnvArg('GM_USER', 'email', 'WC user. If not present, user will be prompted.'),
    EnvArg('GM_PASS', 'password', 'WC password. If not present, user will be prompted.'),
)

mm_envargs = (
    EnvArg('GM_OAUTH', 'oauth_credentials', 'MM refresh token. Defaults to MM.login default.'),
    EnvArg('GM_UP_ID', 'uploader_id', 'MM uploader id. Defaults to MM.login default.'),
    EnvArg('GM_UP_NAME', 'uploader_name', 'MM uploader name. Default to MM.login default.'),
)


def prompt_for_wc_auth():
    """Return a valid (user, pass) tuple by continually
    prompting the user."""

    print ("These tests will never delete or modify your music."
           "\n\n"
           "If the tests fail, you *might* end up with a test"
           " song/playlist in your library, though."
           "\n")

    wclient = Webclient()
    valid_wc_auth = False

    while not valid_wc_auth:
        print
        email = raw_input("Email: ")
        passwd = getpass()

        valid_wc_auth = wclient.login(email, passwd)

    return email, passwd


def retrieve_auth():
    """Searches the env for auth, prompting the user if necessary.

    On success, return (wc_kwargs, mm_kwargs). On failure, raise ValueError."""

    get_kwargs = lambda envargs: dict([(arg.kwarg, os.environ.get(arg.envarg))
                                       for arg in envargs])

    wc_kwargs = get_kwargs(wc_envargs)
    mm_kwargs = get_kwargs(mm_envargs)

    if not all([wc_kwargs[arg] for arg in ('email', 'password')]):
        if os.environ.get('TRAVIS'):
            print 'on Travis but could not read auth from environ; quitting.'
            sys.exit(1)

        wc_kwargs.update(zip(['email', 'password'], prompt_for_wc_auth()))

    if mm_kwargs['oauth_credentials'] is None:
        # ignoring race
        if not os.path.isfile(OAUTH_FILEPATH):
            raise ValueError("You must have oauth credentials stored at the default"
                             " path by Musicmanager.perform_oauth prior to running.")
        del mm_kwargs['oauth_credentials']  # mm default is not None
    else:
        mm_kwargs['oauth_credentials'] = \
            credentials_from_refresh_token(mm_kwargs['oauth_credentials'])

    return (wc_kwargs, mm_kwargs)


def freeze_login_details(wc_kwargs, mm_kwargs):
    """Set the given kwargs to be the default for client login methods."""
    for cls, kwargs in ((Musicmanager, mm_kwargs),
                        (Webclient, wc_kwargs)):
        cls.login = MethodType(
            update_wrapper(partial(cls.login, **kwargs), cls.login),
            None, cls)


def main():
    """Search env for auth envargs and run tests."""

    if '--group=local' not in sys.argv:
        # hack: assume we're just running the proboscis local group
        freeze_login_details(*retrieve_auth())

    # warnings typically signal a change in protocol,
    # so fail the build if anything >= warning are sent,
    noticer = NoticeLogging()
    noticer.setLevel(logging.WARNING)
    root_logger = logging.getLogger('gmusicapi')
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
