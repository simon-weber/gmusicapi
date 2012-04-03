#!/usr/bin/env python

# Copyright (c) 2012, Simon Weber
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of the contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""`gmusicapi` enables interaction with Google Music. This includes both web-client and Music Manager features.

This api is not supported nor endorsed by Google, and could break at any time.

**Respect Google in your use of the API.** Use common sense: protocol compliance, reasonable load, etc.
"""

import json
import re
import string
import time
import exceptions
import collections
import copy
import contextlib
import tempfile
import subprocess
import os
#used for _wc_call to get its calling parent.
#according to http://stackoverflow.com/questions/1095543/get-name-of-calling-functions-module-in-python,
# this 
#  "will interact strangely with import hooks, 
#  won't work on ironpython, 
#  and may behave in surprising ways on jython"
import inspect 

try:
    # These are for python3 support
    from urllib.request import HTTPCookieProcessor, Request, build_opener
    from urllib.error import HTTPError
    from urllib.parse import urlencode, quote_plus
    from http.client import HTTPConnection, HTTPSConnection
    unistr = str
except ImportError:
    # Fallback to python2
    from urllib2 import HTTPCookieProcessor, Request, build_opener
    from urllib2 import HTTPError
    from urllib import urlencode, quote_plus
    from httplib import HTTPConnection, HTTPSConnection
    unistr = unicode

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import validictory

from protocol import WC_Protocol, MM_Protocol
from utils import utils
from utils.apilogging import UsesLog
from gmtools import tools
from utils.clientlogin import ClientLogin
from utils.tokenauth import TokenAuth

supported_upload_filetypes = ("mp3", "m4a", "ogg", "flac", "wma") 

class CallFailure(exceptions.Exception):
    """Exception raised when the Google Music server responds that a call failed.
    
    Attributes:
        name -- name of Api function that had the failing call
        res  -- the body of the failed response
    """
    def __init__(self, name, res):
        self.name = name
        self.res = res

    def __str__(self):
        return "api call {} failed; server returned {}".format(self.name, self.res)

class Api(UsesLog):
    def __init__(self, suppress_failure=False):
        """Initializes an Api.

        :param suppress_failure: when True, never raise CallFailure when a call fails.
        """

        self.suppress_failure = suppress_failure

        self.session = PlaySession()

        self.wc_protocol = WC_Protocol()
        self.mm_protocol = MM_Protocol()

        self.init_logger()
    
    @contextlib.contextmanager
    def _unsuppress_failures(self):
        """An internal context manager to temporarily disable failure suppression.

        This should wrap any Api code which tries to catch CallFailure."""

        orig = self.suppress_failure
        self.suppress_failure = False
        try:
            yield
        finally:
            self.suppress_failure = orig

    #---
    #   Authentication:
    #---

    def is_authenticated(self):
        """Returns whether the api is logged in."""
        return self.session.logged_in


    def login(self, email, password):
        """Authenticates the api with the given credentials.
        Returns True on success, False on failure.

        :param email: eg "`test@gmail.com`"
        :param password: plaintext password. It will not be stored and is sent over ssl.

        Users of two-factor authentication will need to set an application-specific password
        to log in."""

        self.session.login(email, password)

        if self.is_authenticated():
            #Need some extra init for upload authentication.
            self._mm_pb_call("upload_auth") #what if this fails? can it?
            self.log.info("logged in")
        else:
            self.log.info("failed to log wc in")

        return self.is_authenticated()

    def logout(self):
        """Logs out of the api.
        Returns True on success, False on failure."""

        self.session.logout()
        self.log.info("logged out")

        return True


    #---
    #   Api features supported by the web client interface:
    #---

    def change_playlist_name(self, playlist_id, new_name):
        """Changes the name of a playlist. Returns the changed id.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """

        self._wc_call("modifyplaylist", playlist_id, new_name)

        return playlist_id #the call actually doesn't return anything.

    @utils.accept_singleton(dict)
    @utils.empty_arg_shortcircuit()
    def change_song_metadata(self, songs):
        """Changes the metadata for songs given in `GM Metadata Format`_. Returns a list of the song ids changed.

        :param songs: a list of song dictionaries, or a single song dictionary.


        The server response is *not* to be trusted. Instead, reload the library; this will always reflect changes.

        These metadata keys are able to be changed:
        
        * rating: set to 0 (no thumb), 1 (down thumb), or 5 (up thumb)
        * name: use this instead of `title`
        * album
        * albumArtist
        * artist
        * composer
        * disc
        * genre
        * playCount
        * totalDiscs
        * totalTracks
        * track
        * year

        These keys cannot be changed:
        
        * comment
        * id 
        * deleted
        * creationDate
        * albumArtUrl
        * type
        * beatsPerMinute
        * url

        These keys cannot be changed; their values are determined by another key's value:

        * title: set to `name`
        * titleNorm: set to lowercase of `name`
        * albumArtistNorm: set to lowercase of `albumArtist`
        * albumNorm: set to lowercase of `album`
        * artistNorm: set to lowercase of `artist`

        These keys cannot be changed, and may change unpredictably:

        * lastPlayed: likely some kind of last-accessed timestamp
        """

        res = self._wc_call("modifyentries", songs)
        
        return [s['id'] for s in res['songs']]
        
    def create_playlist(self, name):
        """Creates a new playlist. Returns the new playlist id.

        :param title: the title of the playlist to create.
        """

        return self._wc_call("addplaylist", name)['id']

    def delete_playlist(self, playlist_id):
        """Deletes a playlist. Returns the deleted id.

        :param playlist_id: id of the playlist to delete.
        """

        return self._wc_call("deleteplaylist", playlist_id)['deleteId']

    @utils.accept_singleton(basestring)
    @utils.empty_arg_shortcircuit()
    def delete_songs(self, song_ids):
        """Deletes songs from the entire library. Returns a list of deleted song ids.

        :param song_ids: a list of song ids, or a single song id.
        """

        return self._wc_call("deletesong", song_ids)['deleteIds']

    def get_all_songs(self):
        """Returns a list of `song dictionaries`__.
        
        __ `GM Metadata Format`_
        """

        library = []

        lib_chunk = self._wc_call("loadalltracks")
    
        while 'continuationToken' in lib_chunk:
            library += lib_chunk['playlist'] #misleading name; this is the entire chunk
            
            lib_chunk = self._wc_call("loadalltracks", lib_chunk['continuationToken'])

        library += lib_chunk['playlist']

        return library

    def get_playlist_songs(self, playlist_id):
        """Returns a list of `song dictionaries`__, which include `playlistEntryId` keys for the given playlist.

        :param playlist_id: id of the playlist to load.

        __ `GM Metadata Format`_
        """

        return self._wc_call("loadplaylist", playlist_id)["playlist"]

    def get_all_playlist_ids(self, auto=True, instant=True, user=True, always_id_lists=False):
        """Returns a dictionary mapping playlist types to dictionaries of ``{"<playlist name>": "<playlist id>"}`` pairs.

        Available playlist types are:

        * "`auto`" - auto playlists
        * "`instant`" - instant mixes
        * "`user`" - user-defined playlists

        :param auto: make an "`auto`" entry in the result.
        :param instant: make an "`instant`" entry in the result.
        :param user: make a "`user`" entry in the result.
        :param always_id_lists: when False, map name -> id when there is a single playlist for that name. When True, always map to a list (which may only have a single id in it).

        Google Music allows for multiple playlists of the same name. Since this is uncommon, `always_id_lists` is False by default: names will map directly to ids when unique. However, this can create ambiguity if the api user doesn't have advance knowledge of the playlists. In this case, setting `always_id_lists` to True is recommended.

        Note that playlist names can be unicode strings.
        """

        playlists = {}

        res = self._wc_call("loadplaylist", "all")

        if auto:
            playlists['auto'] = self._get_auto_playlists()
        if instant:
            playlists['instant'] = self._playlist_list_to_dict(res['magicPlaylists'])
        if user:
            playlists['user'] = self._playlist_list_to_dict(res['playlists'])

        #Break down singleton lists if desired.
        if not always_id_lists:
            for p_dict in playlists.itervalues():
                for name, id_list in p_dict.iteritems():
                    if len(id_list) == 1: p_dict[name]=id_list[0]
        
        return playlists
        
    def _playlist_list_to_dict(self, pl_list):
        d = {}

        for name, pid in ((p["title"], p["playlistId"]) for p in pl_list):
            if not name in d: d[name] = []
            d[name].append(pid)

        return d
        
    def _get_auto_playlists(self):
        """For auto playlists, returns a dictionary which maps autoplaylist name to id."""
        
        #Auto playlist ids are hardcoded in the wc javascript.
        #If Google releases Music internationally, this will probably be broken.
        #TODO: how to test for this? if loaded, will the calls just fail?
        return {"Thumbs up": "auto-playlist-thumbs-up", 
                "Last added": "auto-playlist-recent",
                "Free and purchased": "auto-playlist-promo"}

    def get_song_download_info(self, song_id):
        """Returns a tuple ``("<download url>", <download count>)``.

        GM allows 2 downloads per song.

        :param song_id: a single song id.
        """

        #The protocol expects a list of songs - could extend with accept_singleton
        info = self._wc_call("multidownload", [song_id])

        return (info["url"], info["downloadCounts"][song_id])

    def get_stream_url(self, song_id):
        """Returns a url that points to a streamable version of this song. 

        :param song_id: a single song id.

        *This is only intended for streaming*. The streamed audio does not contain metadata. Use :func:`get_song_download_info` to download complete files with metadata.

        Reading the file does not require authentication.        
        """

        #This call is strange. The body is empty, and the songid is passed in the querystring.
        res = self._wc_call("play", query_args={'songid': song_id})
        
        return res['url']
        
    def copy_playlist(self, orig_id, copy_name):
        """Copies the contents of a playlist to a new playlist. Returns the id of the new playlist.

        :param orig_id: id of the playlist to be copied.
        :param copy_name: the name of the new copied playlist.

        Useful for making backups of playlists before modifications.
        """
        
        orig_tracks = self.get_playlist_songs(orig_id)
        
        new_id = self.create_playlist(copy_name)
        self.add_songs_to_playlist(new_id, [t["id"] for t in orig_tracks])

        return new_id

    def change_playlist(self, playlist_id, desired_playlist, safe=True):
        """Changes the order and contents of an existing playlist. Returns the id of the playlist when finished - which may not be the argument, in the case of a failure and recovery.
        
        :param playlist_id: the id of the playlist being modified.
        :param desired_playlist: the desired contents and order as a list of song dictionaries, like is returned from :func:`get_playlist_songs`.
        :param safe: if True, ensure playlists will not be lost if a problem occurs. This may slow down updates.

        The server only provides 3 basic (atomic) playlist mutations: addition, deletion, and reordering. This function will automagically use these to apply a list representation of the desired changes.

        However, this might involve multiple calls to the server, and if a call fails, the playlist will be left in an inconsistent state. The `safe` option makes a backup of the playlist before doing anything, so it can be rolled back if a problem occurs. This is enabled by default. Note that this might slow down updates of very large playlists.

        There will always be a warning logged if a problem occurs, even if `safe` is False.
        """
        
        #We'll be modifying the entries in the playlist, and need to copy it.
        #Copying ensures two things:
        # 1. the user won't see our changes
        # 2. changing a key for one entry won't change it for another - which would be the case
        #     if the user appended the same song twice, for example.
        desired_playlist = [copy.deepcopy(t) for t in desired_playlist]
        server_tracks = self.get_playlist_songs(playlist_id)

        if safe: #make the backup.
            #The backup is stored on the server as a new playlist with "_gmusicapi_backup" appended to the backed up name.
            #We can't just store the backup here, since when rolling back we'd be relying on this function - and it just failed.
            names_to_ids = self.get_all_playlist_ids(always_id_lists=True)['user']
            playlist_name = (ni_pair[0] 
                             for ni_pair in names_to_ids.iteritems()
                             if playlist_id in ni_pair[1]).next()

            backup_id = self.copy_playlist(playlist_id, playlist_name + "_gmusicapi_backup")

        #Ensure CallFailures do not get suppressed in our subcalls.
        #Did not unsuppress the above copy_playlist call, since we should fail 
        # out if we can't ensure the backup was made.
        with self._unsuppress_failures():
            try:
                #Counter, Counter, and set of id pairs to delete, add, and keep.
                to_del, to_add, to_keep = tools.find_playlist_changes(server_tracks, desired_playlist)

                ##Delete unwanted entries.
                to_del_eids = [pair[1] for pair in to_del.elements()]
                if to_del_eids: self._remove_entries_from_playlist(playlist_id, to_del_eids)

                ##Add new entries.
                to_add_sids = [pair[0] for pair in to_add.elements()]
                if to_add_sids:
                    new_pairs = self.add_songs_to_playlist(playlist_id, to_add_sids)

                    ##Update desired tracks with added tracks server-given eids.
                    #Map new sid -> [eids]
                    new_sid_to_eids = {}
                    for sid, eid in new_pairs:
                        if not sid in new_sid_to_eids:
                            new_sid_to_eids[sid] = []
                        new_sid_to_eids[sid].append(eid)


                    for d_t in desired_playlist:
                        if d_t["id"] in new_sid_to_eids:
                            #Found a matching sid.
                            match = d_t
                            sid = match["id"]
                            eid = match.get("playlistEntryId") 
                            pair = (sid, eid)

                            if pair in to_keep:
                                to_keep.remove(pair) #only keep one of the to_keep eids.
                            else:
                                match["playlistEntryId"] = new_sid_to_eids[sid].pop()
                                if len(new_sid_to_eids[sid]) == 0:
                                    del new_sid_to_eids[sid]


                ##Now, the right eids are in the playlist.
                ##Set the order of the tracks:

                #The web client has no way to dictate the order without block insertion,
                # but the api actually supports setting the order to a given list.
                #For whatever reason, though, it needs to be set backwards; might be
                # able to get around this by messing with afterEntry and beforeEntry parameters.
                sids, eids = zip(*tools.get_id_pairs(desired_playlist[::-1]))

                if sids: self._wc_call("changeplaylistorder", playlist_id, sids, eids)

                ##Clean up the backup.
                if safe: self.delete_playlist(backup_id)

            except CallFailure:
                self.log.warning("a subcall of change_playlist failed - playlist %s is in an inconsistent state", playlist_id)

                if not safe: raise #there's nothing we can do
                else: #try to revert to the backup
                    self.log.warning("attempting to revert changes from playlist '%s_gmusicapi_backup'", playlist_name)

                    try:
                        self.delete_playlist(playlist_id)
                        self.change_playlist_name(backup_id, playlist_name)
                    except CallFailure:
                        self.log.error("failed to revert changes.")
                        raise
                    else:
                        self.log.warning("reverted changes safely; playlist id of '%s' is now '%s'", playlist_name, backup_id)
                        playlist_id = backup_id
            finally:
                return playlist_id
    
    @utils.accept_singleton(basestring, 2)
    @utils.empty_arg_shortcircuit(position=2)
    def add_songs_to_playlist(self, playlist_id, song_ids):
        """Adds songs to a playlist. Returns a list of (song id, playlistEntryId) tuples that were added.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """

        return [(s['songId'], s['playlistEntryId'])
                for s in 
                self._wc_call("addtoplaylist", playlist_id, song_ids)['songIds']]

    @utils.accept_singleton(basestring, 2)
    @utils.empty_arg_shortcircuit(position=2)
    def remove_songs_from_playlist(self, playlist_id, sids_to_match):
        """Removes all copies of the given song ids from a playlist. Returns a list of removed (sid, eid) pairs.

        :param playlist_id: id of the playlist to remove songs from.
        :param sids_to_match: a list of songids to match, or a single song id.

        This does *not always* the inverse of a call to :func:`add_songs_to_playlist`, since multiple copies of the same song are removed. For more control in this case, get the playlist tracks with :func:`get_playlist_songs`, modify the list of tracks, then use :func:`change_playlist` to push changes to the server.
        """

        playlist_tracks = self.get_playlist_songs(playlist_id)
        sid_set = set(sids_to_match)

        matching_eids = [t["playlistEntryId"]
                         for t in playlist_tracks
                         if t["id"] in sid_set]

        if matching_eids:
            #Call returns "sid_eid" strings.
            sid_eids = self._remove_entries_from_playlist(playlist_id, 
                                                          matching_eids)
            return [s.split("_") for s in sid_eids]
        else:
            return []
    
    @utils.accept_singleton(basestring, 2)
    @utils.empty_arg_shortcircuit(position=2)
    def _remove_entries_from_playlist(self, playlist_id, entry_ids_to_remove):
        """Removes entries from a playlist. Returns a list of removed "sid_eid" strings.

        :param playlist_id: the playlist to be modified.
        :param entry_ids: a list of entry ids, or a single entry id.
        """

        #GM requires the song ids in the call as well; find them.
        playlist_tracks = self.get_playlist_songs(playlist_id)
        remove_eid_set = set(entry_ids_to_remove)
        
        e_s_id_pairs = [(t["id"], t["playlistEntryId"]) 
                        for t in playlist_tracks
                        if t["playlistEntryId"] in remove_eid_set]

        num_not_found = len(entry_ids_to_remove) - len(e_s_id_pairs)
        if num_not_found > 0:
            self.log.warning("when removing, %d entry ids could not be found in playlist id %s", num_not_found, playlist_id)

        #Unzip the pairs.
        sids, eids = zip(*e_s_id_pairs)

        return self._wc_call("deletesong", sids, eids, playlist_id)['deleteIds']
    
        
    def search(self, query):
        """Searches for songs and albums.

        :param query: the search query.


        Search results are organized based on how they were found. Hits on an album title return information on that album. Here is an example album result::

            {'artistName': 'The Cat Empire',
             'imageUrl': '<url>',
             'albumArtist': 'The Cat Empire', 
             'albumName': 'Cities: The Cat Empire Project'}
        
        Hits on song or artist name return the matching `song dictionary`__.

        The responses are returned in a dictionary, arranged by hit type::

              {'album_hits':[<album dictionary>, ...],
               'artist_hits':[<song dictionary>, ...],
               'song_hits':[<song dictionary>, ...]}

        The search ignores punctuation.

        __ `GM Metadata Format`_
        """

        res = self._wc_call("search", query)['results']

        return {"album_hits":res["albums"],
                "artist_hits":res["artists"],
                "song_hits":res["songs"]}


    def _wc_call(self, service_name, *args, **kw):
        """Returns the response of a web client call.
        :param service_name: the name of the call, eg ``search``
        additional positional arguments are passed to ``build_body``for the retrieved protocol.
        if a 'query_args' key is present in kw, it is assumed to be a dictionary of additional key/val pairs to append to the query string.
        """


        protocol = getattr(self.wc_protocol, service_name)

        #Always log the request.
        self.log.debug("wc_call %s %s", service_name, args)
        
        body, res_schema = protocol.build_transaction(*args)
        

        #Encode the body. It might be None (empty).
        if body is not None: #body can be {}, which is different from None. {} is falsey.
            body = "json=" + quote_plus(json.dumps(body))

        extra_query_args = None
        if 'query_args' in kw:
            extra_query_args = kw['query_args']

        res = self.session.open_web_url(protocol.build_url, extra_query_args, body)
        
        read = res.read()
        res = json.loads(read)

        if protocol.gets_logged:
            self.log.debug("wc_call response %s", res)
        else:
            self.log.debug("wc_call response <suppressed>")

        #Check if the server reported success.
        success = utils.call_succeeded(res)
        if not success:
            self.log.error("call to %s failed", service_name)
            self.log.debug("full response: %s", res)
            
            if not self.suppress_failure:
                calling_func_name = inspect.stack()[1][3]
                raise CallFailure(calling_func_name, res) #normally caused by bad arguments to the server

        #Calls are not required to have a schema, and
        # schemas are only for successful calls.
        if success and res_schema:
            try:
                validictory.validate(res, res_schema)
            except ValueError as details:
                self.log.warning("Received an unexpected response from call %s.", service_name)
                self.log.debug("full response: %s", res)
                self.log.debug("failed schema: %s", res_schema)
                self.log.warning("error was: %s", details)
                    
        return res


    #---
    #   Api features supported by the Music Manager interface:
    #---


    #This works, but the protocol isn't quite right.
    #For now, you're better off just taking len(get_all_songs)
    # to get a count of songs in the library. 20,000 songs is the limit for free users.

    # def get_quota(self):
    #     """Returns a tuple of (allowed number of tracks, total tracks, available tracks)."""

    #     quota = self._mm_pb_call("client_state").quota

    #     #protocol incorrect here...
    #     return (quota.maximumTracks, quota.totalTracks, quota.availableTracks)

    

    @utils.accept_singleton(basestring)
    @utils.empty_arg_shortcircuit(ret={})
    def upload(self, filenames):
        """Uploads the given filenames. Returns a dictionary with ``{"<filename>": "<new song id>"}`` pairs for each successful upload.

        Returns an empty dictionary if all uploads fail. CallFailure will never be raised.

        :param filenames: a list of filenames, or a single filename.

        All Google-supported filetypes are supported. Non-mp3 files will be transcoded to a 320kbs abr mp3 before being uploaded, just as Google's Music Manager does. The original filename will be returned, not the name of transcoded file.

        Unlike Google's Music Manager, this function will currently allow the same song to be uploaded more than once if its tags are changed. This is subject to change in the future.
        """
        if not filenames:
            return {}

        results = {}

        with self._temp_mp3_conversion(filenames) as (upload_files, orig_fnames):

            fname_to_id = self._upload_mp3s(map(lambda f: f.name, upload_files))

            for fname, sid in fname_to_id.items():
                results[orig_fnames[fname]] = sid

        return results
        

    @contextlib.contextmanager
    def _temp_mp3_conversion(self, filenames):
        """An internal context manager that converts files to temp mp3 files if needed.
        Returns (list of file objects, {'temp filename':'orig fname'})

        Only supported non-mp3s are converted and given a temp file."""
        
        temp_file_handles = []
        all_file_handles = []

        temp_to_orig = {}

        try:
            for orig_fn in filenames:
                extension = orig_fn.split(".")[-1]

                if extension == "mp3":
                    all_file_handles.append(file(orig_fn))
                    temp_to_orig[orig_fn] = orig_fn

                elif extension in supported_upload_filetypes:
                    t_handle = tempfile.NamedTemporaryFile(prefix="gmusicapi", suffix=".mp3", delete=False)
                    temp_file_handles.append(t_handle)

                    try:
                        self.log.info("converting %s to %s", orig_fn, t_handle.name)
                        err_output = None

                        #pipe:1 -> send output to stdout
                        p = subprocess.Popen(["ffmpeg", "-i", orig_fn, "-f", "mp3", "-ab", "320k", "pipe:1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        
                        audio_data, err_output = p.communicate()
                        
                        #Check for success and write out our temp file.
                        if p.returncode is not 0:
                            raise OSError
                        else:
                            t_handle.write(audio_data)
                            

                    except OSError as e:
                        if err_output is not None:
                            self.log.error("FFmpeg could not convert the file to mp3. output was: %s", err_output)
                        else:
                            self.log.exception("is FFmpeg installed? Failed to convert '%s' to mp3 while uploading. This file will not be uploaded. Error was:", orig_fn)

                        continue

                    finally:
                        #Close the file so mutagen can write out its tags.
                        t_handle.close()
                        

                    #Copy tags over. It's easier to do this here than mess with
                    # passing overriding metadata into _upload() later on
                    if not utils.copy_md_tags(orig_fn, t_handle.name):
                        self.log.warn("failed to copy metadata to converted temp mp3 for '%s'. This file will still be uploaded, but Google Music may not receive (some of) its metadata.", orig_fn)

                    all_file_handles.append(t_handle)
                    temp_to_orig[t_handle.name] = orig_fn

                else:
                    self.log.error("'%s' is not of a supported filetype, and cannot be uploaded. Supported filetypes: %s", orig_fn, supported_upload_filetypes)


            yield all_file_handles, temp_to_orig

        finally:
            #Ensure all temp files get deleted.
            for t in temp_file_handles:
                try:
                    os.remove(t.name)
                except OSError:
                    self.log.exception("failed to delete temporary file '%s'", t.name)

    def _upload_mp3s(self, filenames):
        """Uploads a list of files. All files are assumed to be mp3s."""

        #filename -> GM song id
        fn_sid_map = {}

        #Form and send the metadata request.
        metadata_request, cid_map = self.mm_protocol.make_metadata_request(filenames)
        metadataresp = self._mm_pb_call("metadata", metadata_request)

        #Form upload session requests (for songs GM wants).
        session_requests = self.mm_protocol.make_upload_session_requests(cid_map, metadataresp)

        #Try to get upload sessions and upload each song.
        #This section is in bad need of refactoring.
        for filename, server_id, payload in session_requests:

            post_data = json.dumps(payload)

            success = False
            already_uploaded = False
            attempts = 0

            while not success and attempts < 3:
                
                #Pull this out with the below call when it makes sense to.
                res = json.loads(
                    self.session.post_jumper(
                        "/uploadsj/rupio", 
                        post_data).read())

                if 'sessionStatus' in res:
                    self.log.debug("got a session. full response: %s", str(res))
                    success = True
                    break


                elif 'errorMessage' in res:
                    self.log.debug("upload error. full response: %s", str(res))

                    error_code = res['errorMessage']['additionalInfo']['uploader_service.GoogleRupioAdditionalInfo']['completionInfo']['customerSpecificInfo']['ResponseCode']

                    #This seems more like protocol-worthy information.
                    if error_code == 503:
                        #Servers still syncing; retry with no penalty.
                        self.log.info("upload servers still syncing; trying again.")
                        attempts -= 1

                    elif error_code == 200:
                        #GM reports that the file is already uploaded, probably because the hash matched a server-side file.
                        self.log.warning("GM upload server reports %s is already uploaded as sid: %s", filename, server_id)
                        success = True
                        already_uploaded = True
                        break

                    elif error_code == 404:
                        #Bad request. I've never seen this resolve through retries.
                        self.log.warning("GM upload server")

                    else:
                        #Unknown error code.
                        self.log.warning("upload service reported an unknown error code. Please report this to the project.\n  entire response: %s", str(res))
                    
                else:
                    self.log.warning("upload service sent back a response that could not be interpreted. Please report this to the project.\n  entire response: %s", str(res))
                    
                                        
                time.sleep(3)
                self.log.info("trying again for a session.")
                attempts += 1

            if success and not already_uploaded:
                #Got a session; upload the actual file.
                up = res['sessionStatus']['externalFieldTransfers'][0]
                self.log.info("uploading file. sid: %s", server_id)

                with open(filename, mode="rb") as audio_data:
                    res = json.loads(
                        self.session.post_jumper( 
                            up['putInfo']['url'], 
                            audio_data, 
                            {'Content-Type': up['content_type']}).read())
                
                self.log.debug("post_jumper res: %s", res)

            
                if res['sessionStatus']['state'] == 'FINALIZED':
                    fn_sid_map[filename] = server_id
                    self.log.info("successfully uploaded sid %s", server_id)

            elif already_uploaded:
                fn_sid_map[filename] = server_id

            else:
                self.log.warning("could not upload file %s (sid %s)", filename, server_id)

        return fn_sid_map


    def _mm_pb_call(self, service_name, req = None):
        """Returns the protobuff response of a call to a predefined Music Manager protobuff service."""

        self.log.debug("mm_pb_call: %s(%s)", service_name, str(req))

        res = self.mm_protocol.make_pb(service_name + "_response")

        if not req:
            try:
                req = self.mm_protocol.make_pb(service_name + "_request")
            except AttributeError:
                req = self.mm_protocol.make_pb(service_name) #some request types don't have _request appended.

        url = self.mm_protocol.pb_services[service_name]

        res.ParseFromString(self.session.post_protobuf(url, req))

        self.log.debug("mm_pb_call response: [%s]", str(res))

        return res

#---
#The session layer:
#---

class AlreadyLoggedIn(Exception):
    pass

class NotLoggedIn(Exception):
    pass

class PlaySession(object):
    """
    A Google Play Music session.

    It allows for authentication and the making of authenticated
    requests through the MusicManager API (protocol buffers), Web client requests,
    and the Skyjam client API.
    """

    # The URL for authenticating against Google Play Music
    PLAY_URL = 'https://play.google.com/music/listen?u=0&hl=en'

    # Common User Agent used for web requests
    _user_agent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.6) Gecko/20061201 Firefox/2.0.0.6 (Ubuntu-feisty)"

    def __init__(self):
        """
        Initializes a default unauthenticated session.
        """
        self.client = None
        self.cookies = None
        self.logged_in = False

        # Wish there were better names for these
        self.android = HTTPSConnection('android.clients.google.com')
        self.jumper  = HTTPConnection('uploadsj.clients.google.com')


    def _get_cookies(self):
        """
        Gets cookies needed for web and media streaming access.
        Returns True if the necessary cookies are found, False otherwise.
        """
        if self.logged_in:
            raise AlreadyLoggedIn

        handler = build_opener(HTTPCookieProcessor(self.cookies))
        req = Request(self.PLAY_URL, None, {}) #header)
        resp_obj = handler.open(req)

        return  (
                    self.get_cookie('sjsaid') is not None and
                    self.get_cookie('xt') is not None
                )


    def get_cookie(self, name):
        """
        Finds the value of a cookie by name, returning None on failure.

        :param name: The name of the cookie to find.
        """
        for cookie in self.cookies:
            if cookie.name == name:
                return cookie.value

        return None


    def login(self, email, password):
        """
        Attempts to create an authenticated session using the email and
        password provided.
        Return True if the login was successful, False otherwise.
        Raises AlreadyLoggedIn if the session is already authenticated.

        :param email: The email address of the account to log in.
        :param password: The password of the account to log in.
        """
        if self.logged_in:
            raise AlreadyLoggedIn

        self.client = ClientLogin(email, password, 'sj')
        tokenauth = TokenAuth('sj', self.PLAY_URL, 'jumper')

        if self.client.get_auth_token() is None:
            return False

        tokenauth.authenticate(self.client)
        self.cookies = tokenauth.get_cookies()

        self.logged_in = self._get_cookies()

        return self.logged_in


    def logout(self):
        """
        Resets the session to an unauthenticated default state.
        """
        self.__init__()


    def open_web_url(self, url_builder, extra_args=None, data=None, ua=None):
        """
        Opens an https url using the current session and returns the response.
        Code adapted from:
        http://code.google.com/p/gdatacopier/source/browse/tags/gdatacopier-1.0.2/gdatacopier.py

        :param url_builder: the url, or a function to receieve a dictionary of querystring arg/val pairs and return the url.
        :param extra_args: (optional) key/val querystring pairs.
        :param data: (optional) encoded POST data.
        :param ua: (optional) The User Age to use for the request.
        """
        # I couldn't find a case where we don't need to be logged in
        if not self.logged_in:
            raise NotLoggedIn

        if isinstance(url_builder, basestring):
            url = url_builder
        else:
            url = url_builder({'xt':self.get_cookie("xt")})

        #Add in optional pairs to the querystring.
        if extra_args:
            #Assumes that a qs has already been started (ie we don't need to put a ? first)
            assert (url.find('?') >= 0)

            extra_url_args = ""
            for name, val in extra_args.iteritems():
                extra_url_args += "&{0}={1}".format(name, val)

            url += extra_url_args

        opener = build_opener(HTTPCookieProcessor(self.cookies))

        if not ua:
            ua = self._user_agent

        opener.addheaders = [('User-agent', ua)]

        if data:
            response = opener.open(url, data)
        else:
            response = opener.open(url)

        return response


    def post_protobuf(self, path, protobuf):
        """
        Returns the response from encoding and posting the given data.

        :param path: the name of the service url
        :param proto: data to be encoded with protobuff
        """
        if not self.logged_in:
            raise NotLoggedIn

        urlpath = '/upsj/' + path
        self.android.request('POST', urlpath, protobuf.SerializeToString(), {
            'Cookie':       'SID=%s' % self.client.get_sid_token(),
            'Content-Type': 'application/x-google-protobuf'
        })

        resp = self.android.getresponse()

        return resp.read()


    def post_jumper(self, url, encoded_data, headers=None):
        """
        Returns the response of a post to the MusicManager jumper service.
        """
        if not self.logged_in:
            raise NotLoggedIn

        if not headers:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cookie':       'SID=%s' % self.client.get_sid_token()
            }

        self.jumper.request('POST', url, encoded_data, headers)
        return self.jumper.getresponse()
