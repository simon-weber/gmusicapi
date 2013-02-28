import time

from proboscis.asserts import (
    assert_raises, assert_true, assert_false
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
def retry_propogates_on_failure():
    @utils.retry(tries=1)
    def raise_exception():
        raise AssertionError

    assert_raises(AssertionError, raise_exception)


@test
def retry_sleeps():

    @utils.retry(tries=3, delay=.05, backoff=2)
    def raise_exception():
        raise AssertionError

    pre = time.time()
    assert_raises(AssertionError, raise_exception)
    post = time.time()

    delta = post - pre
    assert_true(.15 < delta < .2, "delta: %s" % delta)
