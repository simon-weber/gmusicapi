.. _ports:

Support for Other Languages
===========================

Here are the ports I'm currently aware of:


-  C#:
   `Taylor Finnell <https://github.com/taylorfinnell/GoogleMusicAPI.NET>`__
-  Java: `Jens Villadsen <https://github.com/jkiddo/gmusic.api>`__
   and `Nick Martin <https://github.com/xnickmx/google-play-client>`__
-  PHP:
   `raydanhk <http://code.google.com/p/unofficial-google-music-api-php/>`__
-  Objective-C:
   `Gregory Wicks <https://github.com/gwicks/gmusicapi-objc>`__
-  Javascript: `My Google Music Turntable uploader
   <https://github.com/simon-weber/Google-Music-Turntable-Uploader>`__
   (not a full port, just an example)
-  Ruby: `Loic Nageleisen <https://github.com/lloeki/ruby-skyjam>`__

They're in various states of completion and maintenance because,
well, building a port is tough.

Alternatively, consider using `GMusicProxy <http://gmusicproxy.net/>`__ or copying its approach.

Building a Port
---------------

It's a good idea to get in touch if you're going to be working on a port;
I can point you to relevant code or otherwise clarify things. Some generally
helpful information follows.

There are basically two clients to Google Music: the webclient, which handles
library management and playback, and the Music Manager, which handles uploads.
Music Manager features are *much* more difficult to support - I'd highly
recommend you ignore them to get started.

Auth is the biggest barrier to getting started. I'm using a little-known trick
where I log into the Music Manager with clientlogin, then upgrade to full SSO
credentials with tokenauth. `This link
<http://nelenkov.blogspot.com/2012/11/sso-using-account-manager.html>`__ might
be helpful.

The :ref:`protocol docs <protocol>` are where you want to look for specific information.

Lastly, keep the license in mind, and, again, be sure to respect Google.
