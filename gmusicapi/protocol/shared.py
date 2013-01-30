#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Definitions shared by multiple clients."""

import json
import sys

from google.protobuf.descriptor import FieldDescriptor
from requests import Request

from gmusicapi.exceptions import ParseException

#There's a lot of code here to simplify call definition, but it's not scary - promise.
#Request objects are currently requests.Request; see http://docs.python-requests.org


class BuildRequestMeta(type):
    """Metaclass to create build_request from static/dynamic config."""

    def __new__(cls, name, bases, dct):
        #To not mess with mro and inheritance, build the class first.
        new_cls = super(BuildRequestMeta, cls).__new__(cls, name, bases, dct)

        merge_keys = ('headers', 'params')
        all_keys = ('method', 'url', 'files', 'data') + merge_keys

        config = {}  # stores key: val for static or f(*args, **kwargs) -> val for dyn
        dyn = lambda key: 'dynamic_' + key
        stat = lambda key: 'static_' + key
        has_key = lambda key: hasattr(new_cls, key)
        get_key = lambda key: getattr(new_cls, key)

        for key in all_keys:
            if not has_key(dyn(key)) and not has_key(stat(key)):
                continue  # this key will be ignored; requests will default it

            if has_key(dyn(key)):
                config[key] = get_key(dyn(key))
            else:
                config[key] = get_key(stat(key))

        for key in merge_keys:
            #merge case: dyn took precedence above, but stat also exists
            if dyn(key) in config and has_key(stat(key)):
                def key_closure(stat_val=get_key(stat(key)), dyn_func=get_key(dyn(key))):
                    def build_key(*args, **kwargs):
                        dyn_val = dyn_func(*args, **kwargs)

                        stat_val.update(dyn_val)
                        return stat_val
                    return build_key
                config[key] = key_closure()

        #To explain some of the funkiness wrt closures, see:
        # http://stackoverflow.com/questions/233673/lexical-closures-in-python

        #create the actual build_request method
        def req_closure(config=config):
            def build_request(cls, *args, **kwargs):
                req_kwargs = {}
                for key, val in config.items():
                    if hasattr(val, '__call__'):
                        val = val(*args, **kwargs)

                    req_kwargs[key] = val

                return Request(**req_kwargs)
            return build_request

        new_cls.build_request = classmethod(req_closure())

        return new_cls


class Call(object):
    """
    The client Call interface is:

     req = SomeCall.build_request(some, params)
     prep_req = req.prepare()
     response = <requests.Session.send(prep_req)>

     try:
         msg = SomeCall.parse_response(response)
     except ParseException
         ...

     try:
         SomeCall.validate(msg)
         SomeCall.check_success(msg)
     except ValidationException:
         ...
     except CallFailure:
         ...

     #msg is python data, the call succeeded, and the response was formatted as expected


    Calls define how to build their requests through static and dynamic data.
    For example, a request might always send some user-agent: this is static.
    Or, it might need the name of a song to modify: this is dynamic.

    Possible values to use in the request are:
        method: eg 'GET' or 'POST'
        url: string
        headers (m): dictionary
        files: dictionary of {filename: fileobject} files to multipart upload.
        data: the body of the request
                If a dictionary is provided, form-encoding will take place.
                A string will be sent as-is.
        params (m): dictionary of URL parameters to append to the URL.

    Calls can define them statically:
        class SomeCall(Call):
            static_url = 'http://foo.com/thiscall'

    Or dynamically:
        class SomeCall(Call):
            #this takes whatever params are needed (ie not necessarily something called endpoint)
            #*args, **kwargs are passed from SomeCall.build_request
            def dynamic_url(endpoint):
                return 'http://foo.com/' + endpoint

    Dynamic data takes precedence over static if both exist,
     except for attributes marked with (m) above. These get merged, with dynamic overriding
     on key conflicts (though this really shouldn't be relied on).
    Here's an example that has static and dynamic headers:
        class SomeCall(Call):
            static_headers = {'user-agent': "I'm totally a Google client!"}

            @classmethod
            def dynamic_headers(cls, keep_alive=False):
                return {'Connection': keep_alive}

    If neither is defined, the param is not passed to the Request when creating it.


    There's three static bool fields to declare what auth the session should send:
        send_xt: param/cookie xsrf token

     AND/OR

        send_clientlogin: google clientlogin cookies
     OR
        send_sso: google SSO (authtoken) cookies

    session_options can also be set to a dict of kwargs to pass to requests.Session.send.

    Calls must define parse_response.
    Calls can also define filter_response, validate and check_success.

    Calls are organized semantically, so one endpoint might have multiple calls.
    """

    __metaclass__ = BuildRequestMeta

    send_xt = False
    send_clientlogin = False
    send_sso = False
    session_options = {}

    @classmethod
    def parse_response(cls, response):
        """Parses a requests.Response to data."""
        raise NotImplementedError

    @classmethod
    def validate(cls, msg):
        pass

    @classmethod
    def check_success(cls, msg):
        pass

    @classmethod
    def filter_response(cls, msg):
        """Return a version of a parsed response appropriate for logging."""
        return msg  # default to identity

    @classmethod
    def get_auth(cls):
        """Return a 3-tuple send (xt, clientlogin, sso)."""
        return (cls.send_xt, cls.send_clientlogin, cls.send_sso)

    @staticmethod
    def _parse_json(text):
        try:
            return json.loads(text)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ParseException(str(e)), None, trace

    @staticmethod
    def _filter_proto(msg, make_copy=True):
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
        for field_name, val in ((fd.name, val) for fd, val in fields
                                if fd.type == FieldDescriptor.TYPE_BYTES):
            setattr(filtered, field_name, "<%s bytes>" % len(val))

        #Filter submessages.
        for field in (val for fd, val in fields
                      if fd.type == FieldDescriptor.TYPE_MESSAGE):

            #protobuf repeated api is bad for reflection
            is_repeated = hasattr(field, '__len__')

            if not is_repeated:
                Call._filter_proto(field, make_copy=False)

            else:
                for i in range(len(field)):
                    #repeatedComposite does not allow setting
                    old_fields = [f for f in field]
                    del field[:]

                    field.extend([Call._filter_proto(f, make_copy=False)
                                  for f in old_fields])

        return filtered
