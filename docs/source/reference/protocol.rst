.. _protocol:

.. currentmodule:: gmusicapi.protocol

Protocol Details
================

The following definitions represent known endpoints relating to Google Music.
They are organized by the client that uses them.

The names of these classes are semantic, and may not match their actual endpoint.

Client code will generally use ``api.Api._make_call`` and provide the parameters that
``dynamic_data`` requires. This can be used to make arbitrary low-level calls
to Google Music endpoints.

It's tough to generate the exact schema of every call in a readable fashion,
so this information is left out.
If you need exact specifications, look at `the code
<https://github.com/simon-weber/Unofficial-Google-Music-API/tree/develop/gmusicapi/protocol>`__
- or submit a pull request to generate the docs =)

Web Client
----------

.. automodule:: gmusicapi.protocol.webclient
   :members:
   :undoc-members:
   :exclude-members: WcCall, build_request, filter_response, validate, expected_response


Music Manager
-------------

.. automodule:: gmusicapi.protocol.musicmanager
   :members:
   :undoc-members:
   :exclude-members: MmCall, build_request, filter_response, validate, send_xt
