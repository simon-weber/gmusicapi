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

Song downloading and streaming
------------------------------
.. automethod:: Webclient.get_song_download_info
.. automethod:: Webclient.get_stream_audio
.. automethod:: Webclient.get_stream_urls
.. automethod:: Webclient.report_incorrect_match

Song manipulation
-----------------
.. automethod:: Webclient.upload_album_art
.. automethod:: Webclient.delete_songs

Playlist manipulation
---------------------
.. automethod:: Webclient.create_playlist
.. automethod:: Webclient.add_songs_to_playlist
.. automethod:: Webclient.remove_songs_from_playlist
.. automethod:: Webclient.get_shared_playlist_info

Other
-----
.. automethod:: Webclient.get_registered_devices
