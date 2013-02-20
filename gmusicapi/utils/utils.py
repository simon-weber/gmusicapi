#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility functions used across api code."""

import logging
import subprocess

from decorator import decorator
from google.protobuf.descriptor import FieldDescriptor

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

#set to True after configure_debug_logging is called to prevent
# setting up more than once
log_already_configured_flag = '_gmusicapi_debug_logging_setup'


def configure_debug_logging():
    """Warnings and above to terminal, below to gmusicapi.log.
    Output includes line number."""

    root_logger = logging.getLogger('gmusicapi')

    if not getattr(root_logger, log_already_configured_flag, None):
        root_logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(log_filename)
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)

        root_logger.addHandler(fh)
        root_logger.addHandler(ch)

        #print out startup message without verbose formatting
        root_logger.info("!-- begin debug log --!")
        root_logger.info("version: " + __version__)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s (%(lineno)s) [%(levelname)s]: %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        setattr(root_logger, log_already_configured_flag, True)


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


def transcode_to_mp3(audio_in, quality=3, slice_start=None, slice_duration=None):
    """Return the bytestring result of transcoding audio_in to mp3.
    An ID3 header is not included in the result.

    :param audio_in: bytestring of input
    :param quality: if int, pass to avconv -qscale. if string, pass to avconv -ab
                    -qscale roughly corresponds to libmp3lame -V0, -V1...
    :param slice_start: (optional) transcode a slice, starting at this many seconds
    :param slice_duration: (optional) when used with slice_start, the number of seconds in the slice

    Raise OSError on transcoding problems, or ValueError on param problems.
    """

    #TODO IOError makes more sense than OSError

    err_output = None
    cmd = ['avconv', '-i', 'pipe:0']

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
                                stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        audio_out, err_output = proc.communicate(input=audio_in)

        if proc.returncode != 0:
            raise OSError  # handle errors in except

    except (OSError, IOError) as e:
        log.exception('transcoding failure')

        err_msg = "transcoding failed: %s. " % e

        if err_output is not None:
            err_msg += "stderr: '%s'" % err_output

        log.debug('full failure output: %s', err_output)

        raise OSError(err_msg)

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
