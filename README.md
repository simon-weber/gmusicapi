A Python API for Google Music.


###Features

* authentication
    * web client
    * music manager

* loading:
    * all song metadata
    * all user playlists (not auto, yet)

* searching:
    * songs
    * artists
    * albums

* playlist:
    * creation
    * name changing
    * song addition (not removal, yet)
    * deletion

* song:
    * downloading - gets a link and download count (GM allows 2 downloads per file)
    * metadata changing (to avoid surprises read protocol_info)
    * ~~ uploading (only MP3 files for now - big thanks to [Kevin](https://github.com/antimatter15) for his awesome work on the music manager protocol)~~ (upload support temporarily pulled while deduplication matters are figured out.)
    
    * removal from library

###Usage
gmapi.api.Api is the user-facing interface.
To get started, see example.py.  

There's not official documentation yet, but the internal docs are kept up-to-date. Just use help(gmapi.api) in an interpreter.

###Notes
This is a work in progress, so debug logging is enabled by default.
All logging is done to gmapi.log, and warnings and above are printed to	the console.
I don't	    log anything authentication-related - you can check the  logs to	be sure.



- - -
  
  
Feel free to contact me	with anything relating to the project. Bug reports, feature requests, and contributions are welcome.



Copyright (c) 2012 Simon Weber
Licensed under the [GPLv3](http://www.gnu.org/licenses/gpl.txt).