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
.. automethod:: Mobileclient.is_authenticated
.. attribute:: Mobileclient.locale

	The locale of the Mobileclient session used to localize some responses.

	Should be an `ICU <http://www.localeplanet.com/icu/>`__ locale supported by Android.

	Set on authentication with :func:`login` but can be changed at any time.

Account Management
------------------
.. attribute:: Mobileclient.is_subscribed

	Returns the subscription status of the Google Music account.

	Result is cached with a TTL of 10 minutes. To get live status before the TTL
	is up, delete the ``is_subscribed`` property of the Mobileclient instance.

		>>> mc = Mobileclient()
		>>> mc.is_subscribed  # Live status.
		>>> mc.is_subscribed  # Cached status.
		>>> del mc.is_subscribed  # Delete is_subscribed property.
		>>> mc.is_subscribed  # Live status.

.. automethod:: Mobileclient.get_registered_devices
.. automethod:: Mobileclient.deauthorize_device

Songs
-----
Songs are uniquely referred to within a library
with a track id in uuid format.

Store tracks also have track ids, but they are in a different
format than library track ids.
``song_id.startswith('T')`` is always ``True`` for store track ids
and ``False`` for library track ids.

Adding a store track to a library will yield a normal song id.

Store track ids can be used in most places that normal song ids can
(e.g. playlist addition or streaming).
Note that sometimes they are stored under the ``'nid'`` key, not the ``'id'`` key.

.. automethod:: Mobileclient.get_all_songs
.. automethod:: Mobileclient.get_stream_url
.. automethod:: Mobileclient.rate_songs
.. automethod:: Mobileclient.change_song_metadata
.. automethod:: Mobileclient.delete_songs
.. automethod:: Mobileclient.get_promoted_songs
.. automethod:: Mobileclient.increment_song_playcount
.. automethod:: Mobileclient.add_store_track
.. automethod:: Mobileclient.add_store_tracks
.. automethod:: Mobileclient.get_station_track_stream_url

Playlists
---------
Like songs, playlists have unique ids within a library.
However, their names do not need to be unique.

The tracks making up a playlist are referred to as
'playlist entries', and have unique entry ids within the
entire library (not just their containing playlist).

.. automethod:: Mobileclient.get_all_playlists
.. automethod:: Mobileclient.get_all_user_playlist_contents
.. automethod:: Mobileclient.get_shared_playlist_contents
.. automethod:: Mobileclient.create_playlist
.. automethod:: Mobileclient.delete_playlist
.. automethod:: Mobileclient.edit_playlist
.. automethod:: Mobileclient.add_songs_to_playlist
.. automethod:: Mobileclient.remove_entries_from_playlist
.. automethod:: Mobileclient.reorder_playlist_entry

Radio Stations
--------------
Radio Stations are available for free in the US only.
A subscription is required in other countries.

.. automethod:: Mobileclient.get_all_stations
.. automethod:: Mobileclient.create_station
.. automethod:: Mobileclient.delete_stations
.. automethod:: Mobileclient.get_station_tracks

Podcasts
--------

.. automethod:: Mobileclient.get_all_podcast_series
.. automethod:: Mobileclient.get_all_podcast_episodes
.. automethod:: Mobileclient.add_podcast_series
.. automethod:: Mobileclient.delete_podcast_series
.. automethod:: Mobileclient.edit_podcast_series
.. automethod:: Mobileclient.get_podcast_episode_stream_url

Search
------
Search Google Play for information about artists, albums, tracks, and more.

.. automethod:: Mobileclient.search
.. automethod:: Mobileclient.get_genres
.. automethod:: Mobileclient.get_album_info
.. automethod:: Mobileclient.get_artist_info
.. automethod:: Mobileclient.get_podcast_episode_info
.. automethod:: Mobileclient.get_podcast_series_info
.. automethod:: Mobileclient.get_track_info
.. automethod:: Mobileclient.get_station_info

Misc
----

.. automethod:: Mobileclient.get_browse_podcast_hierarchy
.. automethod:: Mobileclient.get_browse_podcast_series
.. automethod:: Mobileclient.get_listen_now_items
.. automethod:: Mobileclient.get_listen_now_situations
