"""The session layer allows for authentication and the making of authenticated requests."""

import mechanize
import cookielib
import exceptions
import urllib
import urllib2
import os
import json
import warnings

from decorator import decorator

from urllib2  import *
from urlparse import *

import httplib
from uuid import getnode as getmac
from socket import gethostname
import metadata_pb2
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import random
import string
import time


class AlreadyLoggedIn(exceptions.Exception):
    pass
class NotLoggedIn(exceptions.Exception):
    pass


class WC_Session():
    """A session for the GM web client."""

    _base_url = 'https://music.google.com/music/services/'

    #The wc requires a common user agent.
    _user_agent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1.6) Gecko/20061201 Firefox/2.0.0.6 (Ubuntu-feisty)"


    def __init__(self):
        self._cookie_jar = cookielib.LWPCookieJar() #to hold the session
        self.logged_in = False

    def logout(self):
        self.__init__() #discard our session
        
    def open_https_url(self, target_url, encoded_data = None):
        """Opens an https url using the current session and returns the response.
        Code adapted from: http://code.google.com/p/gdatacopier/source/browse/tags/gdatacopier-1.0.2/gdatacopier.py

        :param target_url: full https url to open.
        :param encoded_data: (optional) encoded POST data.
        """

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self._cookie_jar))

        opener.addheaders = [('User-agent', self._user_agent)]
        
        if encoded_data:
            response = opener.open(target_url, encoded_data)
        else:
            response = opener.open(target_url)
            
        return response

    def get_cookie(self, name):
        """Finds a cookie by name from the cookie jar.
        Returns None on failure.

        :param name:
        """

        for cookie in self._cookie_jar:
            if cookie.name == name:
                return cookie

        return None

    def login(self, email, password):
        """Attempts to login with the given credentials.
        Returns True on success, False on failure.
        
        :param email:
        :param password:
        """

        if self.logged_in:
            raise AlreadyLoggedIn

        #It's easiest just to emulate a browser; some fields are filled by javascript.
        #This code adapted from: http://stockrt.github.com/p/emulating-a-browser-in-python-with-mechanize/

        br = mechanize.Browser()
        br.set_cookiejar(self._cookie_jar)

        # Browser options
        br.set_handle_equiv(True)
        
        #Suppress warning that gzip support is experimental.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            br.set_handle_gzip(True) 

        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)

        # Follows refresh 0 but doesn't hang on refresh > 0
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

        # Google auth requires a common user-agent.
        br.addheaders = [('User-agent', self._user_agent)]

        br.open('https://music.google.com')

        br.select_form(nr=0)

        br.form['Email']=email
        br.form['Passwd']=password
        br.submit()

        self.logged_in = True if self.get_cookie("SID") else False

        return self.logged_in
    
    def make_request(self, call, data):
        """Sends a request to Google Music; returns the response.

        :param call: the name of the service, eg 'search'.
        :param data: Python representation of the json query.
        """

        if not self.logged_in:
            raise NotLoggedIn

        xt_val = self.get_cookie("xt").value

        #The url passes u=0 and the xt cookie's value. Not sure what the u is for.
        url = self._base_url + call + '?u=0&xt=' + xt_val

        #GM needs the input to be named json.
        encoded_data = "json=" + urllib.quote_plus(json.dumps(data))
        
        return self.open_https_url(url, encoded_data)


