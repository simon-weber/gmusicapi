.. _api:
.. currentmodule:: gmusicapi.clients

Client Interfaces
=================

gmusicapi currently has three main interfaces:
one for the music.google.com webclient,
one for the Android App, and
one for the Music Manager. The big differences are:

* :py:class:`Webclient` development has mostly ceased, with the :py:class:`Mobileclient`
  superceding it. It is not tested nor well supported.
* :py:class:`Musicmanager` is used for uploading and downloading, while
  :py:class:`Mobileclient` supports everything but uploading.
* :py:class:`Webclient`/:py:class:`Mobileclient` require a plaintext email and password to login, while
  :py:class:`Musicmanager` uses `OAuth2
  <https://developers.google.com/accounts/docs/OAuth2#installed>`__.
* :py:class:`Mobileclient` supports streaming but requires that the Google Play Music app has been installed
  and run before use.

.. toctree::
   :maxdepth: 2

   webclient
   mobileclient
   musicmanager
