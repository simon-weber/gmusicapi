from proboscis.asserts import (
    assert_raises, assert_true
)
from proboscis import test, before_class, after_class

from gmusicapi.exceptions import NotLoggedIn
from gmusicapi.utils import utils
import gmusicapi.test.utils as test_utils


test = test(groups=['server'])


@test
class NoUploadAuthTests(object):

    @before_class
    def login(self):
        self.api = test_utils.init(perform_upload_auth=False)
        assert_true(self.api.is_authenticated())

    @after_class
    def logout(self):
        assert_true(self.api.logout())

    @test
    def need_upauth_for_upload(self):
        assert_raises(NotLoggedIn, self.api.upload, 'fake filename')
