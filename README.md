#gmusicapi: an unofficial Python API for Google Play Music

The project is not supported nor endorsed by Google. I'll be interning for Google this summer, so to avoid conflicts of interest I'll stop contributing sometime in May. Get in touch if you're interested in taking over maintenance.

**Respect Google in your use of the API**. Use common sense (protocol compliance, reasonable load, etc) and don't ruin the fun for everyone else.

For those looking to use the api, see the installation and usage sections below. Documentation is hosted at Read the Docs: [documentation](http://readthedocs.org/docs/unofficial-google-music-api/en/latest).

For those looking to port or contribute, see the porting section below. There's also a code overview on the wiki: [wiki](https://github.com/simon-weber/Unofficial-Google-Music-API/wiki/Codebase-Overview).

For bugs reports, feature requests, and contributions, go ahead and [open an issue](https://github.com/simon-weber/Unofficial-Google-Music-API/issues/new).

##Features

**New in version 2012.04.03:** 

* full Windows support and a Windows installer
* upload support for all Google-support file formats
* faster retrieval of playlists
* better example code
   
There were also numerous breaking changes needed to improve the Api interface. See the changelog and documentation for details.

**Feature Overview:**

* Getting library information:
    * all song metadata
    * all user playlist titles and ids
    * songs from a specific playlist

* Song streaming and downloading

* Song uploading of all Google-supported file formats (mp3, unprotected m4a, ogg, flac, wma)

* Playlist manipulation:
    * creation
    * name modification
    * song deletion, addition, and reordering

* Song manipulation:
    * metadata modification (be sure to read protocol_info)
    * removal from library

* Searching for songs, artists, and albums.

**What's on the way:**

* integration with the Android service api, thanks to [Darryl Pogue](https://github.com/dpogue/Unofficial-Google-Music-API)
* more user-friendly abstractions

##Usage

The API has been tested on Python 2.7.2 on Linux and Windows.

###Installation

Linux users: use `pip install gmusicapi` to get the most recent version and dependencies.

Windows users: there is an [installation binary on PyPI](http://pypi.python.org/pypi/gmusicapi/).

To upload filetypes other than mp3, you're going to need FFmpeg installed and in your system path. For Ubuntu users: `sudo apt-get install ffmpeg ubuntu-restricted-extras`. Windows users, get [the most recent static binaries](http://ffmpeg.zeranoe.com/builds/) and then [edit your path](http://www.computerhope.com/issues/ch000549.htm) to include the directory that contains ffmpeg.exe.

To check that everything is set up correctly, you can run the test suite: `python -m gmusicapi.test.integration_test_api`. If something goes wrong during testing, there is the chance that you'll end up with an extra playlist or test song in your library, but it should never destructively modify your library. If there is an error during testing, please [open an issue](https://github.com/simon-weber/Unofficial-Google-Music-API/issues/new) to let me know about it. You should also submit your gmusicapi.log.

###Getting Started

gmusicapi.api.Api is the user-facing interface. The provided example.py should be enough to get you started. For more information, see the [documentation](http://readthedocs.org/docs/unofficial-google-music-api/en/latest) and testing code. 

In addition, Michal Odnous has built [an example](https://github.com/odiroot/Unofficial-Google-Music-API/blob/mo-sandbox/example_play.py) that will play songs from your library.

##Ports

Here are the ports I'm currently aware of:

* C#: [Taylor Finnell](https://github.com/Byteopia/GoogleMusicAPI.NET)
* Java: [Jens Villadsen](https://github.com/jkiddo/gmusic.api)


###Porting Information for Developers

Get in touch if you're working on a port. Even if I can't contribute, I might know people who'd like to.

The current implementation uses the same interface that a web browser does, and a code overview can be found [on the wiki](https://github.com/simon-weber/Unofficial-Google-Music-API/wiki/Codebase-Overview). Darryl Pogue is working on a more durable implementation by emulating Google's Android app. His work is [here](https://github.com/dpogue/Unofficial-Google-Music-API), and may easier to port. More information this alternative protocol is [here](https://github.com/dpogue/Unofficial-Google-Music-API/wiki/Skyjam-API).

Either way, you'll probably want to ignore anything related to Music Manager; that's just for uploading. If uploading interests you, more information is [here](https://github.com/simon-weber/google-music-protocol).

Lastly, keep the license in mind, and, again, be sure to respect Google.



##Notes

Debug logging is enabled by default.
All logging is done to gmusicapi.log in your working directory, with warnings and above printed to the console.
Nothing related to authenticated gets logged aside from "logged in" and "logged out" messages.


- - -
  

Copyright 2012 [Simon Weber](http://www.simonmweber.com).  
Licensed under the 3-clause BSD. See COPYING.
