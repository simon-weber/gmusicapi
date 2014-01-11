gmusicapi: an unofficial API for Google Play Music
==================================================

gmusicapi allows control of
`Google Music <http://music.google.com>`__ with Python.

.. code-block:: python

    from gmusicapi import Mobileclient
    
    api = Mobileclient()
    api.login('user@gmail.com', 'my-password')
    # => True
    
    library = api.get_all_songs()
    sweet_track_ids = [track['id'] for track in library
                       if track['artist'] == 'The Cat Empire']
    
    playlist_id = api.create_playlist('Rad muzak')
    api.add_songs_to_playlist(playlist_id, sweet_track_ids)
    
**gmusicapi is not supported nor endorsed by Google.**

That said, it's actively maintained, and used in a bunch of cool projects, like:

-  Malcolm Still's `command line Google Music client <https://github.com/mstill/thunner>`__
   (`screenshot <http://i.imgur.com/Mwl0k.png>`__)
-  Ryan McGuire's `GMusicFS <https://github.com/EnigmaCurry/GMusicFS>`__ - a FUSE
   filesystem linked to your music
-  Kilian Lackhove's `Google Music support <https://github.com/crabmanX/google-music-resolver>`__
   for http://www.tomahawk-player.org
-  `Mario Di Raimondo <https://github.com/diraimondo>`__'s `Google Music http proxy for mediaplayers <http://gmusicproxy.net>`__
-  `@thebigmunch <https://github.com/thebigmunch>`__'s `syncing scripts <https://github.com/thebigmunch/gmusicapi-scripts>`__
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

Over the summer, gmusicapi began a major shift away from the Webclient interface.
That's finished now, so prefer the new Mobileclient interface whenever possible.
Non-deprecated parts of the Webclient are listed at
`the Webclient documentation page
<http://unofficial-google-music-api.readthedocs.org/en/latest/reference/webclient.html>`__.

I've started fulltime work at Venmo as of November, meaning this project is back to
night and weekend development.

For fine-grained development updates, follow me on Twitter:
`@simonmweber <https://twitter.com/simonmweber>`__.

------------

Copyright 2013 `Simon Weber <http://www.simonmweber.com>`__.
Licensed under the 3-clause BSD. See LICENSE.
