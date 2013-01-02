#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Definitions shared by multiple clients."""

from collections import namedtuple
import json
import sys

from google.protobuf.descriptor import FieldDescriptor
import requests

from gmusicapi.exceptions import ParseException
from gmusicapi.utils import utils


Transaction = namedtuple(
    'Transaction',
    [
        'request',  # requests.Request
        'verify_res_schema',  # f(parsed_res) -> throws ValidationException
        'verify_res_success',  # f(parsed_res) -> throws CallFailure
    ],
)


class Call(object):
    """Abstract class for an api call.
    These classes are never instantiated."""

    #http method to use
    method = utils.NotImplementedField

    #should the call be logged?
    gets_logged = True

    #send a xsrf token in the url params?
    send_xt = True

    #static request config options, (m) signals a merge will occur:
    static_config = {}
    #  url – URL to send.
    #  headers (m) – dictionary of headers to send.
    #  files – dictionary of {filename: fileobject} files to multipart upload.
    #  data – the body to attach the request.
    #          If a dictionary is provided, form-encoding will take place.
    #  params (m) – dictionary of URL parameters to append to the URL.
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
    def filter_response(cls, msg):
        """Return a version of a parsed response appropriate for logging."""
        return msg  # default to identity

    @classmethod
    def _request_factory(cls, dynamic_config):
        """Return a PreparedRequest by combining static and dynamic config.
        Dynamic config takes precendence."""

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

        get_items = lambda d, key: d.get(key, {}).items()

        for merge_key in ('headers', 'params'):
            config[merge_key] = dict(get_items(cls.static_config, merge_key) +
                                     get_items(dynamic_config, merge_key))

        req = requests.Request(**config)

        return req

    @staticmethod
    def parse_json(text):
        try:
            return json.loads(text)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ParseException(e.message), None, trace

    @staticmethod
    def filter_proto(msg, make_copy=True):
        """Filter all byte fields in the message and submessages."""
        filtered = msg
        if make_copy:
            filtered = msg.__class__()
            filtered.CopyFrom(msg)

        fields = filtered.ListFields()

        #eg of filtering a specific field
        #if any(fd.name == 'field_name' for fd, val in fields):
        #    filtered.field_name = '<name>'

        #Filter all byte fields.
        for field_name in (fd.name for fd, val in fields
                           if fd.type == FieldDescriptor.TYPE_BYTES):
            setattr(filtered, field_name, '<bytes>')

        #Filter submessages.
        for field in (val for fd, val in fields
                      if fd.type == FieldDescriptor.TYPE_MESSAGE):

            #protobuf repeated api is bad for reflection
            is_repeated = hasattr(field, '__len__')

            if not is_repeated:
                Call.filter_proto(field, make_copy=False)

            else:
                for i in range(len(field)):
                    #repeatedComposite does not allow setting
                    old_fields = [f for f in field]
                    del field[:]

                    field.extend([Call.filter_proto(f, make_copy=False)
                                  for f in old_fields])

        return filtered
