The Unofficial Google Music Api
*******************************

.. automodule:: gmapi.api


Api Features
============

Authentication
--------------
.. autoclass:: Api
    :members: login, logout

Getting Library Information
---------------------------
.. autoclass:: Api
    :members: get_all_songs, get_playlists, get_playlist_songs

Song download, streaming, and upload
------------------------------------
.. autoclass:: Api
    :members: get_song_download_info, get_stream_url, upload

Playlist manipulation
---------------------
.. autoclass:: Api
    :members: add_songs_to_playlist, change_playlist_name, create_playlist, delete_playlist, remove_song_from_playlist

Song manipulation
-----------------
.. autoclass:: Api
    :members: change_song_metadata, delete_song

Searching
---------
.. autoclass:: Api
    :members: search
