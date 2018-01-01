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
   `one designed for the visually impaired <https://github.com/chrisnorman7/gmp3>`__,
   `a web-based jukebox which ships with its own server <https://github.com/chrisnorman7/jukebox>`__,
   `command line <https://github.com/christopher-dg/pmcli>`__
   `clients <https://github.com/and3rson/clay>`__,
   `a FUSE filesystem <https://github.com/EnigmaCurry/GMusicFS>`__,
   and `an Alexa skill <https://github.com/stevenleeg/geemusic>`__
-  library management tools for
   `syncing tracks <https://github.com/thebigmunch/gmusicapi-scripts>`__,
   `syncing playlists <https://github.com/soulfx/gmusic-playlist>`__,
   and `migrating to a different account <https://github.com/brettcoburn/gmusic-migrate>`__
-  proxies for media players, such as
   `gmusicproxy <http://gmusicproxy.net>`__ and
   `gmusicprocurator <https://github.com/malept/gmusicprocurator>`__,
   as well as plugins for 
   `Mopidy <https://github.com/hechtus/mopidy-gmusic>`__,
   `Squeezebox <https://github.com/squeezebox-googlemusic/squeezebox-googlemusic>`__ and
   `Tizonia <https://github.com/tizonia/tizonia-openmax-il>`__.
-  enhancements like `autoplaylists / smart playlists <https://autoplaylists.simon.codes>`__


Getting started
---------------
Start with `the usage docs <http://unofficial-google-music-api.readthedocs.io/en/latest/usage.html#usage>`__, which will guide you through installation and the available apis.

Once you're up and running, you can explore the rest of the docs at http://unofficial-google-music-api.readthedocs.io.

If the documentation doesn't answer your questions, or you just want to get
in touch, either `drop by #gmusicapi on Freenode
<http://webchat.freenode.net/?channels=gmusicapi>`__ or shoot me an email.

Status and updates
------------------

|build_status| |repominder_status|

.. |build_status| image:: https://travis-ci.org/simon-weber/gmusicapi.png?branch=develop
        :target: https://travis-ci.org/simon-weber/gmusicapi
        
.. |repominder_status| image:: https://img.shields.io/badge/dynamic/json.svg?label=release&query=%24.status&maxAge=43200&uri=https%3A%2F%2Fwww.repominder.com%2Fbadge%2FeyJyZXBvX2lkIjogMTEsICJ1c2VyX2lkIjogMn0%3D%2F&link=https%3A%2F%2Fwww.repominder.com%2F
        :target: https://www.repominder.com

* February 2016: Python 3 support!
* September 2015: Google switched to a new music uploading endpoint, breaking uploading for outdated versions of gmusicapi.
* June 2015: Full mobileclient and webclient functionality was restored.
* May 2015: Limited mobileclient functionality was restored.
* April 2015: Google deprecated clientlogin, breaking both the webclient and mobileclient.
* November 2013: I started working fulltime at Venmo, meaning this project is back to night and weekend development.

For fine-grained development updates, follow me on Twitter:
`@simonmweber <https://twitter.com/simonmweber>`__.
