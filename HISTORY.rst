.. :changelog:

History
-------

As of 1.0.0, `semantic versioning <http://semver.org/>`__ is used.

11.0.1
++++++
released 2018-03-18

- update schemas

11.0.0
++++++
released 2017-12-09

- breaking: list calls now default to max_results=None, increasing the default number of results from 100 to 999
- add updated_after param to song/playlist listing to support differential updates
- add support for free radio stations
- add filepath+extension to unsupported file exception message
- fix "I'm Feeling Lucky" station never refreshing its seed
- fix crashes caused by some 503s during uploading
- fix gmtools for https://github.com/simon-weber/Google-Music-Playlist-Importer
- fix AAC and ALAC content type upload detection
- blacklist requests 2.8.2
- improve id documentation
- update schemas

10.1.2
++++++
released 2017-04-03

- validate device ids to prevent 403s during streaming
- fix LocalUnboundError during login for some environments
- update schemas

10.1.1
++++++
released 2017-02-10

- deprecate include_deleted param to greatly speed up responses for Mobileclient.get_all_*
- Mobileclient.search now works on non-subscription accounts
- fix logging IOError on read-only filesystems
- fix problems caused by broken requests IDNA support

10.1.0
++++++
released 2016-10-31

- deprecate the Webclient
- add podcast support to Mobileclient:
   - get_all_podcast_series
   - get_all_podcast_episodes
   - add_podcast_series
   - delete_podcast_series
   - edit_podcast_series
   - get_podcast_episode_stream_url
   - get_podcast_episode_info
   - get_podcast_series_info
   - get_browse_podcast_hierarchy
   - get_browse_podcast_series
- add Mobileclient.add_store_tracks
- add Mobileclient.rate_songs
- add Musicmanager.get_quota
- fix get_all_user_playlist_contents hanging for large playlists
- fix is_authenticated status after uploader_id exceptions
- fix upload progress tracker remaining after upload
- various internal improvements and schema updates


10.0.1
++++++
released 2016-06-04

- switch to pycryptodomex
- minor schema adjustments

10.0.0
++++++
released 2016-05-01

- breaking: Mobileclient.search_all_access is now Mobileclient.search
- breaking: Mobileclient.add_aa_track is now Mobileclient.add_store_track
- add situation_hits and video_hits to Mobclient.search
- add methods Mobileclient.deauthorize_device, .get_listen_now_items, and .get_listen_now_situations
- add property Mobileclient.is_subscribed
- add playlists and curated stations as station seeds
- add params locale and subscription to Mobileclient.login
- add param enable_transcoding to Musicmanager.upload
- update to newer Google apis, returning more data in responses
- reduce memory usage during uploading
- fix a variety of bugs, mostly python2/3 type errors

9.0.0
+++++
released 2016-03-05

- breaking: attempting to reupload a file after changing only its tags will result in a rejection as a duplicate upload (it used to upload successfully)
- fix webclient login after Google changes
- fix ``'str' object has no attribute 'refresh'``
- prevent upstream protobufs TypeError by locking version
- a 'matched' value may be returned even if matching is not enabled if we were unable to disallow matching

8.0.0
+++++
released 2016-02-08

- breaking: drop support for python < 2.7.9
- add (experimental) python 3 support!
- add Musicmanager.get_purchased_songs
- add station_hits to search_all_access results
- add disc_number and total_disc_count to Musicmanager.get_uploaded_songs
- add a prompt for device id in tests
- upgrade gpsoauth, removing dependency on pycrypto
- deprecate Webclient.create_playlist and Webclient.get_registered_devices
- fix various packaging problems
- fix KeyError in Mobileclient.get_station_tracks
- fix a TypeError from requests
- fix various bits of the docs

7.0.0
+++++
released 2015-09-19

- breaking: python 2.6 is no longer supported
- breaking: webclient.get_registered_devices has a slightly different schema
- fix Webclient authentication and get_stream_urls
- fix MusicManager uploading: Google shut down the rupio endpoint
- fix certificate validation
- fix album artist metadata not being upload

6.0.0
+++++
released 2015-06-20

- fix creation of multiple android devices from android_id=None; support creating device ids from mac address.
- android_id is now optional for mobileclient.get_stream_url, defaulting to android_id from login()

5.0.0
+++++
released 2015-06-02

