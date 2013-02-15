.. _api:

Api Features
============

.. currentmodule:: gmusicapi
.. automodule:: gmusicapi.api

Setup and login
---------------
.. autoclass:: Api
    :members: __init__, login, logout

Getting songs and playlists
---------------------------
.. autoclass:: Api
    :members: get_all_songs, get_all_playlist_ids, get_playlist_songs

Song uploading, downloading, and streaming
------------------------------------------
.. autoclass:: Api
    :members: get_song_download_info, get_stream_url, upload, report_incorrect_match

Playlist manipulation
---------------------
.. autoclass:: Api
    :members: change_playlist, change_playlist_name, copy_playlist, create_playlist, delete_playlist, add_songs_to_playlist, remove_songs_from_playlist

Song manipulation
-----------------
.. autoclass:: Api
    :members: change_song_metadata, delete_songs


Searching
---------
.. autoclass:: Api
    :members: search
