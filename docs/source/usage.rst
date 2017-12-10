.. _usage:
.. currentmodule:: gmusicapi.clients

Usage
=====

Installation
------------
Use `pip <https://pip.pypa.io/en/stable/installing/>`__:
``$ pip install gmusicapi``.
This will grab all the source dependencies.
Avoid using ``easy_install``.

If you're upgrading from a date-versioned release (eg ``2013.03.04``),
do ``$ pip uninstall gmusicapi; pip install gmusicapi`` instead.

If you're going to be uploading music,
you'll likely need
`avconv <http://libav.org/avconv.html>`__ or
`ffmpeg <http://ffmpeg.org/ffmpeg.html>`__
installed and in your system path, along with at least libmp3lame.

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

If you're not going to be uploading music, you'll likely
want to use the :py:class:`Mobileclient`: it supports streaming
and library management.
It requires plaintext auth, so your code might look something like:

.. code-block:: python

    from gmusicapi import Mobileclient

    api = Mobileclient()
    logged_in = api.login('user@gmail.com', 'my-password', Mobileclient.FROM_MAC_ADDRESS)
    # logged_in is True if login was successful

Note that 2-factor users will need to setup and provide an app-specific password.

If you're going to upload Music, you want the :py:class:`Musicmanager`.
It uses `OAuth2
<https://developers.google.com/accounts/docs/OAuth2#installed>`__ and
does not require plaintext credentials.

Instead, you'll need to authorize your account *once* before logging in.
The easiest way is to run:

.. code-block:: python

    from gmusicapi import Musicmanager

    mm = Musicmanager()
    mm.perform_oauth()

If successful, this will save your credentials to disk.
Then, future runs can start with:

.. code-block:: python

    from gmusicapi import Musicmanager

    mm = Musicmanager()
    mm.login()

    # mm.upload('foo.mp3')
    # ...


If you need both library management and uploading, just create 
multiple client instances.

There is also the :py:class:`Webclient`, which is a mostly-deprecated
interface. It is not tested nor well supported. Use :class:`Mobileclient`
or :class:`Musicmanager` if possible.

The reference section has complete information on all clients:

.. toctree::
   :maxdepth: 2

   reference/api
