#!/usr/bin/env python
# -*- coding: utf-8 -*-

from _version import __version__

__copyright__ = 'Copyright 2013 Simon Weber'
__license__ = 'BSD 3-Clause'
__title__ = 'gmusicapi'

#from gmusicapi.api import Api
from gmusicapi.exceptions import CallFailure

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
