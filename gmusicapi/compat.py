# -*- coding: utf-8 -*-

"""
Single interface for code that varies across Python versions
"""

import sys

_ver = sys.version_info
is_py26 = (_ver[:2] == (2, 6))

if is_py26:
    from gmusicapi.utils.counter import Counter
    import unittest2 as unittest
    import simplejson as json
else:  # 2.7
    from collections import Counter
    import unittest
    import json
