.. _ports:

Support for Other Languages
===========================

Here are the ports I'm currently aware of:


-  C++: `Greg Wicks <https://github.com/gwicks/gmusicapi-curl>`__
-  C#:
   `Taylor Finnell <https://github.com/taylorfinnell/GoogleMusicAPI.NET>`__
-  Java: `Jens Villadsen <https://github.com/jkiddo/gmusic.api>`__
   and `Nick Martin <https://github.com/xnickmx/google-play-client>`__
-  PHP:
   `raydanhk <http://code.google.com/p/unofficial-google-music-api-php/>`__
-  Objective-C:
   `Gregory Wicks <https://github.com/gwicks/gmusicapi-objc>`__
-  Javascript:
   `Lari Rasku <https://code.google.com/p/google-musicmanager-js/>`__.
   There's also my `Google Music Turntable uploader
   <https://github.com/simon-weber/Google-Music-Turntable-Uploader>`__;
   it's not a port, but may be useful as an example.
-  Node: `Jamon Terrell <https://github.com/jamon/playmusic>`__
-  Ruby: `Loic Nageleisen <https://github.com/lloeki/ruby-skyjam>`__

They're in various states of completion and maintenance because,
well, building a port is tough.

Alternatively, consider using `GMusicProxy <http://gmusicproxy.net/>`__ or copying its approach.

Building a Port
---------------

Get in touch if you're working on a port.
I'm happy to answer questions and point you to relevant bits of code.

Generally, though, the `protocol package
<https://github.com/simon-weber/Unofficial-Google-Music-API/tree/develop/gmusicapi/protocol>`__
is what you'll want to look at.
It contains all of the call schemas in a psuedo-dsl that's explained
`here
<https://github.com/simon-weber/Unofficial-Google-Music-API/blob/develop/gmusicapi/protocol/shared.py>`__.
