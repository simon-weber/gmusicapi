The Unofficial Google Music Api
*******************************

The api itself is hosted at GitHub: https://github.com/simon-weber/Unofficial-Google-Music-API.

.. currentmodule:: gmusicapi
.. automodule:: gmusicapi.api



Api Features
============

Authentication
--------------
.. autoclass:: Api
    :members: login, logout

Getting songs and playlists
-----------------------------------
.. autoclass:: Api
    :members: get_all_songs, get_all_playlist_ids, get_playlist_songs

Song uploading, downloading, and streaming
------------------------------------------
.. autoclass:: Api
    :members: get_song_download_info, get_stream_url, upload

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


GM Metadata Format
==================

Google Music sends song metadata in dictionaries.

These dictionaries have up to 30 keys. Here is an example::

    {'comment': ''
     'rating': 0
     'lastPlayed': 1324954872637533L
     'disc': 1
     'composer': ''
     'year': 2009
     'id': '305a7b83-32fa-3a71-9a77-498dfce74aad'
     'album': 'Live on Earth'
     'title': 'The Car Song'
     'deleted': False
     'albumArtist': 'The Cat Empire'
     'type': 2
     'titleNorm': 'the car song'
     'track': 2
     'albumArtistNorm': 'the cat empire'
     'totalTracks': 0
     'beatsPerMinute': 0
     'genre': 'Alternative'
     'playCount': 0
     'creationDate': 1324614519429366L
     'name': 'The Car Song'
     'albumNorm': 'live on earth'
     'artist': 'The Cat Empire'
     'url': ''
     'totalDiscs': 2
     'durationMillis': 562000
     'artistNorm': 'the cat empire',
     'subjectToCuration': False,
     'metajamId': '',
     (optional entry; exists if there is album art)
     'albumArtUrl': '//lh6.googleusercontent.com/<long identifier>'
     }


In addition, songs retrieved in the context of a playlist will contain a `playlistEntryId` which is unique to the relevant playlist.

See ``Metadata_Expectations`` in ``protocol.py`` for complete information.
