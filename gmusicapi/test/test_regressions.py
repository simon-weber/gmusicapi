#!/usr/bin/env python

#Copyright 2012 Simon Weber.

#This file is part of gmusicapi - the Unofficial Google Music API.

#Gmapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmapi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with gmusicapi.  If not, see <http://www.gnu.org/licenses/>.

"""A test harness for regressions."""

import unittest
import random
import os
import string

from ..utils.apilogging import LogController
from ..test import utils as test_utils


#Expected to be in this directory.
no_tags_filename = "no_tags.mp3"
has_tags_filename = "test.mp3"

#Lots of things to be pulled out of the other api call test class here.

class TestRegressions(test_utils.BaseTest):
    """Runs regression tests.
    Tests are intended not to modify the library, but no guarantees are made.
    """

    @classmethod
    def setUpClass(cls):
        super(TestRegressions, cls).setUpClass()

        cls.log = LogController().get_logger("gmusicapi.test.TestRegressions")

        #Get the full path of the test file.
        path = os.path.realpath(__file__)
        cls.no_tags_filename = path[:string.rfind(path, r'/')] + r'/' + no_tags_filename
        cls.has_tags_filename = path[:string.rfind(path, r'/')] + r'/' + has_tags_filename


    #---
    #   Monolithic tests: 
    #   (messy, but less likely to destructively modify the library)
    #   Modified from http://stackoverflow.com/questions/5387299/python-unittest-testcase-execution-order
    #---

    def notags_1_upload_notags(self):
        """Upload the file without tags."""
        result = self.api.upload(self.no_tags_filename)
        self.assertTrue(self.no_tags_filename in result)
        
        #Messy; need to pass on id to be deleted.
        self.notags_uploaded_id = result[self.no_tags_filename]

    def notags_2_upload_hastags(self):
        """Upload the file with tags."""
        result = self.api.upload(self.has_tags_filename)
        self.assertTrue(self.has_tags_filename in result)
        
        self.hastags_uploaded_id = result[self.has_tags_filename]

    def notags_3_delete(self):
        """Delete the uploaded files."""
        self.assert_success(
            self.api.delete_song(self.notags_uploaded_id))

        self.assert_success(
            self.api.delete_song(self.hastags_uploaded_id))

        del self.notags_uploaded_id
        del self.hastags_uploaded_id

    def test_notags_upload(self):
        self.run_steps("notags")


if __name__ == '__main__':
    unittest.main()
