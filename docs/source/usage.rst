.. _usage:
.. currentmodule:: gmusicapi.clients

Usage
=====

Installation
------------
Use `pip <http://www.pip-installer.org/en/latest/index.html>`__:
``$ pip install gmusicapi``.
This will grab all the source dependencies.
Avoid using ``easy_install``.

If you're upgrading from a date-versioned release (eg ``2013.03.04``),
do ``$ pip uninstall gmusicapi; pip install gmusicapi`` instead.

To upload anything other than mp3s, you're going to need
`Libav's avconv <http://libav.org/avconv.html>`__
installed and in your system path, along with at least libmp3lame.

 - Ubuntu/Debian users:
   ``$ sudo apt-get install libav-tools libavcodec-extra-53``.
 - Windows users, get `the most recent static binaries <http://win32.libav.org/releases/>`__
   and then `edit your path <http://www.computerhope.com/issues/ch000549.htm>`__
   to include the directory that contains avconv.exe.
   
If you need to install avconv from source, be sure to use
``$ ./configure --enable-gpl --enable-nonfree --enable-libmp3lame``.

To check that everything is set up correctly, you can run the test
suite: ``$ python -m gmusicapi.test.run_tests``.
If something goes horribly wrong there's the chance you'll end up
with an extra test playlist or song in your library, but you 
should never lose anything.
If the tests fail, please
`open an issue <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/new>`__
so the problem can be fixed.

Quickstart
----------

If you're not going to be uploading music, use the :py:class:`Webclient`.
This requires plaintext auth, so your code might look something like:

.. code-block:: python

    from gmusicapi import Webclient

    api = Webclient()
    logged_in = api.login('user@gmail.com', 'my-password')
    # logged_in is True if login was successful

Note that 2-factor users will need to setup and provide an app-specific password.

If you're going to upload Music, you want the :py:class:`Musicmanager`.
It uses `OAuth2
<https://developers.google.com/accounts/docs/OAuth2#installed>`__ and
does not require plaintext credentials.

Instead, you'll need to authorize your account *once* before logging in.
The easiest way is to follow the prompts from:

.. code-block:: python

    from gmusicapi import Musicmanager

    mm = Musicmanager()
    mm.perform_oauth()

If successful, this will save your credentials to disk.
Then, future runs will start with:

.. code-block:: python

    from gmusicapi import Musicmanager

    mm = Musicmanager()
    mm.login()

    # mm.upload('foo.mp3')
    # ...


If you need both library management and uploading, just create one of each
type of client.

The reference section has complete information on both clients:

.. toctree::
   :maxdepth: 2

   reference/api
