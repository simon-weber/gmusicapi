.. _webclient:
.. currentmodule:: gmusicapi.clients

Webclient Interface
===================

.. autoclass:: Webclient

Setup and login
---------------
.. automethod:: Webclient.__init__
.. automethod:: Webclient.login
.. automethod:: Webclient.logout

Getting songs and playlists
---------------------------
.. automethod:: Webclient.get_all_songs
.. automethod:: Webclient.get_all_playlist_ids
.. automethod:: Webclient.get_playlist_songs
.. automethod:: Webclient.search

Song downloading and streaming
------------------------------
.. automethod:: Webclient.get_song_download_info
.. automethod:: Webclient.get_stream_url
.. automethod:: Webclient.report_incorrect_match

Song manipulation
-----------------
.. automethod:: Webclient.change_song_metadata
.. automethod:: Webclient.upload_album_art
.. automethod:: Webclient.delete_songs

Playlist manipulation
---------------------
.. automethod:: Webclient.create_playlist
.. automethod:: Webclient.change_playlist_name
.. automethod:: Webclient.copy_playlist
.. automethod:: Webclient.delete_playlist

Playlist content manipulation
-----------------------------
.. automethod:: Webclient.change_playlist
.. automethod:: Webclient.add_songs_to_playlist
.. automethod:: Webclient.remove_songs_from_playlist
