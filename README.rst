gmusicapi: an unofficial Python API for Google Play Music
=========================================================

This project allows control of
`Google Music <http://music.google.com>`_ from Python. It is not
supported nor endorsed by Google.

**Respect Google in your use of the API**. Use common sense
(protocol compliance, reasonable load, etc) and don't ruin the fun
for everyone else.

For those looking to use the api, see the installation and usage
sections below.
`Documentation is hosted at Read the Docs <http://readthedocs.org/docs/unofficial-google-music-api/en/latest>`_.

For those looking to port or contribute, see the porting section
below. There's also
`an out of date code overview on the wiki <https://github.com/simon-weber/Unofficial-Google-Music-API/wiki/Codebase-Overview>`_.

For bugs reports, feature requests, and contributions, go ahead and
`open an issue <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/new>`_.

Also, check out these nifty projects that use gmusicapi:


-  Malcolm Still's `command line Google Music client <https://github.com/mstill/thunner>`_
   (`screenshot <http://i.imgur.com/Mwl0k.png>`_)
-  David Dooling's `sync scripts for Banshee <https://github.com/ddgenome/banshee-helper-scripts>`_
-  Mendhak's `Rhythmbox metadata sync plugin <https://github.com/mendhak/rhythmbox-gmusic-sync>`_
-  Ryan McGuire's `GMusicFS <https://github.com/EnigmaCurry/GMusicFS>`_ - a FUSE
   filesystem linked to your music
-  Kilian Lackhove's `Google Music support <https://github.com/crabmanX/google-music-resolver>`_
   for http://www.tomahawk-player.org

Features
--------

**New in version 2013.01.05**


-  compatibility update for playlist modification
-  there are various problems with uploading at the moment - it's
   being tracked in
   `this issue <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/51#issuecomment-11833220>`_

**Feature Overview:**


-  Getting library information:
   
   -  all song metadata
   -  all user playlist titles and ids
   -  songs from a specific playlist

-  Song streaming and downloading

-  Song uploading of all Google-supported file formats

-  Playlist manipulation:
   
   -  creation
   -  name modification
   -  song deletion, addition, and reordering

-  Song manipulation:
   
   -  metadata modification (be sure to read the documentation)
   -  removal from library

-  Searching for songs, artists, and albums.


**Coming soon:**


-  album art manipulation
-  better upload support
-  better documentation

Usage
-----

The API has been tested on Python 2.7.2 on Linux and Windows.

Installation
~~~~~~~~~~~~

Use `pip <http://www.pip-installer.org/en/latest/index.html>`_:
``pip install gmusicapi`` will grab all the source dependencies.
Windows users could alternatively use the
`installation binary on PyPI <http://pypi.python.org/pypi/gmusicapi/>`_.
I would recommend *against* using ``easy_install``.

If you want to make changes to gmusicapi, see the guidance in the
`contributing doc <https://github.com/simon-weber/Unofficial-Google-Music-API/blob/master/CONTRIBUTING.md>`_.

To upload filetypes other than mp3, you're going to need FFmpeg
installed and in your system path. For Ubuntu users:
``sudo apt-get install ffmpeg ubuntu-restricted-extras``. Windows
users, get
`the most recent static binaries <http://ffmpeg.zeranoe.com/builds/>`_
and then
`edit your path <http://www.computerhope.com/issues/ch000549.htm>`_
to include the directory that contains ffmpeg.exe.

To check that everything is set up correctly, you can run the test
suite: ``python -m gmusicapi.test.integration_test_api``. If
something goes wrong during testing, there is the chance that
you'll end up with an extra playlist or test song in your library,
but it should never destructively modify your library. If there is
an error during testing, please
`open an issue <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/new>`_
to let me know about it.

Getting Started
~~~~~~~~~~~~~~~

gmusicapi.api.Api is the user-facing interface. The provided
`example.py <https://github.com/simon-weber/Unofficial-Google-Music-API/blob/master/example.py>`_
should be enough to get you started. For complete information, see
the
`documentation <http://readthedocs.org/docs/unofficial-google-music-api/en/latest>`_.
The testing code might also be useful.

Ports
-----

Here are the ports I'm currently aware of:


-  C#:
   `Taylor Finnell <https://github.com/Byteopia/GoogleMusicAPI.NET>`_
-  Java: `Jens Villadsen <https://github.com/jkiddo/gmusic.api>`_
   and `Nick Martin <https://github.com/xnickmx/google-play-client>`_
-  PHP:
   `raydanhk <http://code.google.com/p/unofficial-google-music-api-php/>`_

Porting Information for Developers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get in touch if you're working on a port. Even if I can't
contribute, I might know people who'd like to.

The current implementation uses the same interface that a web
browser does, and a code overview can be found
`on the wiki <https://github.com/simon-weber/Unofficial-Google-Music-API/wiki/Codebase-Overview>`_.
Darryl Pogue is worked on a more durable implementation by
emulating Google's Android app. His work is
`here <https://github.com/dpogue/Unofficial-Google-Music-API>`_,
and may easier to port. More information this alternative protocol
is
`here <https://github.com/dpogue/Unofficial-Google-Music-API/wiki/Skyjam-API>`_.

Either way, you'll probably want to ignore anything related to
Music Manager; that's just for uploading. If uploading interests
you, more information is
`here <https://github.com/simon-weber/google-music-protocol>`_.

Lastly, keep the license in mind, and, again, be sure to respect
Google.

Notes
-----

Debug logging is enabled by default. All logging is done to
gmusicapi.log in your working directory, with warnings and above
printed to the console. Nothing related to authenticated gets
logged aside from "logged in" and "logged out" messages.

--------------

Copyright 2012 `Simon Weber <http://www.simonmweber.com>`_.
Licensed under the 3-clause BSD. See COPYING.

.. image:: https://cruel-carlota.pagodabox.com/68a92ecf6b6590372f435fb2674d072e
