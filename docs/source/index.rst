gmusicapi: an unofficial API for Google Play Music
==================================================

This library allows control of
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
    

**This project is not supported nor endorsed by Google.**
Use common sense (protocol compliance, reasonable load, etc) and don't ruin the fun
for everyone else.

Features
--------

All major functionality is supported:

-  Library management: list, create, delete, and modify songs and playlists

-  Streaming and single-song downloading

-  Music Manager uploading/scan-and-match and library downloading

-  Most All Access features


See `the changelog
<https://github.com/simon-weber/gmusicapi/blob/develop/HISTORY.rst>`__
for changes by version.

Using gmusicapi
---------------

.. toctree::
   :hidden:

   usage
   ports
   contributing

Getting started
+++++++++++++++
The :ref:`usage section <usage>` has installation instructions
and some simple examples.

Api and data reference
++++++++++++++++++++++
The reference has details for all classes and functions, as well as 
information on the Google Music data you'll encounter:

.. toctree::
   :maxdepth: 2

   reference/api
   reference/protocol

Making gmusicapi better
+++++++++++++++++++++++
Contributions are always welcome! 
The :ref:`contributing section <contributing>` has more details.

`The code
<https://github.com/simon-weber/gmusicapi>`__
might also be useful.

Ports and other languages
+++++++++++++++++++++++++
The :ref:`ports section <ports>` lists known ports and information for making
ports.

Getting help
++++++++++++
Running into bugs? Have questions? Drop by ``#gmusicapi`` on Freenode.
If you've never used IRC before, it's easy: just fill in a nickname and captcha
at `this webchat link <http://webchat.freenode.net/?channels=gmusicapi>`__.

If IRC makes you uncomfortable, you can always email me directly:
`simon@simonmweber.com <mailto:simon@simonmweber.com>`__.
