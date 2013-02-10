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


.. _songdict-format:

Song Dictionary Format
======================

Google Music sends song metadata in dictionaries.
Many of them cannot be changed, and others don't appear in all songs.
See `the code <https://github.com/simon-weber/Unofficial-Google-Music-API
/blob/develop/gmusicapi/protocol/metadata.py>`_ for complete information.

Songs retrieved in the context of a playlist will contain a ``playlistEntryId``
which is unique to the relevant playlist.

Here is a non-playlist example, which might be out of date::

    {
      "album": "Heritage", 
      "albumArtUrl": "//lh4.googleusercontent.com/...", 
      "albumArtist": "Opeth", 
      "albumArtistNorm": "opeth", 
      "albumNorm": "heritage", 
      "artist": "Opeth", 
      "artistNorm": "opeth", 
      "beatsPerMinute": 0, 
      "bitrate": 320, 
      "comment": "", 
      "composer": "", 
      "creationDate": 1354427077896500, 
      "deleted": false, 
      "disc": 0, 
      "durationMillis": 418000, 
      "genre": "Progressive Metal", 
      "id": "5924d75a-931c-30ed-8790-f7fce8943c85", 
      "lastPlayed": 1360449492166904, 
      "matchedId": "Txsffypukmmeg3iwl3w5a5s3vzy", 
      "name": "Haxprocess", 
      "playCount": 0, 
      "rating": 0, 
      "recentTimestamp": 1354427941107000, 
      "storeId": "Txsffypukmmeg3iwl3w5a5s3vzy", 
      "subjectToCuration": false, 
      "title": "Haxprocess", 
      "titleNorm": "haxprocess", 
      "totalDiscs": 0, 
      "totalTracks": 10, 
      "track": 6, 
      "type": 2, 
      "url": "", 
      "year": 2011
    }


