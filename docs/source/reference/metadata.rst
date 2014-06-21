.. _metadata:

Song Metadata
=============

Format Example
--------------

.. _songdict-format:

**This information is outdated and only applies to the webclient.**

Google Music sends song metadata in json objects, which are represented as Python dictionaries.

The dictionary is a slightly misleading representation, since some keys cannot be modified.
In general, use common sense when changing values - changing something like 'album' is
more likely to work than changing 'creationDate'.

Here is an example of a song dictionary::

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



Full Information
----------------

.. currentmodule:: gmusicapi.protocol
.. automodule:: gmusicapi.protocol.metadata
   :members: KnownMetadataFields 
