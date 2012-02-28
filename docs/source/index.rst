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
    :members: get_song_download_info, get_stream_url

    .. automethod:: upload(filenames)

Playlist manipulation
---------------------
.. autoclass:: Api
    :members: change_playlist_name, create_playlist, delete_playlist

    .. automethod:: add_songs_to_playlist(playlist_id, song_ids)
    .. automethod:: remove_song_from_playlist(song_ids, playlist_id)

Song manipulation
-----------------
.. autoclass:: Api

    .. automethod:: change_song_metadata(songs)
    .. automethod:: delete_song(song_ids)


Searching
---------
.. autoclass:: Api
    :members: search
