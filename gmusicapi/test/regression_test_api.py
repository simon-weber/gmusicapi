#!/usr/bin/env python

# Copyright (c) 2012, Simon Weber
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of the contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""A test harness to ensure old bugs to do resurface.
Tests are intended not to modify the library, but no guarantees are made."""

import unittest
import random
import os
import string

from ..utils.apilogging import UsesLog
from ..test import utils as test_utils
from ..protocol import MetadataExpectations
from ..protocol import UnknownExpectation

#Expected to be in this directory.
has_tags_filename = 'upper.MP3'
#Also tests unicode compatibility.
no_tags_filename = '한글.mp3'

#Lots of things to be pulled out of the other api call test class here.

class TestRegressions(test_utils.BaseTest, UsesLog):

    @classmethod
    def setUpClass(cls):
        super(TestRegressions, cls).setUpClass()

        cls.init_class_logger()

        #Get the full path of the test file.
        path = os.path.realpath(__file__)
        cls.no_tags_filename = path[:string.rfind(path, os.sep)] + os.sep + no_tags_filename
        cls.has_tags_filename = path[:string.rfind(path, os.sep)] + os.sep + has_tags_filename

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
        self.api.delete_songs(self.notags_uploaded_id)

        self.api.delete_songs(self.hastags_uploaded_id)

        del self.notags_uploaded_id
        del self.hastags_uploaded_id

    def test_notags_upload(self):
        self.run_steps("notags")

    def test_invalid_md_key(self):
        expt = MetadataExpectations.get_expectation("foo", warn_on_unknown=False)
        self.assertTrue(expt is UnknownExpectation)

        #Don't want any unknowns when getting all.
        for expt in MetadataExpectations.get_all_expectations():
            self.assertTrue(expt is not UnknownExpectation)


if __name__ == '__main__':
    unittest.main()
