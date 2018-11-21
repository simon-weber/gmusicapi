#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals
from future.utils import PY3, bind_method
from builtins import *  # noqa

from collections import namedtuple
import functools
import logging
import os
import sys

from proboscis import TestProgram

from gmusicapi.clients import Musicmanager, Mobileclient
from gmusicapi import session
from gmusicapi.test import local_tests, server_tests  # noqa
from gmusicapi.test.utils import NoticeLogging

EnvArg = namedtuple('EnvArg', 'envarg is_required kwarg description')

# these names needed to be compressed to fit everything into the travisci key size.
# there's also:
#    * GM_A: when set (to anything) states that we are testing on a subscription account.
#    * GM_AA_D_ID: a registered device id for use with mc streaming

# wc_envargs = (
#     EnvArg('GM_U', 'email', 'WC user. If not present, user will be prompted.'),
#     EnvArg('GM_P', 'password', 'WC password. If not present, user will be prompted.'),
# )

mc_envargs = (
    EnvArg('GM_AA_D_ID', True, 'device_id', 'a registered device id for use with MC streaming'),
    EnvArg('GM_R', False, 'oauth_credentials', 'an MC refresh token (defaults to MC.login default)'),
)

mm_envargs = (
    EnvArg('GM_O', False, 'oauth_credentials', 'an MM refresh token (defaults to MM.login default)'),
    EnvArg('GM_I', False, 'uploader_id', 'an MM uploader id (defaults to MM.login default)'),
    EnvArg('GM_N', False, 'uploader_name', 'an MM uploader name (default to MM.login default)'),
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


def _get_kwargs(envargs):
    kwargs = {}
    for arg in envargs:
        if arg.is_required and arg.envarg not in os.environ:
            raise ValueError("%s was not exported and must be %s" % (arg.envarg, arg.description))

        val = os.environ.get(arg.envarg)

        if arg.kwarg == 'oauth_credentials' and val is not None:
            oauth_info = session.Musicmanager.oauth if arg.envarg == 'GM_O' else session.Mobileclient.oauth
            kwargs['oauth_credentials'] = session.credentials_from_refresh_token(val, oauth_info)
        else:
            kwargs[arg.kwarg] = val

    return kwargs


def retrieve_auth():
    """Searches the env for auth.

    On success, return (mc_kwargs, mm_kwargs). On failure, raise ValueError."""

    mc_kwargs = _get_kwargs(mc_envargs)
    mm_kwargs = _get_kwargs(mm_envargs)

    return (mc_kwargs, mm_kwargs)


def freeze_method_kwargs(klass, method_name, **kwargs):
    method = getattr(klass, method_name)
    partialfunc = functools.partialmethod if PY3 else functools.partial
    bind_method(klass, method_name, partialfunc(method, **kwargs))


def freeze_login_details(mc_kwargs, mm_kwargs):
    """Set the given kwargs to be the default for client login methods."""

    freeze_method_kwargs(Musicmanager, 'login', **mm_kwargs)
    freeze_method_kwargs(Mobileclient, 'oauth_login', **mc_kwargs)


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
