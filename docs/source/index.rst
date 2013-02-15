gmusicapi: an unofficial API for Google Play Music
==================================================

version v\ |version|

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

.. toctree::
   :glob:
   :hidden:

   usage
   contributing

For help getting started, check out the :ref:`usage section <usage>`.

If you'd like to help make gmusicapi better, the
:ref:`contributing section <contributing>` is for you.

Lastly, the reference has details on specific features, as well as the format of
the Google Music data you'll see.

.. toctree::
   :maxdepth: 2

   reference/api
   reference/metadata
   reference/protocol
