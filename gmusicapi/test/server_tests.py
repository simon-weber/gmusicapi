from proboscis.asserts import (
    assert_raises, assert_true, assert_equal
)
from proboscis import test, before_class, after_class, SkipTest

from gmusicapi.exceptions import NotLoggedIn
import gmusicapi.test.utils as test_utils


@test(groups=['server'])
class NoUpauthTests(object):

    @before_class
    def login(self):
        self.api = test_utils.init(perform_upload_auth=False)
        assert_true(self.api.is_authenticated())

    @after_class(always_run=True)
    def logout(self):
        assert_true(self.api.logout())

    @test
    def need_upauth_for_upload(self):
        assert_raises(NotLoggedIn, self.api.upload, 'fake filename')


@test(groups=['server'])
class UpauthTests(object):
    @before_class
    def login(self):
        self.api = test_utils.init()
        assert_true(self.api.is_authenticated())

    @after_class(always_run=True)
    def logout(self):
        assert_true(self.api.logout())

    @test
    def create_song(self):
        """Create a song to operate on."""
        self.song_id = None

        filepath = test_utils.mp3_filenames[0]

        uploaded, matched, not_uploaded = self.api.upload(filepath)
        assert_equal(not_uploaded, {})
        assert_equal(matched, {})
        assert_equal(uploaded.keys(), [filepath])

        self.song_id = uploaded[filepath]

    @test(depends_on=[create_song], always_run=True)
    def delete_song(self):
        if self.song_id is None:
            #TODO consider searching and deleting here?
            raise SkipTest('did not store self.song_id')

        res = self.api.delete_songs(self.song_id)

        assert_equal(res, [self.song_id])
