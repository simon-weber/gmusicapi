.. _api:
.. currentmodule:: gmusicapi.clients

Client Interfaces
=================

gmusicapi has two main interfaces: one for the music.google.com webclient, and
one for the Music Manager. The big differences are:

* :py:class:`Musicmanager` is used only for uploading, while :py:class:`Webclient`
  supports everything but uploading.
* :py:class:`Webclient` requires a plaintext email and password to login, while
  :py:class:`Musicmanager` uses `OAuth2
  <https://developers.google.com/accounts/docs/OAuth2#installed>`__.

.. toctree::
   :maxdepth: 2

   webclient
   musicmanager
