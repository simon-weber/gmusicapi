#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility functions used across api code."""

import functools
import json
import logging
import subprocess
import time

from decorator import decorator
from google.protobuf.descriptor import FieldDescriptor
from oauth2client.client import OAuth2Credentials

from gmusicapi import __version__

log = logging.getLogger(__name__)

#Map descriptor.CPPTYPE -> python type.
_python_to_cpp_types = {
    long: ('int32', 'int64', 'uint32', 'uint64'),
    float: ('double', 'float'),
    bool: ('bool',),
    str: ('string',),
}

cpp_type_to_python = dict(
    (getattr(FieldDescriptor, 'CPPTYPE_' + cpp.upper()), python)
    for (python, cpplist) in _python_to_cpp_types.items()
    for cpp in cpplist
)

root_logger_name = "gmusicapi"
log_filename = "gmusicapi.log"


def credentials_from_refresh_token(token):
    # why doesn't Google provide this!?

    # too lazy to break circular dependency
    from gmusicapi.protocol import musicmanager

    cred_json = {"_module": "oauth2client.client",
                 "token_expiry": "2000-01-01T00:13:37Z",  # to refresh now
                 "access_token": 'bogus',
                 "token_uri": "https://accounts.google.com/o/oauth2/token",
                 "invalid": False,
                 "token_response": {
                     "access_token": 'bogus',
                     "token_type": "Bearer",
                     "expires_in": 3600,
                     "refresh_token": token},
                 "client_id": musicmanager.oauth.client_id,
                 "id_token": None,
                 "client_secret": musicmanager.oauth.client_secret,
                 "revoke_uri": "https://accounts.google.com/o/oauth2/revoke",
                 "_class": "OAuth2Credentials",
                 "refresh_token": token,
                 "user_agent": None}

    return OAuth2Credentials.new_from_json(json.dumps(cred_json))


def dual_decorator(func):
    """This is a decorator that converts a paramaterized decorator for no-param use.

    source: http://stackoverflow.com/questions/3888158.
    """
    @functools.wraps(func)
    def inner(*args, **kw):
        if ((len(args) == 1 and not kw and callable(args[0])
             and not (type(args[0]) == type and issubclass(args[0], BaseException)))):
            return func()(args[0])
        else:
            return func(*args, **kw)
    return inner


def configure_debug_log_handlers(logger):
    """Warnings and above to terminal, below to gmusicapi.log.
    Output includes line number."""

    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_filename)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    logger.addHandler(fh)
    logger.addHandler(ch)

    #print out startup message without verbose formatting
    logger.info("!-- begin debug log --!")
    logger.info("version: " + __version__)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s (%(lineno)s) [%(levelname)s]: %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)


