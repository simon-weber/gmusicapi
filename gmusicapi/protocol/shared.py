"""Definitions shared by multiple clients."""

from collections import namedtuple
import json
import sys

import requests


Transaction = namedtuple(
    'Transaction',
    ['request',  # contains all http info to make the call
     'verify_res_schema',  # f(parsed_res) -> bool. checks response schema
     'verify_res_success',  # like verify schema, but checks for soft failure
    ],
)


class ParseException(Exception):
    """Thrown by parse_response on errors."""
    pass


class Call(object):
    """Abstract class for an api call.
    These classes are never instantiated."""

    #should the call be logged?
    gets_logged = True

    #static request options can be defined in a call:
    #  method – HTTP method to use.
    #  url – URL to send.
    #  headers – dictionary of headers to send.
    #  files – dictionary of {filename: fileobject} files to multipart upload.
    #  data – the body to attach the request.
    #          If a dictionary is provided, form-encoding will take place.
    #  params – dictionary of URL parameters to append to the URL.
    #These probably won't be used:
    #  cookies – dictionary or CookieJar of cookies to attach to this request.
    #  auth – Auth handler or (user, pass) tuple.
    #  hooks – dictionary of callback hooks, for internal usage.

    @classmethod
    def build_transaction(cls, *args, **kwargs):
        """Given call-specific args, return a Transaction."""
        raise NotImplementedError

    @classmethod
    def parse_response(cls, text):
        """Parses http text to data for call responses."""
        raise NotImplementedError

    @classmethod
    def _build_request(cls, **kwargs):
        """Return a PreparedRequest by combining given dynamic config with the
        static config."""

        config = {key: kwargs.get(key, getattr(cls)) for key in
                  ('method', 'url', 'headers', 'files', 'data', 'params')}

        req = requests.Request(**config)
        req.prepare()

        return req

    @classmethod
    def parse_json(cls, text):
        try:
            return json.loads(text)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ParseException(e.message), None, trace
