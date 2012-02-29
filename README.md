An unofficial Python API for Google Music. The project is not supported nor endorsed by Google.  

Official documentation is provided by Read the Docs: [documentation](http://readthedocs.org/docs/unofficial-google-music-api/en/latest).  

###Features

* Authentication:
    * web client
    * music manager

* Getting library information:
    * all song metadata
    * all user playlist titles and ids (not auto, yet)
    * songs from a specific playlist

* Song streaming, downloading, and uploading (mp3 only, currently).

* Playlist manipulation:
    * creation
    * name changing
    * song addition and removal
    * deletion

* Song manipulation:
    * metadata changing (to avoid surprises read protocol_info)
    * removal from library

* Searching for songs, artists, and albums.

###Usage
gmapi.api.Api is the user-facing interface.
To get started, see example.py. For other examples, see the testing code.

###Dependencies
The API has been tested on Python 2.7.1+ on linux.

Currently, the following third party modules are used:

* [decorator](http://pypi.python.org/pypi/decorator)

* [mutagen](http://code.google.com/p/mutagen)

* [protobuf](http://code.google.com/p/protobuf)

* [mechanize](http://wwwsearch.sourceforge.net/mechanize/)

These correspond to the following Ubuntu packages:
    
    python-decorator python-mutagen python-protobuf python-mechanize


###Notes
This is a work in progress, so debug logging is enabled by default.
All logging is done to gmapi.log in your working directory, and warnings and above are printed to the console.
Nothing authentication-related gets logged aside from "logged in" and "logged out" messages.


- - -
  
  
Feel free to email me or - better yet - open an issue for bugs, feature requests, or contributions.



Copyright (c) 2012 Simon Weber  
Licensed under the [GPLv3](http://www.gnu.org/licenses/gpl.txt).