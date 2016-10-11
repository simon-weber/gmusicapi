#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals
from future.utils import PY3, bind_method
from builtins import *  # noqa

from collections import namedtuple
import functools
from getpass import getpass
import logging
import os
import sys

from proboscis import TestProgram

from gmusicapi.clients import Musicmanager, Mobileclient, OAUTH_FILEPATH
from gmusicapi.protocol.musicmanager import credentials_from_refresh_token
from gmusicapi.test import local_tests, server_tests  # noqa
from gmusicapi.test.utils import NoticeLogging

EnvArg = namedtuple('EnvArg', 'envarg kwarg description')

# these names needed to be compressed to fit everything into the travisci key size.
# there's also:
#    * GM_A: when set (to anything) states that we are testing on a subscription account.
#    * GM_AA_D_ID: a registered device id for use with mc streaming

wc_envargs = (
    EnvArg('GM_U', 'email', 'WC user. If not present, user will be prompted.'),
    EnvArg('GM_P', 'password', 'WC password. If not present, user will be prompted.'),
)

mc_envargs = (
    EnvArg('GM_U', 'email', 'MC user. If not present, user will be prompted.'),
    EnvArg('GM_P', 'password', 'MC password. If not present, user will be prompted.'),
    EnvArg('GM_AA_D_ID', 'android_id', 'A registered device id for use with MC streaming'),
)

mm_envargs = (
    EnvArg('GM_O', 'oauth_credentials', 'MM refresh token. Defaults to MM.login default.'),
    EnvArg('GM_I', 'uploader_id', 'MM uploader id. Defaults to MM.login default.'),
    EnvArg('GM_N', 'uploader_name', 'MM uploader name. Default to MM.login default.'),
)


# Webclient auth retreival removed while testing disabled.
#
# def prompt_for_wc_auth():
#     """Return a valid (user, pass) tuple by continually
#     prompting the user."""
#
#     print("These tests will never delete or modify your music."
#           "\n\n"
#           "If the tests fail, you *might* end up with a test"
#           " song/playlist in your library, though."
#           "\n")
#
#     wclient = Webclient()
#     valid_wc_auth = False
#
#     while not valid_wc_auth:
#         print()
#         email = input("Email: ")
#         passwd = getpass()
#
#         valid_wc_auth = wclient.login(email, passwd)
#
#     return email, passwd


def prompt_for_mc_auth():
    """Return a valid (user, pass, android_id) tuple by continually
    prompting the user."""

    print("These tests will never delete or modify your music."
          "\n\n"
          "If the tests fail, you *might* end up with a test"
          " song/playlist in your library, though."
          "\n")

    mclient = Mobileclient()
    valid_mc_auth = False

    while not valid_mc_auth:
        print()
        email = input("Email: ")
        passwd = getpass()

        try:
            android_id = os.environ['GM_AA_D_ID']
        except KeyError:
            android_id = input("Device ID ('mac' for FROM_MAC_ADDRESS): ")

        if android_id == "mac":
            android_id = Mobileclient.FROM_MAC_ADDRESS

        if not android_id:
            print('a device id must be provided')
            sys.exit(1)

        valid_mc_auth = mclient.login(email, passwd, android_id)

    return email, passwd, android_id


def retrieve_auth():
    """Searches the env for auth, prompting the user if necessary.

    On success, return (mc_kwargs, mm_kwargs). On failure, raise ValueError."""

    def get_kwargs(envargs):
        return dict([(arg.kwarg, os.environ.get(arg.envarg))
                     for arg in envargs])

    mc_kwargs = get_kwargs(mc_envargs)
    mm_kwargs = get_kwargs(mm_envargs)

    if not all([mc_kwargs[arg] for arg in ('email', 'password', 'android_id')]):
        if os.environ.get('TRAVIS'):
            print('on Travis but could not read auth from environ; quitting.')
            sys.exit(1)

        mc_kwargs.update(zip(['email', 'password', 'android_id'], prompt_for_mc_auth()))

    if mm_kwargs['oauth_credentials'] is None:
        # ignoring race
        if not os.path.isfile(OAUTH_FILEPATH):
            raise ValueError("You must have oauth credentials stored at the default"
                             " path by Musicmanager.perform_oauth prior to running.")
        del mm_kwargs['oauth_credentials']  # mm default is not None
    else:
        mm_kwargs['oauth_credentials'] = \
            credentials_from_refresh_token(mm_kwargs['oauth_credentials'])

    return (mc_kwargs, mm_kwargs)


def freeze_method_kwargs(klass, method_name, **kwargs):
    method = getattr(klass, method_name)
    partialfunc = functools.partialmethod if PY3 else functools.partial
    bind_method(klass, method_name, partialfunc(method, **kwargs))


def freeze_login_details(mc_kwargs, mm_kwargs):
    """Set the given kwargs to be the default for client login methods."""
    for cls, kwargs in ((Musicmanager, mm_kwargs),
                        (Mobileclient, mc_kwargs),
                        ):
        freeze_method_kwargs(cls, 'login', **kwargs)


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
        TestProgram(module=sys.modules[__name__]).run_and_exit()
    except SystemExit as e:
        print()
        if noticer.seen_message:
            print('(failing build due to log warnings)')
            sys.exit(1)

        if e.code is not None:
            sys.exit(e.code)

if __name__ == '__main__':
    main()
