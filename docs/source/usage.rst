.. _usage:

Usage
=====

Installation
------------
Use `pip <http://www.pip-installer.org/en/latest/index.html>`__:
``pip install gmusicapi``.
This will grab all the source dependencies.
Don't use ``easy_install`` unless you really have to.

To upload anything other than mp3s, you're going to need
`Libav's avconv <http://libav.org/avconv.html>`__
installed and in your system path, along with at least libmp3lame.

 - Ubuntu/Debian users:
   ``sudo apt-get install libav-tools libavcodec-extra-53``.
 - Windows users, get `the most recent static binaries <http://win32.libav.org/releases/>`__
   and then `edit your path <http://www.computerhope.com/issues/ch000549.htm>`__
   to include the directory that contains avconv.exe.
   
If you need to install avconv from source, be sure to use
``./configure --enable-gpl --enable-nonfree --enable-libmp3lame``.

To check that everything is set up correctly, you can run the test
suite: ``python gmusicapi/test/run_tests.py``.
If something goes horribly wrong there's the chance you'll end up
with an extra test playlist or song in your library, but you 
should never lose anything.
If the tests fail, please
`open an issue <https://github.com/simon-weber/Unofficial-Google-Music-API/issues/new>`__
so the problem can be fixed.

Quickstart
----------

Generally, your code will start with:

.. code-block:: python

    from gmusicapi import Api

    api = Api()
    logged_in = api.login('user@gmail.com', 'my-password')
    # logged_in is True if login was successful

Note that 2-factor users will need to setup and provide an app-specific password.

If you're not going to be uploading music, use:

.. code-block:: python

    api.login('user@gmail.com', 'my-password', perform_upload_auth=False)

instead. This will prevent an upload device from being registered (which is good: you
only get 10 of these).

Next, check out `the provided example
<https://github.com/simon-weber/Unofficial-Google-Music-API/blob/master/example.py>`__.

If you're looking to do something a bit more wild, the reference section has
all the details:

.. toctree::
   :maxdepth: 2

   reference/api
   reference/metadata
   reference/protocol
