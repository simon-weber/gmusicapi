.. _usage:
.. currentmodule:: gmusicapi.clients

Usage
=====

Installation
------------
Use `pip <https://pip.pypa.io/en/stable/installing/>`__:
``$ pip install gmusicapi``.

To install the yet-to-be-released development version, use
``$ pip install git+https://github.com/simon-weber/gmusicapi.git@develop#egg=gmusicapi``.

If you're going to be uploading music,
you'll likely need
`avconv <http://libav.org/avconv.html>`__ or
`ffmpeg <http://ffmpeg.org/ffmpeg.html>`__
installed and in your system path, along with at least libmp3lame:
 - Linux

   - Use your distro's package manager:
     e.g ``$ sudo apt-get install libav-tools libavcodec-extra-53``
     (ffmpeg requires extra steps on
     `Debian <http://www.deb-multimedia.org>`__/`Ubuntu <https://launchpad.net/~jon-severinsson/+archive/ubuntu/ffmpeg/>`__).
   - Download pre-built binaries of
     `avconv <http://johnvansickle.com/libav/>`__ or `ffmpeg <http://johnvansickle.com/ffmpeg/>`__
     and `edit your path <http://www.troubleshooters.com/linux/prepostpath.htm>`__
     to include the directory that contains avconv/ffmpeg.

 - Mac

   - Use `Homebrew <http://brew.sh/>`__ to install
     `libav (avconv) <http://braumeister.org/formula/libav>`__ or
     `ffmpeg <http://braumeister.org/formula/ffmpeg>`__.

 - Windows

   - Download pre-built binaries of
     `avconv <http://win32.libav.org/releases/>`__ or `ffmpeg <http://ffmpeg.zeranoe.com/builds/>`__
     and `edit your path <http://www.computerhope.com/issues/ch000549.htm>`__
     to include the directory that contains avconv.exe/ffmpeg.exe.

 - Google App Engine

   - See `this thread <https://github.com/simon-weber/gmusicapi/issues/381#issue-116838059>`__ for instructions.

The only time avconv or ffmpeg is not required is when uploading mp3s without scan-and-match enabled.
   
If you need to install avconv/ffmpeg from source, be sure to use
``$ ./configure --enable-gpl --enable-nonfree --enable-libmp3lame``.

Quickstart
----------

There are two supported client classes based on different Google apis.

The :py:class:`Mobileclient` uses the Android app's apis to handle 
library management and playback.

The :py:class:`Musicmanager` uses the desktop Music Manager's apis to
handle uploading and downloading.

Both have similar command-line `OAuth2 <https://developers.google.com/accounts/docs/OAuth2#installed>`__
interfaces for logging in. For example:

.. code-block:: python

    from gmusicapi import Musicmanager

    mm = Musicmanager()
    mm.perform_oauth()

This only needs to be run once, and if successful will save a refresh token to disk.
Then, future runs can start with:

.. code-block:: python

    from gmusicapi import Musicmanager

    mm = Musicmanager()
    mm.login()  # currently named oauth_login for the Mobileclient


If you need both library management and uploading, just create 
multiple client instances.

There is also the :py:class:`Webclient`, which is uses the webapp's
apis to handle similar tasks to the Mobileclient.
It is not tested nor well supported, and requires providing full account credentials
to use. Avoid it if possible.

The reference section has complete information on all clients:

.. toctree::
   :maxdepth: 2

   reference/api
