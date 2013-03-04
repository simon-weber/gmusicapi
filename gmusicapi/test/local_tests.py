import time

from proboscis.asserts import (
    assert_raises, assert_true, assert_false, assert_equal,
)
from proboscis import test

from gmusicapi import Api
from gmusicapi.utils import utils


#TODO test gather_local, transcoding

#All tests end up in the local group.
test = test(groups=['local'])

##
# api
##


@test
def no_auth_initially():
    api = Api()
    assert_false(api.is_authenticated())


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


@test
def auto_playlists_are_empty():
    # this doesn't actually hit the server at the moment.
    # see issue 102
    api = Api()
    assert_equal(api.get_all_playlist_ids(auto=True, user=False),
                 {'auto': {}})