class MM_Session:    
    """A session for the Music Manager."""

    @decorator
    def require_auth(f, self = None, *args, **kw):
        """Decorator to check for auth before running a function.
        Assumes that the function is a member of this class.
        """

        if not self.sid:
            raise NotLoggedIn

        return f(self, *args, **kw)

    def __init__(self):
        self.sid = None
        self.android = httplib.HTTPSConnection("android.clients.google.com")


        self.mac = hex(getmac())[2:-1]
        self.mac = ':'.join([self.mac[x:x+2] for x in range(0, 10, 2)])

        self.hostname = gethostname()

        self.uauth = metadata_pb2.UploadAuth()
        self.uauth.address = self.mac
        self.uauth.hostname = self.hostname

        self.clientstate = metadata_pb2.ClientState()
        self.clientstate.address = self.mac

        #These get initialized after login.
        self.uauthresp = metadata_pb2.UploadAuthResponse()
        self.clientstateresp = metadata_pb2.ClientStateResponse()

    def login(self, email, password):
        payload = {
            'Email': email,
            'Passwd': password,
            'service': 'sj',
            'accountType': 'GOOGLE'
        }
        r = urllib.urlopen("https://google.com/accounts/ClientLogin", 
                            urllib.urlencode(payload)).read()

        first = r.split("\n")[0]

        #Bad auth will return Error=BadAuthentication\n

        if first.split("=")[0] == "SID":
            self.sid = first
            self.uauthresp.ParseFromString(self.protopost("upauth", self.uauth))
            self.clientstateresp.ParseFromString(self.protopost("clientstate", self.clientstate))
            return True
        else:
            return False

    @require_auth
    def get_quota(self):
        self.clientstateresp.ParseFromString(self.protopost("clientstate", self.clientstate))

        return self.clientstateresp.quota

    @require_auth
    def protopost(self, path, proto):
        """Returns the response from encoding and posting the given data.
        
        :param path: the name of the service url
        :param proto: data to be encoded with protobuff
        """

        self.android.request("POST", "/upsj/"+path, proto.SerializeToString(), {
            "Cookie": self.sid,
            "Content-Type": "application/x-google-protobuf"
        })
        r = self.android.getresponse()


        return r.read()

    @require_auth
    def upload(self, song_filenames):
        """Uploads the songs stored in the given filenames.
        Metadata will be read from id3 tags."""
        
        filemap = {} #this maps a generated ClientID with a filename

        metadata = metadata_pb2.MetadataRequest()
        metadata.address = self.mac        

        for filename in song_filenames:

            track = metadata.tracks.add()

            audio = MP3(filename, ID3 = EasyID3)

            chars = string.ascii_letters + string.digits 
            id = ''.join(random.choice(chars) for i in range(20))
            filemap[id] = filename
            track.id = id

            filesize = os.path.getsize(filename)

            track.fileSize = filesize

            track.bitrate = audio.info.bitrate / 1000
            track.duration = int(audio.info.length * 1000)
            if "album" in audio: track.album = audio["album"][0]

            if "title" in audio: track.title = audio["title"][0]
            if "artist" in audio: track.artist = audio["artist"][0]
            if "composer" in audio: track.composer = audio["composer"][0]
            #I can fix this...
            #if "albumartistsort" in audio: track.albumArtist = audio["albumartistsort"][0]
            if "genre" in audio: track.genre = audio["genre"][0]
            if "date" in audio: track.year = int(audio["date"][0])
            if "bpm" in audio: track.beatsPerMinute = int(audio["bpm"][0])

            if "tracknumber" in audio: 
                tracknumber = audio["tracknumber"][0].split("/")
                track.track = int(tracknumber[0])
                if len(tracknumber) == 2:
                    track.totalTracks = int(tracknumber[1])

            if "discnumber" in audio:
                discnumber = audio["discnumber"][0].split("/")
                track.disc = int(discnumber[0])
                if len(discnumber) == 2:
                    track.totalDiscs = int(discnumber[1])


        metadataresp = metadata_pb2.MetadataResponse()
        metadataresp.ParseFromString(self.protopost("metadata?version=1", metadata))

        jumper = httplib.HTTPConnection('uploadsj.clients.google.com')

        for song in metadataresp.response.uploads:
            filename = filemap[song.id]
            audio = MP3(filename, ID3 = EasyID3)
            print os.path.basename(filename)
            #if options.verbose: print song
            inlined = {
                "title": "jumper-uploader-title-42",
                "ClientId": song.id,
                "ClientTotalSongCount": len(metadataresp.response.uploads),
                "CurrentTotalUploadedCount": "0",
                "CurrentUploadingTrack": audio["title"][0],
                "ServerId": song.serverId,
                "SyncNow": "true",
                "TrackBitRate": audio.info.bitrate,
                "TrackDoNotRematch": "false",
                "UploaderId": self.mac
            }
            payload = {
              "clientId": "Jumper Uploader",
              "createSessionRequest": {
                "fields": [
                    {
                        "external": {
                      "filename": os.path.basename(filename),
                      "name": os.path.abspath(filename),
                      "put": {},
                      "size": os.path.getsize(filename)
                    }
                    }
                ]
              },
              "protocolVersion": "0.8"
            }
            for key in inlined:
                payload['createSessionRequest']['fields'].append({
                    "inlined": {
                        "content": str(inlined[key]),
                        "name": key
                    }
                })

            #print json.dumps(payload)

            while True:
                jumper.request("POST", "/uploadsj/rupio", json.dumps(payload), {
                    "Content-Type": "application/x-www-form-urlencoded", #wtf? shouldn't it be json? but that's what the google client sends
                    "Cookie": self.sid
                })
                r = json.loads(jumper.getresponse().read())
                #if options.verbose: print r
                if 'sessionStatus' in r: break
                time.sleep(3)
                print "Waiting for servers to sync..."

            up = r['sessionStatus']['externalFieldTransfers'][0]
            print "Uploading a file... this may take a while"
            jumper.request("POST", up['putInfo']['url'], open(filename), {
                'Content-Type': up['content_type']
            })
            r = json.loads(jumper.getresponse().read())
            #if options.verbose: print r
            if r['sessionStatus']['state'] == 'FINALIZED':
                print "Uploaded File Successfully"
