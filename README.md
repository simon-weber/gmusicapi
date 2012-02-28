An unofficial Python API for Google Music. The project is not supported nor endorsed by Google.  

Official documentation is provided by Read the Docs: [documentation](http://readthedocs.org/docs/unofficial-google-music-api/en/latest).  

###Features

* authentication
    * web client
    * music manager

* loading:
    * all song metadata
    * all user playlist titles and ids (not auto, yet)
    * songs from a specific playlist

* searching:
    * songs
    * artists
    * albums

* playlist:
    * creation
    * name changing
    * song addition and removal
    * deletion

* song:
    * downloading - gets a link and download count (GM allows 2 downloads per file)
    * metadata changing (to avoid surprises read protocol_info)
    * uploading - mp3 only as of now (unlike Google's music manager, it will upload multiple copies of the same file if tags differ. Google's backend will actively reject duplicate uploads, however.)
    * streaming - gets a url that works without authentication
    * removal from library

###Usage
gmapi.api.Api is the user-facing interface, and its internal documentation is kept up to date.
To get started, see example.py.

###Notes
This is a work in progress, so debug logging is enabled by default.
All logging is done to gmapi.log in your working directory, and warnings and above are printed to the console.
Nothing authentication-related gets logged aside from "logged in" and "logged out" messages.


- - -
  
  
Feel free to email me or - better yet - open an issue for bugs, feature requests, or contributions.



Copyright (c) 2012 Simon Weber  
Licensed under the [GPLv3](http://www.gnu.org/licenses/gpl.txt).