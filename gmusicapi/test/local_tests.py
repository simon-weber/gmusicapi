# -*- coding: utf-8 -*-

"""
Tests that don't hit the Google Music servers.
"""
from __future__ import print_function, division, absolute_import, unicode_literals
from builtins import *  # noqa

from collections import namedtuple
import os
import time

from mock import MagicMock
from proboscis.asserts import (
    assert_raises, assert_true, assert_false, assert_equal,
    assert_is_not, Check
)
from proboscis import test

import gmusicapi.session
from gmusicapi.clients import Mobileclient, Musicmanager
from gmusicapi.exceptions import AlreadyLoggedIn
from gmusicapi.protocol.shared import authtypes
from gmusicapi.protocol import mobileclient
from gmusicapi.utils import utils, jsarray

jsarray_samples = []
jsarray_filenames = [base + '.jsarray' for base in ('searchresult', 'fetchartist')]

test_file_dir = os.path.dirname(os.path.abspath(__file__))
for filepath in [os.path.join(test_file_dir, p) for p in jsarray_filenames]:
    with open(filepath, 'r', encoding="utf-8") as f:
        jsarray_samples.append(f.read())

# TODO test gather_local, transcoding

# All tests end up in the local group.
test = test(groups=['local'])


@test
def longest_increasing_sub():
    lisi = utils.longest_increasing_subseq
    assert_equal(lisi([]), [])
    assert_equal(lisi(list(range(10, 0, -1))), [1])
    assert_equal(lisi(list(range(10, 20))), list(range(10, 20)))
    assert_equal(lisi([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9]),
                 [1, 2, 3, 5, 8, 9])

#
# clients
#
# this feels like a dumb pattern, but I can't think of a better way
names = ('Mobileclient', 'Musicmanager')  # Webclient removed since testing is disabled.
Clients = namedtuple('Clients', [n.lower() for n in names])


def create_clients():
    clients = []
    for name in names:
        cls = getattr(gmusicapi.clients, name)
        c = cls()

        # mock out the underlying session
        c.session = MagicMock()
        clients.append(c)

    return Clients(*clients)


@test
def no_client_auth_initially():
    # wc = Webclient()
    # assert_false(wc.is_authenticated())

    mc = Mobileclient()
    assert_false(mc.is_authenticated())

    mm = Musicmanager()
    assert_false(mm.is_authenticated())


@test
def mm_prevents_bad_mac_format():
    mm = create_clients().musicmanager

    with Check() as check:
        for bad_mac in ['bogus',
                        '11:22:33:44:55:66:',
                        '11:22:33:44:55:ab',
                        '11:22:33:44:55']:
            check.raises(
                ValueError,
                mm._perform_upauth,
                uploader_id=bad_mac,
                uploader_name='valid')


# @test
# def auto_playlists_are_empty():
#     # this doesn't actually hit the server at the moment.
#     # see issue 102
#     api = Api()
#     assert_equal(api.get_all_playlist_ids(auto=True, user=False),
#                  {'auto': {}})

#
# sessions
#
Sessions = namedtuple('Sessions', [n.lower() for n in names])


def create_sessions():
    sessions = []
    for name in names:
        cls = getattr(gmusicapi.session, name)
        s = cls()

        # mock out the underlying requests.session
        s._rsession = MagicMock()
        sessions.append(s)

    return Sessions(*sessions)


@test
def no_session_auth_initially():
    for s in create_sessions():
        assert_false(s.is_authenticated)


@test
def session_raises_alreadyloggedin():
    for s in create_sessions():
        s.is_authenticated = True

        def login():
            # hackish: login ignores args so we can test them all here;
            # this just ensures we have an acceptable amount of args
            s.login(*([None] * 3))

        assert_raises(AlreadyLoggedIn, login)


@test
def session_logout():
    for s in create_sessions():
        s.is_authenticated = True
        old_session = s._rsession
        s.logout()

        assert_false(s.is_authenticated)
        old_session.close.assert_called_once_with()
        assert_is_not(s._rsession, old_session)


@test
def send_without_auth():
    for s in create_sessions():
        s.is_authenticated = True

        mock_session = MagicMock()
        mock_req_kwargs = {'fake': 'kwargs'}

        s.send(mock_req_kwargs, authtypes(), mock_session)

        # sending without auth should not use the normal session,
        # since that might have auth cookies automatically attached
        assert_false(s._rsession.called)

        mock_session.request.called_once_with(**mock_req_kwargs)
        mock_session.closed.called_once_with()


#
# protocol
#


@test
def authtypes_factory_defaults():
    auth = authtypes()
    assert_false(auth.oauth)
    assert_false(auth.sso)
    assert_false(auth.xt)


@test
def authtypes_factory_args():
    auth = authtypes(oauth=True)
    assert_true(auth.oauth)
    assert_false(auth.sso)
    assert_false(auth.xt)


@test
def mc_url_signing():
    sig, _ = mobileclient.GetStreamUrl.get_signature("Tdr6kq3xznv5kdsphyojox6dtoq",
                                                     "1373247112519")
    assert_equal(sig, b"gua1gInBdaVo7_dSwF9y0kodua0")


#
# utils
#

@test
def retry_failure_propogation():
    @utils.retry(tries=1)
    def raise_exception():
        raise AssertionError

    assert_raises(AssertionError, raise_exception)


@test
def retry_sleep_timing():

    @utils.retry(tries=3, delay=.05, backoff=2)
    def raise_exception():
        raise AssertionError

    pre = time.time()
    assert_raises(AssertionError, raise_exception)
    post = time.time()

    delta = post - pre
    assert_true(.15 < delta < .2, "delta: %s" % delta)


@test
def retry_is_dual_decorator():
    @utils.retry
    def return_arg(arg=None):
        return arg

    assert_equal(return_arg(1), 1)


@test
def jsarray_parsing():
    for raw in jsarray_samples:
        # should not raise an exception
        jsarray.loads(raw)


@test
def locate_transcoder():
    utils.locate_mp3_transcoder()  # should not raise
