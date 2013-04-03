gmusicapi: an unofficial API for Google Play Music
==================================================

gmusicapi allows control of
`Google Music <http://music.google.com>`__ with Python.


.. code-block:: python

    from gmusicapi import Webclient
    
    api = Webclient()
    api.login('user@gmail.com', 'my-password')
    # => True

    library = api.get_all_songs()
    sweet_tracks = [track for track in library if track['artist'] == 'The Cat Empire']

    playlist_id = api.create_playlist('Rad muzak')
    api.change_playlist(playlist_id, sweet_tracks)
    
**gmusicapi is not supported nor endorsed by Google.**

That said, it's actively maintained, and used in a bunch of cool projects:

-  Malcolm Still's `command line Google Music client <https://github.com/mstill/thunner>`__
   (`screenshot <http://i.imgur.com/Mwl0k.png>`__)
-  Ryan McGuire's `GMusicFS <https://github.com/EnigmaCurry/GMusicFS>`__ - a FUSE
   filesystem linked to your music
-  David Dooling's `sync scripts for Banshee <https://github.com/ddgenome/banshee-helper-scripts>`__
-  Kilian Lackhove's `Google Music support <https://github.com/crabmanX/google-music-resolver>`__
   for http://www.tomahawk-player.org
-  Tom Graham's `playlist syncing tool <https://github.com/Tyris/m3uGoogleMusicSync>`__


Getting started
---------------
Everything you need is at http://unofficial-google-music-api.readthedocs.org.

If the documentation doesn't answer your questions, or you just want to get
in touch, either `drop by #gmusicapi on Freenode
<http://webchat.freenode.net/?channels=gmusicapi>`__ or shoot me an email.

Status and updates
------------------

.. image:: https://travis-ci.org/simon-weber/Unofficial-Google-Music-API.png?branch=develop
        :target: https://travis-ci.org/simon-weber/Unofficial-Google-Music-API

Version 1.0.0 splits the previous Api interface 
into Webclient and Musicmanager. See
https://unofficial-google-music-api.readthedocs.org/en/latest/usage.html#quickstart
for help with the new interfaces.

For updates, follow me on Twitter:
`@simonmweber <https://twitter.com/simonmweber>`__.

------------

Copyright 2013 `Simon Weber <http://www.simonmweber.com>`__.
Licensed under the 3-clause BSD. See LICENSE.

.. image:: https://cruel-carlota.pagodabox.com/68a92ecf6b6590372f435fb2674d072e
