#!/usr/bin/env python

"""Python api for Google Music."""

import json
import re
import string
import time

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from gmapi.session import *
from gmapi.protocol import *
from gmapi.utils import utils
from gmapi.utils.apilogging import LogController

class Api:
    """ Contains abstractions of API calls."""


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

        :param email: eg test@gmail.com
        :param password
        """

        self.wc_session.login(email, password)
        self.mm_session.login(email, password)


        if self.is_authenticated():
            #Need some extra init for upload authentication.
            self._mm_pb_call("upload_auth")
            
            self.log.info("logged in")

            #Probably not needed:
            #self.mm_pb_call("client_state") - not tested
        else:
            self.log.info("failed to log in")

        return self.is_authenticated()

    def logout(self):
        """Log out of the Api.
        Returns True on success, False on failure."""

        self.wc_session.logout()
        self.mm_session.logout()

        self.log.info("logged out")

        return True


    #---
    #   Api features supported by the web client interface:
    #---

    def add_playlist(self, name):
        """Creates a new playlist.

        :param title: the title of the playlist to create.
        """

        return self._wc_call("addplaylist", name)

    @utils.accept_singleton(basestring, 2) #can also accept a single string in pos 2 (song_ids)
    def add_to_playlist(self, playlist_id, song_ids):
        """Adds songs to a playlist.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """

        return self._wc_call("addtoplaylist", playlist_id, song_ids)


    @utils.accept_singleton(dict)
    def change_song_metadata(self, songs):
        """Change the metadata for some songs.
        Songs are presumed to be in GM dictionary format.

        :param songs: a list of songs, or a single song.
        """

        #Warn about metadata changes that may cause problems.
        #If you change the interface, you can warn about changing bad categories, too.
        #Something like safelychange(song, entries) where entries are only those you want to change.
        limited_md = self.wc_protocol.limited_md
        for song_md in songs:
            for key in limited_md:
                if key in song_md and song_md[key] not in limited_md[key]:
                    self.log.warning("setting id (%s)[%s] to a dangerous value. Check metadata expectations in protocol.py", song_md["id"], key)

        return self._wc_call("modifyentries", songs)
        

    def change_playlist_name(self, playlist_id, new_name):
        """Changes the name of a playlist.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """

        return self._wc_call("modifyplaylist", playlist_id, new_name)

    def delete_playlist(self, playlist_id):
        """Deletes a playlist.

        :param playlist_id: id of the playlist to delete.
        """

        return self._wc_call("deleteplaylist", playlist_id)

    @utils.accept_singleton(basestring) #position defaults to 1
    def delete_song(self, song_ids):
        """Delete a song from the entire library.

        :param song_ids: a list of song ids, or a single song id.
        """

        return self._wc_call("deletesong", song_ids)

    def get_library_track_metadata(self):
        """Returns a list of song metadata dictionaries.
        """

        library = []

        lib_chunk = self._wc_call("loadalltracks")
    
        while 'continuationToken' in lib_chunk:
            library += lib_chunk['playlist'] #misleading name; this is the entire chunk
            
            lib_chunk = self._wc_call("loadalltracks", lib_chunk['continuationToken'])

        library += lib_chunk['playlist']

        return library

    def get_playlist_ids(self):
        """Returns a dictionary mapping playlist name to id for all user playlists.
        The dictionary does not include autoplaylists.
        """
        
        #Playlists are built in to the markup server-side.
        #There's a lot of html; rather than parse, it's easier to just cut
        # out the playlists ul, then use a regex.
        res = self.wc_session.open_https_url("https://music.google.com/music/listen?u=0")
        markup = res.read()

        #Get the playlists ul.
        markup = markup[markup.index(r'<ul id="playlists" class="playlistContainer">'):]
        markup = markup[:markup.index(r'</ul>') + 5]


        id_name = re.findall(r'<li id="(.*?)" class="nav-item-container".*?title="(.*?)">', markup)
        
        playlists = {}
        
        for p_id, p_name in id_name:
            playlists[p_name] = p_id

        return playlists

    def get_track_download_info(self, song_id):
        """Returns a tuple of (download url, download_count).

        :param song_id: a single song id.
        """

        #The protocol expects a list of songs - could extend with accept_singleton
        info = self._wc_call("multidownload", [song_id])

        return (info["url"], info["downloadCounts"][song_id])


    def search(self, query):
        """Searches for songs, artists and albums.
        GM ignores punctuation.

        :param query: the search query.
        """

        return self._wc_call("search", query)


    def _wc_call(self, service_name, *args, **kw):
        """Returns the response of a call with the web client session and protocol."""

        #Pull these suppressed calls out somewhere.
        if service_name != "loadalltracks":
            self.log.debug("wc_call: %s(%s)", service_name, str(args))

        protocol_builder = getattr(self.wc_protocol, service_name)

        res = self.wc_session.make_request(service_name, 
                                           protocol_builder(*args, **kw))
        
        res = json.loads(res.read())

        if service_name != "loadalltracks":
            self.log.debug("wc_call response: [%s]", res)

        return res


    #---
    #   Api features supported by the Music Manager interface:
    #---


    #This works, but the protocol isn't quite right.
    #For now, you're better of just taking len(get_library_track_metadata)
    # to get a count of songs in the library.

    # def get_quota(self):
    #     """Returns a tuple of (allowed number of tracks, total tracks, available tracks)."""

    #     quota = self._mm_pb_call("client_state").quota

    #     #protocol incorrect here...
    #     return (quota.maximumTracks, quota.totalTracks, quota.availableTracks)


    #Upload support pulled while deduplication matters are figured out.
    # @utils.accept_singleton(basestring)
    # def upload(self, filenames):
    #     """Uploads the MP3s stored in the given filenames.
    #     Returns a mapping of filename: GM song id for each successful upload.
    #     Returns an empty dictionary if all uploads fail.

    #     :param filenames: a list of filenames, or a single filename
    #     """

    #     #filename -> GM song id
    #     fn_sid_map = {}

    #     #Form and send the metadata request.
    #     metadata_request, cid_map = self.mm_protocol.make_metadata_request(filenames)
    #     metadataresp = self._mm_pb_call("metadata", metadata_request)

    #     #Form upload session requests (for songs GM wants).
    #     session_requests = self.mm_protocol.make_upload_session_requests(cid_map, metadataresp)

    
    #     for filename, server_id, payload in session_requests:

    #         post_data = json.dumps(payload)

    #         #Continuously try for a session.
    #         while True:
                
    #             #Pull this out with the below call when it makes sense to.
    #             res = json.loads(
    #                 self.mm_session.jumper_post(
    #                     "/uploadsj/rupio", 
    #                     post_data).read())

    #             #if options.verbose: print res
    #             if 'sessionStatus' in res: break
    #             time.sleep(3)
    #             #print "Waiting for servers to sync..."

    #         #Got a session; upload the actual file.
    #         up = res['sessionStatus']['externalFieldTransfers'][0]
    #         #print "Uploading a file... this may take a while"

    #         res = json.loads(
    #             self.mm_session.jumper_post( 
    #                 up['putInfo']['url'], 
    #                 open(filename), 
    #                 {'Content-Type': up['content_type']}).read())


    #         #if options.verbose: print res
    #         if res['sessionStatus']['state'] == 'FINALIZED':
    #             fn_sid_map[filename] = server_id


    #     return fn_sid_map


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
