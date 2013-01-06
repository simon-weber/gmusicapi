#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Definitions shared by multiple clients."""

import json
import sys
import types

from google.protobuf.descriptor import FieldDescriptor
from requests import Request

from gmusicapi.exceptions import ParseException

#There's a lot of code here to simplify call definition, but it's not scary - promise.
#Request objects are currently requests.Request; see http://docs.python-requests.org


class BuildRequestMeta(type):
    """Metaclass to create build_request from static/dynamic config."""

    def __new__(cls, name, bases, dct):
        #Create _key methods on the class from combining static_key and dynamic_key.

        #To explain some of the funkiness wrt closures, see:
        # http://stackoverflow.com/questions/233673/lexical-closures-in-python

        config = {}  # stores key: val for static or f(*args, **kwargs) -> val for dyn
        dyn = lambda key: 'dynamic_' + key
        stat = lambda key: 'static_' + key

        merge_keys = ('headers', 'params')
        all_keys = ('method', 'url', 'files', 'data') + merge_keys

        for key in all_keys:
            if dyn(key) not in dct and stat(key) not in dct:
                continue  # this key will be ignored; requests will default it

            #use get on left since dyn might not be declared
            config[key] = dct.get(dyn(key)) or dct[stat(key)]

        for key in merge_keys:
            #merge case: dyn took precedence above, but stat also exists
            if dyn(key) in config and stat(key) in dct:
                def key_closure(stat_val=dct[stat(key)], dyn_func=dct[dyn(key)]):
                    def build_key(cls, *args, **kwargs):
                        dyn_val = dyn_func(cls, *args, **kwargs)

                        stat_val.update(dyn_val)
                        return stat_val
                    return build_key
                config[key] = classmethod(key_closure())

        #create the actual build_request method
        def req_closure(config=config):
            def build_request(cls, *args, **kwargs):
                req_kwargs = {}
                for key, val in config.items():
                    if isinstance(val, types.FunctionType):
                        val = val(cls, *args, **kwargs)
                    req_kwargs[key] = val

                return Request(**req_kwargs)
            return build_request

        dct['build_request'] = classmethod(req_closure())

        return super(BuildRequestMeta, cls).__new__(cls, name, bases, dct)


class Call(object):
    """
    The client Call interface is:

     req = SomeCall.build_request(some, params)
     req.prepare() # this is specific to requests.Request

     response_text = <send off the request somehow>

     try:
        res = SomeCall.process_response(response_text)
     except ParseException, ValidationException, CallFailure
        ...

     #res is python data, the call succeeded, and the response was formatted as expected


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


    Calls can also define filter_response - this takes the result of process_response and
     formats it to be logged. It's useful for taking out eg gross byte fields.

    Calls are organized semantically, so one endpoint might have multiple calls.
    """

    __metaclass__ = BuildRequestMeta

    send_xt = False
    send_clientlogin = False
    send_sso = False

    @classmethod
    def parse_response(cls, text):
        """Parses http text to data for call responses."""
        raise NotImplementedError

    @classmethod
    def filter_response(cls, msg):
        """Return a version of a parsed response appropriate for logging."""
        return msg  # default to identity

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
