.. _api:
.. currentmodule:: gmusicapi.clients

Client Interfaces
=================

gmusicapi currently has three main interfaces:
one for the music.google.com webclient, 
one for the Android App, and
one for the Music Manager. The big differences are:

* :py:class:`Webclient` development has mostly ceased, with the :py:class:`Mobileclient`
  superceding it.
* :py:class:`Musicmanager` is used only for uploading, while
  :py:class:`Webclient`/:py:class:`Mobileclient`
  support everything but uploading.
* :py:class:`Webclient`/:py:class:`Mobileclient` require a plaintext email and password to login, while
  :py:class:`Musicmanager` uses `OAuth2
  <https://developers.google.com/accounts/docs/OAuth2#installed>`__.
* :py:class:`Webclient` and :py:class:`Mobileclient` both support streaming, but
  :py:class:`Mobileclient` requires that the Google Music app has been installed
  and run before use.

.. toctree::
   :maxdepth: 2

   webclient
   mobileclient
   musicmanager