- breaking: Webclient.login temporarily broken after clientlogin deprecation
- breaking: Mobileclient.get_thumbs_up_songs renamed to mobileclient.get_promoted_songs
- breaking: Mobileclient.change_playlist_name is now edit_playlist
- fix Mobileclient.login breakage due to clientlogin deprecation
- fix Mobileclient.get_genres: return a list and handle invalid parent genres
- add support for filtering out recently played station tracks to Mobileclient.get_station_tracks
- add public playlist results to Mobileclient.search_all_access
- add Mobileclient.get_registered_devices
- add quality option to Mobileclient.get_stream_url
- add support for public playlist creation to Mobileclient.create_playlist
- make optional description param for Webclient.create_playlist
- better handle locating mp3 transcoder


4.0.0
+++++
released 2014-06-08

- breaking: remove webclient.change_song_metadata; use mobileclient.change_song_metadata instead
- breaking: remove webclient.get_all_songs; use mobileclient.get_all_songs instead
- breaking: remove webclient.get_playlist_songs; use mobileclient.get_all_user_playlist_contents instead
- breaking: remove webclient.get_all_playlist_ids; use mobileclient.get_all_user_playlists instead
- breaking: webclient.upload_album_art now returns a url to the uploaded image
- breaking: due to backend changes, mobileclient.change_song_metadata can only change ratings
- add mobileclient.get_thumbs_up_songs
- add mobileclient.increment_song_playcount
- add webclient.create_playlist, which is capable of creating public playlists
- add webclient.get_shared_playlist_info

3.1.0
+++++
released 2014-01-20

- add verify_ssl option to client init
- greatly loosen dependency version requirements

3.0.1
+++++
released 2013-12-11

- remove extraneous logging introduced in 3.0.0 -- this could have logged auth details, so it's recommended to delete old logs

3.0.0
+++++
released 2013-11-03

- Musicmanager.get_all_songs is now Musicmanager.get_uploaded_songs
- Mobileclient.get_all_playlist_contents is now Mobileclient.get_all_user_playlist_contents, and will no longer return results for subscribed playlists
- add Mobileclient.get_shared_playlist_contents
- add Mobileclient.reorder_playlist_entry
- add Mobileclient.change_song_metadata
- add Mobileclient.get_album_info
- add Mobileclient.get_track_info
- add Mobileclient.get_genres
- compatibility fixes

2.0.0
+++++
released 2013-08-01

- remove broken Webclient.{create_playlist, change_playlist, copy_playlist, search, change_playlist_name}
- add Mobileclient; this will slowly replace most of the Webclient, so prefer it when possible
- add support for streaming All Access songs
- add Webclient.get_registered_devices
- add a toggle to turn off validation per client
- raise an exception when a song dictionary is passed instead of an id

1.2.0
+++++
released 2013-05-16

- add support for listing/downloading songs with the Musicmanager.
  When possible, this should be preferred to the Webclient's method, since
  it does not have a download quota.
- fix a bug where the string representing a machine's mac 
  was not properly formed for use as an uploader_id.
  This will cause another machine to be registered for some users;
  the old device can be identified from its lack of a version number.
- verify user-provided uploader_ids

1.1.0
+++++
released 2013-04-19

- get_all_songs can optionally return a generator
- compatibility updates for AddPlaylist call
- log to appdirs.user_log_dir by default
- add open_browser param to perform_oauth

1.0.0
+++++
released 2013-04-02

- breaking: Api has been split into Webclient and Musicmanager
- breaking: semantic versioning (previous versions removed from PyPi)
- Music Manager OAuth support
- faster uploading when matching is disabled
- faster login

2013.03.04
++++++++++

- add artistMatchedId to metadata
- tests are no longer a mess

2013.02.27
++++++++++

- add support for uploading album art (`docs
  <https://unofficial-google-music-api.readthedocs.io/en/
  latest/reference/api.html#gmusicapi.api.Api.upload_album_art>`__)

- add support for .m4b files
- add CancelUploadJobs call (not exposed in api yet)
- Python 2.6 compatibility
- reduced peak memory usage when uploading
- logging improvements
- improved error messages when uploading

2013.02.15
++++++++++

- user now controls logging (`docs
  <https://unofficial-google-music-api.readthedocs.io/en/
  latest/reference/api.html#gmusicapi.api.Api.__init__>`__)

