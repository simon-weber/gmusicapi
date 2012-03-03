#!/usr/bin/env python

#Copyright 2012 Simon Weber.

#This file is part of gmapi - the Unofficial Google Music API.

#Gmapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmapi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with gmapi.  If not, see <http://www.gnu.org/licenses/>.


"""`gmapi` enables interaction with Google Music. This includes both web-client and Music Manager features.

This api is not supported nor endorsed by Google, and could break at any time.

**Respect Google in your use of the API.** Use common sense: protocol compliance, reasonable load, etc.
"""

import json
import re
import string
import time
import urllib

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from gmapi.session import WC_Session, MM_Session
from gmapi.protocol import WC_Protocol, MM_Protocol
from gmapi.utils import utils
from gmapi.utils.apilogging import LogController

class Api:
    def __init__(self):
        self.wc_session = WC_Session()
        self.wc_protocol = WC_Protocol()

        self.mm_session = MM_Session()
        self.mm_protocol = MM_Protocol()

        self.log = LogController().get_logger(__name__ + "." + self.__class__.__name__)


    #---
    #   Authentication:
    #---

    def is_authenticated(self):
        """Returns whether the api is logged in."""

        return self.wc_session.logged_in and not (self.mm_session.sid == None)

    def login(self, email, password):
        """Authenticates the api with the given credentials.
        Returns True on success, False on failure.

        Two factor authentication is currently unsupported.

        :param email: eg "`test@gmail.com`"
        :param password: plaintext password. It will not be stored and is sent over ssl."""

        self.wc_session.login(email, password)
        self.mm_session.login(email, password)


        if self.is_authenticated():
            #Need some extra init for upload authentication.
            self._mm_pb_call("upload_auth") #what if this fails? can it?
            self.log.info("logged in")
        else:
            self.log.info("failed to log in")

        return self.is_authenticated()

    def logout(self):
        """Logs out of the api.
        Returns True on success, False on failure."""

        self.wc_session.logout()
        self.mm_session.logout()

        self.log.info("logged out")

        return True


    #---
    #   Api features supported by the web client interface:
    #---


    @utils.accept_singleton(basestring, 2) #can also accept a single string in pos 2 (base 0 - song_ids)
    def add_songs_to_playlist(self, playlist_id, song_ids):
        """Adds songs to a playlist.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """

        return self._wc_call("addtoplaylist", playlist_id, song_ids)

    def change_playlist_name(self, playlist_id, new_name):
        """Changes the name of a playlist.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """

        return self._wc_call("modifyplaylist", playlist_id, new_name)

    @utils.accept_singleton(dict)
    def change_song_metadata(self, songs):
        """Changes the metadata for songs given in `GM Metadata Format`_.

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

        return self._wc_call("modifyentries", songs)
        
    def create_playlist(self, name):
        """Creates a new playlist.

        :param title: the title of the playlist to create.
        """

        return self._wc_call("addplaylist", name)

    def delete_playlist(self, playlist_id):
        """Deletes a playlist.

        :param playlist_id: id of the playlist to delete.
        """

        return self._wc_call("deleteplaylist", playlist_id)

    @utils.accept_singleton(basestring)
    def delete_song(self, song_ids):
        """Deletes songs from the entire library.

        :param song_ids: a list of song ids, or a single song id.
        """

        return self._wc_call("deletesong", song_ids)

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
        """Returns a list of `song dictionaries`__, which include `entryId` keys for the given playlist.

        :param playlist_id: id of the playlist to load.

        __ `GM Metadata Format`_
        """

        return self._wc_call("loadplaylist", playlist_id)["playlist"]

    def get_playlists(self, auto=True, instant=True, user=True):
        """Returns a dictionary mapping playlist types to dictionaries of ``{"<playlist name>": "<playlist id>"}`` pairs.

        Available playlist types are:

        * "`auto`" - auto playlists
        * "`instant`" - instant mixes
        * "`user`" - user-defined playlists

        Playlist names can be unicode strings.

        :param auto: make an "`auto`" entry in the result.
        :param instant: make an "`instant`" entry in the result.
        :param user: make a "`user`" entry in the result.
        """

        playlists = {}
        
        #Only hit the page once for all playlists.
        res = self.wc_session.open_authed_https_url("https://music.google.com/music/listen?u=0")
        markup = res.read()

        if auto:
            playlists['auto'] = self._get_auto_playlists()
        if instant:
            playlists['instant'] = self._get_instant_mixes(markup)
        if user:
            playlists['user'] = self._get_user_playlists(markup)

        return playlists
        
    def _get_auto_playlists(self):
        """For auto playlists, returns a dictionary which maps autoplaylist name to id."""
        
        #Auto playlist ids are hardcoded in the wc javascript.
        #If Google releases Music internationally, this will be broken.
        return {"Thumbs up": "auto-playlist-thumbs-up", 
                "Last added": "auto-playlist-recent",
                "Free and purchased": "auto-playlist-promo"}

    
    def _get_playlists_in(self, ul_id, markup=None):
        """Returns a dictionary mapping playlist name to id for the given ul id in the markup.

        :param ul_id: the id of the unordered list that defines the playlists.
        :markup: (optional) markup of the page."""
        
        #Instant mixes and playlists are built in to the markup server-side.
        #There's a lot of html; rather than parse, it's easier to just cut
        # out the playlists ul, then use a regex.

        if not markup:
            res = self.wc_session.open_authed_https_url("https://music.google.com/music/listen?u=0")
            markup = res.read()

        ul_start = r'<ul id="{0}" class="playlistContainer">'.format(ul_id)

        #Cut out the unordered list containing the playlists.
        markup = markup[markup.index(ul_start):]
        markup = markup[:markup.index(r'</ul>') + 5]

        id_name = re.findall(r'<li id="(.*?)" class="nav-item-container".*?title="(.*?)">', markup)
        
        playlists = {}
        
        for p_id, p_name in id_name:
            playlists[utils.unescape_html(p_name)] = p_id

        return playlists
        
    def _get_instant_mixes(self, markup=None):
        """For instant mixes, returns a dictionary which maps instant mix name to id."""
        return self._get_playlists_in("magic-playlists", markup)

    def _get_user_playlists(self, markup=None):
        """For user-created playlists, returns a dictionary which maps playlist name to id."""
        return self._get_playlists_in("playlists", markup)

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

        *This is only intended for streaming*. The streamed audio does not contain metadata. Use :func:`get_song_download_info` to download complete files with metadata.

        Reading the file does not require authentication.
        
        :param song_id: a single song id.
        """

        #This call is strange. The body is empty, and the songid is passed in the querystring.
        res = self._wc_call("play", query_args={'songid': song_id})
        
        return res['url']
        

    @utils.accept_singleton(basestring)
    def remove_song_from_playlist(self, song_ids, playlist_id):
        """Removes songs from a playlist.

        :param song_ids: a list of song ids, or a single song id.
        """

        #Not as easy as just calling deletesong with the playlist;
        # we need the entryIds for the songs with the playlist as well.

        playlist_tracks = self.get_playlist_songs(playlist_id)

        entry_ids = []

        for sid in song_ids:
            matched_eids = [t["playlistEntryId"] for t in playlist_tracks if t["id"] == sid]
            
            if len(matched_eids) < 1:
                self.log.warning("could not match song id %s to any entryIds")
            else:
                entry_ids.extend(matched_eids)


        return self._wc_call("deletesong", song_ids, entry_ids, playlist_id)

    def search(self, query):
        """Searches for songs, artists and albums.
        GM ignores punctuation.

        :param query: the search query.

        Example response, where <hits> are matching `song dictionaries`__:
        ``{"results":{"artists":[<hits>],"albums":[<hits>],"songs":[<hits>]}}``

        __ `GM Metadata Format`_
        """

        return self._wc_call("search", query)


    def _wc_call(self, service_name, *args, **kw):
        """Returns the response of a web client call.
        :param service_name: the name of the call, eg ``search``
        additional positional arguments are passed to ``build_body``for the retrieved protocol.
        if a 'query_args' key is present in kw, it is assumed to be a dictionary of additional key/val pairs to append to the query string.
        """


        protocol = getattr(self.wc_protocol, service_name)

        if protocol.gets_logged:
            self.log.debug("wc_call: %s(%s)", service_name, str(args))
        
        body = protocol.build_body(*args)
        

        #Encode the body. It might be None (empty).
        #This should probably be done in protocol, and an encoded body grabbed here.
        if body != None: #body can be {}, which is different from None. {} is falsey.
            body = "json=" + urllib.quote_plus(json.dumps(body))

        extra_query_args = None
        if 'query_args' in kw:
            extra_query_args = kw['query_args']

        if protocol.requires_login:
            res = self.wc_session.open_authed_https_url(protocol.build_url, extra_query_args, body)
        else:
            res = self.wc_session.open_https_url(protocol.build_url, extra_query_args, body)
        
        res = json.loads(res.read())

        if protocol.gets_logged:
            self.log.debug("wc_call response: %s", res)

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
    def upload(self, filenames):
        """Uploads the MP3s stored in the given filenames. Returns a dictionary with ``{"<filename>": "<new song id>"}`` pairs for each successful upload.

        Returns an empty dictionary if all uploads fail.

        :param filenames: a list of filenames, or a single filename.

        Unlike Google's Music Manager, this function will currently allow the same song to be uploaded more than once if its tags are changed. This is subject to change in the future.
        """

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
                    self.mm_session.jumper_post(
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

                res = json.loads(
                    self.mm_session.jumper_post( 
                        up['putInfo']['url'], 
                        open(filename), 
                        {'Content-Type': up['content_type']}).read())

            
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

        res.ParseFromString(self.mm_session.protopost(url, req))

        self.log.debug("mm_pb_call response: [%s]", str(res))

        return res
