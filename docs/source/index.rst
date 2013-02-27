gmusicapi: an unofficial API for Google Play Music
==================================================

This library allows control of
`Google Music <http://music.google.com>`__ with Python.

.. code-block:: python

    from gmusicapi import Api
    api = Api()
    api.login('user@gmail.com', 'my-password')
    # => True

    library = api.get_all_songs()
    sweet_tracks = [track for track in library if track['artist'] == 'The Cat Empire']

    playlist_id = api.create_playlist('Rad muzak')
    api.change_playlist(playlist_id, sweet_tracks)
    

**This project is not supported nor endorsed by Google.**
Use common sense (protocol compliance, reasonable load, etc) and don't ruin the fun
for everyone else.

Features
--------

All major functionality is supported:

-  Library management: list, create, delete, and modify songs and playlists

-  Web-client streaming and single-song downloading

-  Music Manager uploading/scan-and-match of all Google-supported file formats

Other features are on the way:

-  Music Manager library downloading (issue `#90
   <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/90>`__)
-  Full "fix incorrect match" support (issue `#89
   <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/89>`__)

See `the changelog
<https://github.com/simon-weber/Unofficial-Google-Music-API/blob/develop/HISTORY.rst>`__
for changes by version.

Using gmusicapi
---------------

.. toctree::
   :hidden:

   usage
   ports
   contributing

For help getting started, check out the :ref:`usage section <usage>`.

The reference has details on specific features, as well as the format of
the Google Music data you'll see:

.. toctree::
   :maxdepth: 2

   reference/api
   reference/metadata
   reference/protocol

If you'd like to help make gmusicapi better, the
:ref:`contributing section <contributing>` is for you.
You might also be interested in `the code
<https://github.com/simon-weber/Unofficial-Google-Music-API>`__.

If you don't want to use Python, or you want to create a port, see the
:ref:`ports section <ports>`.

Lastly, feel free to drop by ``#gmusicapi`` on Freenode to ask questions or just hang out.
