.. _api:
.. currentmodule:: gmusicapi.clients

Client Interfaces
=================

gmusicapi currently has three main interfaces:
one for the music.google.com webclient, 
one for the Android App, and
one for the Music Manager. The big differences are:

* :py:class:`Webclient` development has ceased, and the :py:class:`Mobileclient`
  will take its place
* :py:class:`Musicmanager` is used only for uploading, while
  :py:class:`Webclient`/:py:class:`Mobileclient`
  support everything but uploading.
* :py:class:`Webclient`/:py:class:`Mobileclient` require a plaintext email and password to login, while
  :py:class:`Musicmanager` uses `OAuth2
  <https://developers.google.com/accounts/docs/OAuth2#installed>`__.

.. toctree::
   :maxdepth: 2

   webclient
   mobileclient
   musicmanager