- documentation overhaul

2013.02.14
++++++++++

- fix international logins

2013.02.12
++++++++++

- fix packaging issues

2013.02.11
++++++++++

- improve handling of strange metadata when uploading
- add a dependency on `dateutil <http://labix.org/python-dateutil>`__

2013.02.09
++++++++++

- breaking: upload returns a 3-tuple (`docs
  <https://unofficial-google-music-api.readthedocs.io/en
  /latest/#gmusicapi.api.Api.upload>`__)

- breaking: get_all_playlist_ids always returns lists of ids; remove always_id_lists option
  (`docs <https://unofficial-google-music-api.readthedocs.io/en
  /latest/#gmusicapi.api.Api.get_all_playlist_ids>`__)

- breaking: remove suppress_failure option in Api.__init__
- breaking: copy_playlist ``orig_id`` argument renamed to ``playlist_id`` (`docs
  <https://unofficial-google-music-api.readthedocs.io/en
  /latest/#gmusicapi.api.Api.copy_playlist>`__)

- new: report_incorrect_match (only useful for Music Manager uploads) (`docs
  <https://unofficial-google-music-api.readthedocs.io/en
  /latest/#gmusicapi.api.Api.report_incorrect_match>`__)

- uploading fixed
- avconv replaces ffmpeg
- scan and match is supported
- huge code improvements

2013.01.05
++++++++++

- compatibility update for playlist mutation
- various metadata compatibility updates

2012.11.09
++++++++++

- bugfix: support for uploading uppercase filenames (Tom Graham)
- bugfix: fix typo in multidownload validation, and add test

2012.08.31
++++++++++

- metadata compatibility updates (storeId, lastPlayed)
- fix uploading of unicode filenames without tags

2012.05.04
++++++++++

- update allowed rating values to 1-5 (David Dooling)
- update metajamId to matchedId (David Dooling)
- fix broken expectation about disc/track numbering metadata

2012.04.03
++++++++++

- change to the 3-clause BSD license
- add Kevin Kwok to AUTHORS

2012.04.01
++++++++++

- improve code in example.py
- support uploading of all Google-supported formats: m4a, ogg, flac, wma, mp3. Non-mp3 are transcoded to 320kbs abr mp3 using ffmpeg
- introduce dependency on ffmpeg. for non-mp3 uploading, it needs to be in path and have the needed transcoders available
- get_playlists is now get_all_playlist_ids, and is faster
- add an exception CallFailure. Api functions raise it if the server says their request failed
- add suppress_failure (default False) option to Api.__init__()
- change_playlist now returns the changed playlistId (pid)
- change_song_metadata now returns a list of changed songIds (sids)
- create_playlist now returns the new pid
- delete_playlist now returns the deleted pid
- delete_songs now returns a list of deleted sids
- change_playlist now returns the pid of the playlist - which may differ from the one passed in
- add_songs_to_playlist now returns a list of (sid, new playlistEntryId aka eid) tuples of added songs
- remove_songs_from_playlist now returns a list of removed (sid, eid) pairs
- search dictionary is now flattened, without the "results" key. see documentation for example

2012.03.27
++++++++++

- package for pip/pypi
- add AUTHORS file
- remove session.py; the sessions are now just api.PlaySession (Darryl Pogue)
- protocol.Metadata_Expectations.get_expectation will return UnknownExpectation when queried for unknown keys; this should prevent future problems
- add immutable 'subjectToCuration' and 'metajamId' fields - use unknown

2012.03.16
++++++++++

- add change_playlist for playlist modifications
- get_playlists supports multiple playlists of the same name by returning lists of playlist ids. By default, it will return a single string (the id) for unique playlist names; see the always_id_lists parameter.
- api.login now attempts to bump Music Manager authentication first, bypassing browser emulation. This allows for much faster authentication.
- urls updated for the change to Google Play Music
- remove_songs_from_playlist now takes (playlist_id, song_ids), for consistency with other playlist mutations

2012.03.04
++++++++++

- change name to gmusicapi to avoid ambiguity
- change delete_song and remove_song_from_playlist to delete_songs and remove_songs_from_playlist, for consistency with other functions
- add verification of WC json responses
- setup a sane branch model. see http://nvie.com/posts/a-successful-git-branching-model/
- improve logging
