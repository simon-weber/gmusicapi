#!/usr/bin/env python
# -*- coding: utf-8 -*-

from _version import __version__

__copyright__ = 'Copyright 2013 Simon Weber'
__license__ = 'BSD 3-Clause'
__title__ = 'gmusicapi'

from gmusicapi.clients import Webclient, Musicmanager
from gmusicapi.exceptions import CallFailure

# appease flake8: the imports are purposeful
(__version__, Webclient, Musicmanager, CallFailure)

# Removing this for now; logging is important, and people shouldn't ignore it.
## Set default logging handler to avoid "No handler found" warnings.
#import logging
#try:  # Python 2.7+
#    from logging import NullHandler
#except ImportError:
#    class NullHandler(logging.Handler):
#        def emit(self, record):
#            pass
#
#logging.getLogger(__name__).addHandler(NullHandler())
