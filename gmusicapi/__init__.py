# -*- coding: utf-8 -*-

from gmusicapi._version import __version__
from gmusicapi.clients import Webclient, Musicmanager, Mobileclient
from gmusicapi.exceptions import CallFailure

__copyright__ = 'Copyright 2015 Simon Weber'
__license__ = 'BSD 3-Clause'
__title__ = 'gmusicapi'

# appease flake8: the imports are purposeful
(__version__, Webclient, Musicmanager, Mobileclient, CallFailure)
