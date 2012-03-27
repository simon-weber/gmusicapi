#!/usr/bin/env python

#Copyright 2012 Simon Weber.

#This file is part of gmusicapi - the Unofficial Google Music API.

#Gmusicapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmusicapi is distributed in the hope that it will be useful,
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

from ..utils.apilogging import UsesLog
from ..test import utils as test_utils
from ..protocol import Metadata_Expectations
from ..protocol import UnknownExpectation

#Expected to be in this directory.
no_tags_filename = "no_tags.mp3"
has_tags_filename = "test.mp3"

#Lots of things to be pulled out of the other api call test class here.

class TestRegressions(test_utils.BaseTest, UsesLog):
    """Runs regression tests.
    Tests are intended not to modify the library, but no guarantees are made.
    """

    @classmethod
    def setUpClass(cls):
        super(TestRegressions, cls).setUpClass()

        cls.init_class_logger()

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
            self.api.delete_songs(self.notags_uploaded_id))

        self.assert_success(
            self.api.delete_songs(self.hastags_uploaded_id))

        del self.notags_uploaded_id
        del self.hastags_uploaded_id

    def test_notags_upload(self):
        self.run_steps("notags")

    def test_invalid_md_key(self):
        expt = Metadata_Expectations.get_expectation("foo", warn_on_unknown=False)
        self.assertTrue(expt is UnknownExpectation)

        #Don't want any unknowns when getting all.
        for expt in Metadata_Expectations.get_all_expectations():
            self.assertTrue(expt is not UnknownExpectation)


if __name__ == '__main__':
    unittest.main()
