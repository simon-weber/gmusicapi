#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Definitions shared by multiple clients."""

from collections import namedtuple
import json
import sys

import requests


Transaction = namedtuple(
    'Transaction',
    ['request',  # requests.Request
     'verify_res_schema',  # f(parsed_res) -> throws ValidationException
     'verify_res_success',  # f(parsed_res) -> throws CallFailure
    ],
)


class ParseException(Exception):
    """Thrown by parse_response on errors."""
    pass


class ValidationException(Exception):
    """Thrown by Transaction.verify_res_schema on errors."""
    pass


class Call(object):
    """Abstract class for an api call.
    These classes are never instantiated."""

    #should the call be logged?
    gets_logged = True

    #most calls send a xsrf token in the url params
    send_xt = True

    #static request config options can be defined in a call:
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
    def _request_factory(cls, dynamic_config):
        """Return a PreparedRequest by combining method with dynamic config."""

        #valid dynamic config:
        #  url – URL to send.
        #  headers – dictionary of headers to send.
        #  files – dictionary of {filename: fileobject} to multipart upload.
        #  data – the body to attach the request.
        #          If a dictionary is provided, form-encoding will take place.
        #  params – dictionary of URL parameters to append to the URL.
        #These probably won't be used:
        #  cookies – dictionary or CookieJar of cookies
        #  auth – Auth handler or (user, pass) tuple.
        #  hooks – dictionary of callback hooks, for internal usage.

        config = dynamic_config
        config['method'] = cls.method

        req = requests.Request(**config)

        return req

    @staticmethod
    def parse_json(text):
        try:
            return json.loads(text)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ParseException(e.message), None, trace
