from collections import namedtuple
import time

from mock import MagicMock as Mock
from proboscis.asserts import (
    assert_raises, assert_true, assert_false, assert_equal,
    assert_is_not
)
from proboscis import test

#from gmusicapi import Api
import gmusicapi.session
from gmusicapi.exceptions import AlreadyLoggedIn  # ,NotLoggedIn
from gmusicapi.utils import utils


#TODO test gather_local, transcoding

#All tests end up in the local group.
test = test(groups=['local'])

##
# clients
##TODO


# @test
# def no_client_auth_initially():
#     api = Api()
#     assert_false(api.is_authenticated())


# @test
# def auto_playlists_are_empty():
#     # this doesn't actually hit the server at the moment.
#     # see issue 102
#     api = Api()
#     assert_equal(api.get_all_playlist_ids(auto=True, user=False),
#                  {'auto': {}})

##
# sessions
##
session_names = ('_Base', 'Webclient', 'Musicmanager')
Sessions = namedtuple('Sessions', 'base webclient musicmanager')


def create_sessions():
    sessions = []
    for name in session_names:
        cls = getattr(gmusicapi.session, name)
        s = cls()

        # mock out the underlying requests.session
        s._rsession = Mock()
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
            # this just ensures we have an acceptable amount
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


##
# utils
##

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
