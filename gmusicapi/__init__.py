# -*- coding: utf-8 -*-

from gmusicapi._version import __version__
from gmusicapi.clients import Webclient, Musicmanager, Mobileclient
from gmusicapi.exceptions import CallFailure

__copyright__ = 'Copyright 2014 Simon Weber'
__license__ = 'BSD 3-Clause'
__title__ = 'gmusicapi'

# appease flake8: the imports are purposeful
(__version__, Webclient, Musicmanager, Mobileclient, CallFailure)


class Api(object):
    """Mock class used to signal gmusicapi.Api deprecation."""
    def __init__(self):
        # not using warnings because this change cannot be ignored
        raise ImportError('gmusicapi.Api is deprecated; use gmusicapi.Webclient'
                          ' or gmusicapi.Musicmanager instead.'
                          '\n'
                          'For help rewriting your code, see'
                          ' https://unofficial-google-music-api.readthedocs.org/'
                          'en/latest/usage.html#quickstart.'
                          '\n'
                          'For an explanation of why the change was made, see'
                          ' https://github.com/simon-weber/'
                          'Unofficial-Google-Music-API/issues/112.')
