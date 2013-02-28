from proboscis.asserts import (
    assert_raises
)
"""
__all__ = [
    'assert_equal',
    'assert_false',
    'assert_is',
    'assert_is_none',
    'assert_is_not',
    'assert_is_not_none',
    'assert_not_equal',
    'assert_true',
    'assert_raises',
    'assert_raises_instance',
    'fail',
]
"""

from proboscis import test

from gmusicapi.utils import utils


"""
assert_raises(mymodule.UserNotFoundException, mymodule.login,
                  {'username':test_user.username, 'password':'fdgggdsds'})
"""

#All tests end up in the local group.
test = test(groups=['local'])


@test
def retry_propogates_on_failure():
    @utils.retry(Exception, tries=1)
    def raise_exception():
        raise Exception

    assert_raises(Exception, raise_exception)
