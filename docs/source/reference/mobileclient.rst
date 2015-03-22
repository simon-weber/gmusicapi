.. _mobileclient:
.. currentmodule:: gmusicapi.clients

Mobileclient Interface
======================

.. autoclass:: Mobileclient

Setup and login
---------------
.. automethod:: Mobileclient.__init__
.. automethod:: Mobileclient.login
.. automethod:: Mobileclient.logout

Songs
-----
Songs are uniquely referred to within a library
with a 'song id' or 'track id' uuid.

.. automethod:: Mobileclient.get_all_songs
.. automethod:: Mobileclient.get_stream_url
.. automethod:: Mobileclient.change_song_metadata
.. automethod:: Mobileclient.delete_songs
.. automethod:: Mobileclient.get_promoted_songs
.. automethod:: Mobileclient.increment_song_playcount

Playlists
---------
Like songs, playlists have unique ids within a library.
However, their names do not need to be unique.

The tracks making up a playlist are referred to as
'playlist entries', and have unique entry ids within the
entire library (not just their containing playlist).

.. automethod:: Mobileclient.get_all_playlists
.. automethod:: Mobileclient.get_all_user_playlist_contents
.. automethod:: Mobileclient.create_playlist
.. automethod:: Mobileclient.delete_playlist
.. automethod:: Mobileclient.edit_playlist
.. automethod:: Mobileclient.add_songs_to_playlist
.. automethod:: Mobileclient.reorder_playlist_entry
.. automethod:: Mobileclient.remove_entries_from_playlist
.. automethod:: Mobileclient.get_shared_playlist_contents

Other
-----
.. automethod:: Mobileclient.get_registered_devices

All Access Radio
----------------
.. automethod:: Mobileclient.get_all_stations
.. automethod:: Mobileclient.get_station_tracks
.. automethod:: Mobileclient.create_station
.. automethod:: Mobileclient.delete_stations

Other All Access features
-------------------------
All Access/store tracks also have track ids, but they are in a different
form from normal track ids.
``store_id.beginswith('T')`` always holds for these ids (and will not
for library track ids).

Adding a store track to a library will yield a normal song id.

All Access track ids can be used in most places that normal song ids can
(e.g. when for playlist addition or streaming).
Note that sometimes they are stored under the ``'nid'`` key, not the ``'id'`` key.

.. automethod:: Mobileclient.search_all_access
.. automethod:: Mobileclient.add_aa_track
.. automethod:: Mobileclient.get_artist_info
.. automethod:: Mobileclient.get_album_info
.. automethod:: Mobileclient.get_track_info
.. automethod:: Mobileclient.get_genres