@dual_decorator
def retry(retry_exception=None, tries=5, delay=2, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    An exception from a final attempt will propogate.

    :param retry_exception: exception (or tuple of exceptions) to check for and retry on.
      If None, use AssertionError.
    :param tries: number of times to try (not retry) before giving up
    :param delay: initial delay between retries in seconds
    :param backoff: backoff multiplier
    :param logger: logger to use. If None, use 'gmusicapi.utils' logger

    Modified from
    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python.
    """

    if logger is None:
        logger = logging.getLogger('gmusicapi.utils')

    if retry_exception is None:
        retry_exception = AssertionError

    @decorator
    def retry_wrapper(f, *args, **kwargs):
        mtries, mdelay = tries, delay  # make our own mutable copies
        while mtries > 1:
            try:
                return f(*args, **kwargs)
            except retry_exception as e:
                logger.info("%s, retrying in %s seconds...", e, mdelay)

                time.sleep(mdelay)
                mtries -= 1
                mdelay *= backoff
        return f(*args, **kwargs)

    return retry_wrapper


def pb_set(msg, field_name, val):
    """Return True and set val to field_name in msg if the assignment
    is type-compatible, else return False.

    val will be coerced to a proper type if needed.

    :param msg: an instance of a protobuf.message
    :param field_name:
    :param val
    """

    #Find the proper type.
    field_desc = msg.DESCRIPTOR.fields_by_name[field_name]
    proper_type = cpp_type_to_python[field_desc.cpp_type]

    #Try with the given type first.
    #Their set hooks will automatically coerce.
    try_types = (type(val), proper_type)

    for t in try_types:
        log.debug("attempt %s.%s = %s(%r)", msg.__class__.__name__, field_name, t, val)
        try:
            setattr(msg, field_name, t(val))
            log.debug("! success")
            break
        except (TypeError, ValueError):
            log.debug("X failure")
    else:
        return False  # no assignments stuck

    return True


def transcode_to_mp3(filepath, quality=3, slice_start=None, slice_duration=None):
    """Return the bytestring result of transcoding the file at *filepath* to mp3.
    An ID3 header is not included in the result.

    :param filepath: location of file
    :param quality: if int, pass to avconv -qscale. if string, pass to avconv -ab
                    -qscale roughly corresponds to libmp3lame -V0, -V1...
    :param slice_start: (optional) transcode a slice, starting at this many seconds
    :param slice_duration: (optional) when used with slice_start, the number of seconds in the slice

    Raise IOError on transcoding problems, or ValueError on param problems.
    """

    err_output = None
    cmd = ['avconv', '-i', filepath]

    if slice_duration is not None:
        cmd.extend(['-t', str(slice_duration)])
    if slice_start is not None:
        cmd.extend(['-ss', str(slice_start)])

    if isinstance(quality, int):
        cmd.extend(['-qscale', str(quality)])
    elif isinstance(quality, basestring):
        cmd.extend(['-ab', quality])
    else:
        raise ValueError("quality must be int or string, but received %r" % quality)

    cmd.extend(['-f', 's16le',  # don't output id3 headers
                '-c', 'libmp3lame',
                'pipe:1'])

    log.debug('running transcode command %r', cmd)

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        audio_out, err_output = proc.communicate()

        if proc.returncode != 0:
            err_output = ("(return code: %r)\n" % proc.returncode) + err_output
            raise IOError  # handle errors in except

    except (OSError, IOError) as e:
        log.exception('transcoding failure')

        err_msg = "transcoding failed: %s. " % e

        if err_output is not None:
            err_msg += "stderr: '%s'" % err_output

        log.debug('full failure output: %s', err_output)

        raise IOError(err_msg)

    else:
        return audio_out


def truncate(x, max_els=100, recurse_levels=0):
    """Return a 'shorter' truncated x of the same type, useful for logging.
    recurse_levels is only valid for homogeneous lists/tuples.
    max_els ignored for song dictionaries."""

    #Coerce tuple to list to ease truncation.
    is_tuple = False
    if isinstance(x, tuple):
        is_tuple = True
        x = list(x)

    try:
        if len(x) > max_els:
            if isinstance(x, basestring):
                return x[:max_els] + '...'

            if isinstance(x, dict):
                if 'id' in x and 'titleNorm' in x:
                    #assume to be a song dict
                    trunc = dict((k, x.get(k)) for k in ['title', 'artist', 'album'])
                    trunc['...'] = '...'
                    return trunc
                else:
                    return dict(x.items()[:max_els] + [('...', '...')])

            if isinstance(x, list):
                trunc = x[:max_els] + ['...']
                if recurse_levels > 0:
                    trunc = [truncate(e, recurse_levels - 1) for e in trunc[:-1]]
                if is_tuple:
                    trunc = tuple(trunc)
                return trunc

    except TypeError:
        #does not have len
        pass

    return x


def empty_arg_shortcircuit(return_code='[]', position=1):
    """Decorate a function to shortcircuit and return something immediately if
    the length of a positional arg is 0.

    :param return_code: (optional) code to exec as the return value - default is a list.
    :param position: (optional) the position of the expected list - default is 1.
    """

    #The normal pattern when making a collection an optional arg is to use
    # a sentinel (like None). Otherwise, you run the risk of the collection
    # being mutated - there's only one, not a new one on each call.
    #Here we've got multiple things we'd like to
    # return, so we can't do that. Rather than make some kind of enum for
    # 'accepted return values' I'm just allowing freedom to return anything.
    #Less safe? Yes. More convenient? Definitely.

    @decorator
    def wrapper(function, *args, **kw):
        if len(args[position]) == 0:
            #avoid polluting our namespace
            ns = {}
            exec 'retval = ' + return_code in ns
            return ns['retval']
        else:
            return function(*args, **kw)

    return wrapper


def accept_singleton(expected_type, position=1):
    """Allows a function expecting a list to accept a single item as well.
    The item will be wrapped in a list.
    Will not work for nested lists.

    :param expected_type: the type of the items in the list
    :param position: (optional) the position of the expected list - defaults to 1.
    """

    @decorator
    def wrapper(function, *args, **kw):

        if isinstance(args[position], expected_type):
            #args are a tuple, can't assign into them
            args = list(args)
            args[position] = [args[position]]
            args = tuple(args)

        return function(*args, **kw)

    return wrapper


#Used to mark a field as unimplemented.
@property
def NotImplementedField(self):
    raise NotImplementedError
