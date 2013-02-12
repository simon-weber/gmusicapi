#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility functions used across api code."""

from htmlentitydefs import name2codepoint
import re
import subprocess

import chardet
from decorator import decorator
import mutagen
from google.protobuf.descriptor import FieldDescriptor

from apilogging import LogController
log = LogController.get_logger("utils")

#Map descriptor.CPPTYPE -> python type.
_python_to_cpp_types = {
    long: ('int32', 'int64', 'uint32', 'uint64'),
    float: ('double', 'float'),
    bool: ('bool',),
    str: ('string',),
}

cpp_type_to_python = {
    getattr(FieldDescriptor, 'CPPTYPE_' + cpp.upper()): python
    for python, cpplist in _python_to_cpp_types.items()
    for cpp in cpplist
}


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

    cmd.extend(['-f', 's16be',  # don't output id3 headers
                '-c', 'libmp3lame',
                'pipe:1'])

    #TODO might be good to log the final command

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        audio_out, err_output = proc.communicate(input=audio_in)

        if proc.returncode != 0:
            raise OSError  # handle errors in except

    except OSError as e:
        #TODO would be better to log.exception here
        err_msg = "transcoding failed: %s. " % e

        if err_output is not None:
            err_msg += "stderr: '%s'" % err_output

        raise OSError(err_msg)

    else:
        return audio_out


def truncate(x, max_els=100, recurse_levels=0):
    """Return a 'shorter' truncated x of the same type.
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
                    trunc = {k: x.get(k) for k in ['title', 'artist', 'album']}
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


def guess_str_encoding(s):
    """Return a tuple (guessed encoding, confidence)."""

    res = chardet.detect(s)
    return (res['encoding'], res['confidence'])

def guess_file_encoding(filename):
    with open(filename) as f:
        return guess_str_encoding(f.read())

def copy_md_tags(from_fname, to_fname):
    """Copy all metadata from *from_fname* to *to_fname* and write.

    Return True on success, False if not all keys were copied/saved."""

    from_tags = mutagen.File(from_fname, easy=True)
    to_tags = mutagen.File(to_fname, easy=True)

    if from_tags is None or to_tags is None:
        log.debug("couldn't find an appropriate handler for tag files: '%s' '%s'", from_fname, to_fname)
        return False


    success = True

    for k,v in from_tags.iteritems():
        try:
            #Some tags don't store values in strings, but in special container types.
            #Those should be converted to strings so we can safely save them.
            #Also, the value might be a list of tags or a single tag.

            if not isinstance(v, basestring):
                safe = [str(e) for e in v]
            else:
                safe = str(e)

            to_tags[k] = safe
        except mutagen.easyid3.EasyID3KeyError as e:
            #Raised because we're copying in an unsupported in easy-mode key.
            log.debug("skipping non easy key", exc_info=True)
        except:
            #lots of things can go wrong, just skip the key
            log.warning("problem when copying keys from '%s' to '%s'", from_fname, to_fname, exc_info=True)
            success = False

    try:
        to_tags.save()
    except:
        log.warning("could not save tag file %s", to_fname, exc_info=True)
        success = False

    return success

def to_camel_case(s):
    """Given a sring in underscore form, returns a copy of it in camel case.
    eg, camel_case('test_string') => 'TestString'. """
    return ''.join(map(lambda x: x.title(), s.split('_')))

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


#From http://stackoverflow.com/questions/275174/how-do-i-perform-html-decoding-encoding-using-python-django
name2codepoint['#39'] = 39
def unescape_html(s):
    """Return unescaped HTML code.

    see http://wiki.python.org/moin/EscapingHtml."""
    return re.sub('&(%s);' % '|'.join(name2codepoint),
              lambda m: unichr(name2codepoint[m.group(1)]), s)


#Used to mark a field as unimplemented.
#From: http://stackoverflow.com/questions/1151212/equivalent-of-notimplementederror-for-fields-in-python
@property
def NotImplementedField(self):
    raise NotImplementedError

def call_succeeded(response):
    """Returns True if the call succeeded, False otherwise."""

    #Failed responses always have a success=False key.
    #Some successful responses do not have a success=True key, however.

    if 'success' in response.keys():
        return response['success']
    else:
        return True
