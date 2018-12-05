# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals
from gmusicapi.clients.webclient import Webclient
from gmusicapi.clients.musicmanager import Musicmanager
from gmusicapi.clients.mobileclient import Mobileclient

(Webclient, Musicmanager, Mobileclient)  # noqa

import warnings
from gmusicapi.exceptions import GmusicapiWarning
OAUTH_FILEPATH = Musicmanager.OAUTH_FILEPATH
msg = ("gmusicapi.clients.OAUTH_FILEPATH is deprecated and will be removed;"
       " use Musicmanager.OAUTH_FILEPATH")
warnings.warn(msg, GmusicapiWarning, stacklevel=2)
