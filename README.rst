gmusicapi: an unofficial API for Google Play Music
==================================================

gmusicapi allows control of
`Google Music <http://music.google.com>`__ with Python.

.. code-block:: python

    from gmusicapi import Mobileclient
    
    api = Mobileclient()
    api.login('user@gmail.com', 'my-password', Mobileclient.FROM_MAC_ADDRESS)
    # => True
    
    library = api.get_all_songs()
    sweet_track_ids = [track['id'] for track in library
                       if track['artist'] == 'The Cat Empire']
    
    playlist_id = api.create_playlist('Rad muzak')
    api.add_songs_to_playlist(playlist_id, sweet_track_ids)
    
**gmusicapi is not supported nor endorsed by Google.**

That said, it's actively maintained, and powers a bunch of cool projects:

-  alternate clients, including
   `one designed for the visually impaired <https://github.com/chrisnorman7/gmp>`__,
   `a command line client <https://github.com/mstill/thunner>`__
   and `FUSE filesystem <https://github.com/EnigmaCurry/GMusicFS>`__
-  library management tools for
   `syncing tracks <https://github.com/thebigmunch/gmusicapi-scripts>`__,
   `syncing playlists <https://github.com/soulfx/gmusic-playlist>`__,
   and `migrating to a different account <https://github.com/brettcoburn/gmusic-migrate>`__
-  proxies for media players, such as
   `gmusicproxy <http://gmusicproxy.net>`__ and
   `gmusicprocurator <https://github.com/malept/gmusicprocurator>`__,
   as well as plugins for 
   `Mopidy <https://github.com/hechtus/mopidy-gmusic>`__ and
   `Squeezebox <https://github.com/hechtus/squeezebox-googlemusic>`__.
-  enhancements like `autoplaylists / smart playlists <https://autoplaylists.simon.codes>`__


Getting started
---------------
Everything you need is at http://unofficial-google-music-api.readthedocs.org.

If the documentation doesn't answer your questions, or you just want to get
in touch, either `drop by #gmusicapi on Freenode
<http://webchat.freenode.net/?channels=gmusicapi>`__ or shoot me an email.

Status and updates
------------------

.. image:: https://travis-ci.org/simon-weber/gmusicapi.png?branch=develop
        :target: https://travis-ci.org/simon-weber/gmusicapi

* February 2016: Python 3 support!
* September 2015: Google switched to a new music uploading endpoint, breaking uploading for outdated versions of gmusicapi.
* June 2015: Full mobileclient and webclient functionality was restored.
* May 2015: Limited mobileclient functionality was restored.
* April 2015: Google deprecated clientlogin, breaking both the webclient and mobileclient.
* November 2013: I started working fulltime at Venmo, meaning this project is back to night and weekend development.

For fine-grained development updates, follow me on Twitter:
`@simonmweber <https://twitter.com/simonmweber>`__.

------------

Copyright 2015 `Simon Weber <http://www.simonmweber.com>`__.
Licensed under the 3-clause BSD. See LICENSE.
