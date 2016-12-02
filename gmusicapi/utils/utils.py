# -*- coding: utf-8 -*-

"""Utility functions used across api code."""
from __future__ import print_function, division, absolute_import, unicode_literals
from past.builtins import basestring
from builtins import *  # noqa

import ast
from bisect import bisect_left
from distutils import spawn
import errno
import functools
import inspect
import itertools
import logging
import os
import re
import subprocess
import time
import traceback
import warnings

from decorator import decorator
from google.protobuf.descriptor import FieldDescriptor

from gmusicapi import __version__
from gmusicapi.appdirs import my_appdirs
from gmusicapi.exceptions import CallFailure, GmusicapiWarning, NotSubscribed

# this controls the crazy logging setup that checks the callstack;
#  it should be monkey-patched to False after importing to disable it.
# when False, static code will simply log in the standard way under the root.
per_client_logging = True

# Map descriptor.CPPTYPE -> python type.
_python_to_cpp_types = {
    int: ('int32', 'int64', 'uint32', 'uint64'),
    float: ('double', 'float'),
    bool: ('bool',),
    str: ('string',),
}

cpp_type_to_python = dict(
    (getattr(FieldDescriptor, 'CPPTYPE_' + cpp.upper()), python)
    for (python, cpplist) in _python_to_cpp_types.items()
    for cpp in cpplist
)

log_filepath = os.path.join(my_appdirs.user_log_dir, 'gmusicapi.log')
printed_log_start_message = False  # global, set in config_debug_logging

# matches a mac address in GM form, eg
#   00:11:22:33:AA:BB
_mac_pattern = re.compile("^({pair}:){{5}}{pair}$".format(pair='[0-9A-F]' * 2))


class DynamicClientLogger(object):
    """Dynamically proxies to the logger of a Client higher in the call stack.

    This is a ridiculous hack needed because
    logging is, in the eyes of a user, per-client.

    So, logging from static code (eg protocol, utils) needs to log using the
    config of the calling client's logger.

    There can be multiple clients, so we can't just use a globally-available
    logger.

    Instead of refactoring every function to receieve a logger, we introspect
    the callstack at runtime to figure out who's calling us, then use their
    logger.

    This probably won't work on non-CPython implementations.
    """

    def __init__(self, caller_name):
        self.caller_name = caller_name

    def __getattr__(self, name):
        # this isn't a totally foolproof way to proxy, but it's fine for
        # the usual logger.debug, etc methods.

        logger = logging.getLogger(self.caller_name)

        if per_client_logging:
            # search upwards for a client instance
            for frame_rec in inspect.getouterframes(inspect.currentframe()):
                frame = frame_rec[0]

                try:
                    if 'self' in frame.f_locals:
                        f_self = frame.f_locals['self']

                        # can't import and check against classes; that causes an import cycle
                        if ((f_self is not None and
                             f_self.__module__.startswith('gmusicapi.clients') and
                             f_self.__class__.__name__ in ('Musicmanager', 'Webclient',
                                                           'Mobileclient'))):
                            logger = f_self.logger
                            break
                finally:
                    del frame  # avoid circular references

            else:
                # log to root logger.
                # should this be stronger? There's no default root logger set up.
                stack = traceback.extract_stack()
                logger.info('could not locate client caller in stack:\n%s',
                            '\n'.join(traceback.format_list(stack)))

        return getattr(logger, name)


log = DynamicClientLogger(__name__)


def deprecated(instructions):
    """Flags a method as deprecated.

    :param instructions: human-readable note to assist migration.
    """

    @decorator
    def wrapper(func, *args, **kwargs):
        message = "{0} is deprecated and may break unexpectedly.\n{1}".format(
            func.__name__,
            instructions)

        warnings.warn(message,
                      GmusicapiWarning,
                      stacklevel=2)

        return func(*args, **kwargs)

    return wrapper


def longest_increasing_subseq(seq):
    """Returns the longest (non-contiguous) subsequence
    of seq that is strictly increasing.
    """
    # adapted from http://goo.gl/lddm3c
    if not seq:
        return []

    # head[j] = index in 'seq' of the final member of the best subsequence
    # of length 'j + 1' yet found
    head = [0]
    # predecessor[j] = linked list of indices of best subsequence ending
    # at seq[j], in reverse order
    predecessor = [-1]
    for i in range(1, len(seq)):
        # Find j such that:  seq[head[j - 1]] < seq[i] <= seq[head[j]]
        # seq[head[j]] is increasing, so use binary search.
        j = bisect_left([seq[head[idx]] for idx in range(len(head))], seq[i])

        if j == len(head):
            head.append(i)
        if seq[i] < seq[head[j]]:
            head[j] = i

        predecessor.append(head[j - 1] if j > 0 else -1)

    # trace subsequence back to output
    result = []
    trace_idx = head[-1]
    while (trace_idx >= 0):
        result.append(seq[trace_idx])
        trace_idx = predecessor[trace_idx]

    return result[::-1]


def id_or_nid(song_dict):
    """Equivalent to ``d.get('id') or d['nid']``.

    Uploaded songs have an id key, while AA tracks
    have a nid key, which can often be used interchangably.
    """

    return song_dict.get('id') or song_dict['nid']


def datetime_to_microseconds(dt):
    """Return microseconds since epoch, as an int.

    :param dt: a datetime.datetime

    """
    return int(time.mktime(dt.timetuple()) * 1000000) + dt.microsecond


def is_valid_mac(mac_string):
    """Return True if mac_string is of form
    eg '00:11:22:33:AA:BB'.
    """
    if not _mac_pattern.match(mac_string):
        return False

    return True


def create_mac_string(num, splitter=':'):
    """Return the mac address interpretation of num,
    in the form eg '00:11:22:33:AA:BB'.

    :param num: a 48-bit integer (eg from uuid.getnode)
    :param spliiter: a string to join the hex pairs with
    """

    mac = hex(num)[2:]

    # trim trailing L for long consts
    if mac[-1] == 'L':
        mac = mac[:-1]

    pad = max(12 - len(mac), 0)
    mac = '0' * pad + mac
    mac = splitter.join([mac[x:x + 2] for x in range(0, 12, 2)])
    mac = mac.upper()

    return mac


# from http://stackoverflow.com/a/5032238/1231454
def make_sure_path_exists(path, mode=None):
    try:
        if mode is not None:
            os.makedirs(path, mode)
        else:
            os.makedirs(path)

    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


# from http://stackoverflow.com/a/8101118/1231454
class DocstringInheritMeta(type):
    """A variation on
    http://groups.google.com/group/comp.lang.python/msg/26f7b4fcb4d66c95
    by Paul McGuire
    """

    def __new__(meta, name, bases, clsdict):
        if not('__doc__' in clsdict and clsdict['__doc__']):
            for mro_cls in (mro_cls for base in bases for mro_cls in base.mro()):
                doc = mro_cls.__doc__
                if doc:
                    clsdict['__doc__'] = doc
                    break
        for attr, attribute in clsdict.items():
            if not attribute.__doc__:
                for mro_cls in (mro_cls for base in bases for mro_cls in base.mro()
                                if hasattr(mro_cls, attr)):
                    doc = getattr(getattr(mro_cls, attr), '__doc__')
                    if doc:
                        attribute.__doc__ = doc
                        break
        return type.__new__(meta, name, bases, clsdict)


def dual_decorator(func):
    """This is a decorator that converts a paramaterized decorator for no-param use.

    source: http://stackoverflow.com/questions/3888158.
    """
    @functools.wraps(func)
    def inner(*args, **kw):
        if ((len(args) == 1 and not kw and callable(args[0]) and
             not (type(args[0]) == type and issubclass(args[0], BaseException)))):
            return func()(args[0])
        else:
            return func(*args, **kw)
    return inner


@dual_decorator
def enforce_id_param(position=1):
    """Verifies that the caller is passing a single song id, and not
    a song dictionary.

    :param position: (optional) the position of the expected id - defaults to 1.
    """

    @decorator
    def wrapper(function, *args, **kw):

        if not isinstance(args[position], basestring):
            raise ValueError("Invalid param type in position %s;"
                             " expected an id (did you pass a dictionary?)" % position)

        return function(*args, **kw)

    return wrapper


@dual_decorator
def enforce_ids_param(position=1):
    """Verifies that the caller is passing a list of song ids, and not a
    list of song dictionaries.

    :param position: (optional) the position of the expected list - defaults to 1.
    """

    @decorator
    def wrapper(function, *args, **kw):

        if ((not isinstance(args[position], (list, tuple)) or
             not all([isinstance(e, basestring) for e in args[position]]))):
            raise ValueError("Invalid param type in position %s;"
                             " expected ids (did you pass dictionaries?)" % position)

        return function(*args, **kw)

    return wrapper


def configure_debug_log_handlers(logger):
    """Warnings and above to stderr, below to gmusicapi.log when possible.
    Output includes line number."""

    global printed_log_start_message

    logger.setLevel(logging.DEBUG)

    logging_to_file = True
    try:
        make_sure_path_exists(os.path.dirname(log_filepath), 0o700)
        debug_handler = logging.FileHandler(log_filepath)
    except (OSError, IOError):
        logging_to_file = False
        debug_handler = logging.StreamHandler()

    debug_handler.setLevel(logging.DEBUG)

    important_handler = logging.StreamHandler()
    important_handler.setLevel(logging.WARNING)

    logger.addHandler(debug_handler)
    logger.addHandler(important_handler)

    if not printed_log_start_message:
        # print out startup message without verbose formatting
        logger.info("!-- begin debug log --!")
        logger.info("version: " + __version__)
        if logging_to_file:
            logger.info("logging to: " + log_filepath)

        printed_log_start_message = True

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s (%(module)s:%(lineno)s) [%(levelname)s]: %(message)s'
    )
    debug_handler.setFormatter(formatter)
    important_handler.setFormatter(formatter)


@dual_decorator
def retry(retry_exception=None, tries=5, delay=2, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    An exception from a final attempt will propogate.

    :param retry_exception: exception (or tuple of exceptions) to check for and retry on.
      If None, use (AssertionError, CallFailure).
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
        retry_exception = (AssertionError, CallFailure)

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

    # Find the proper type.
    field_desc = msg.DESCRIPTOR.fields_by_name[field_name]
    proper_type = cpp_type_to_python[field_desc.cpp_type]

    # Try with the given type first.
    # Their set hooks will automatically coerce.
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


def locate_mp3_transcoder():
    """Return the path to a transcoder (ffmpeg or avconv) with mp3 support.

    Raise ValueError if none are suitable."""

    transcoders = ['ffmpeg', 'avconv']
    transcoder_details = {}

    for transcoder in transcoders:
        cmd_path = spawn.find_executable(transcoder)
        if cmd_path is None:
            transcoder_details[transcoder] = 'not installed'
            continue

        with open(os.devnull, "w") as null:
            stdout = subprocess.check_output([cmd_path, '-codecs'], stderr=null).decode("ascii")
        mp3_encoding_support = ('libmp3lame' in stdout and 'disable-libmp3lame' not in stdout)
        if mp3_encoding_support:
            transcoder_details[transcoder] = "mp3 encoding support"
            break  # mp3 decoding/encoding supported
        else:
            transcoder_details[transcoder] = 'no mp3 encoding support'
    else:
        raise ValueError('ffmpeg or avconv must be in the path and support mp3 encoding'
                         "\ndetails: %r" % transcoder_details)

    return cmd_path


def transcode_to_mp3(filepath, quality='320k', slice_start=None, slice_duration=None):
    """Return the bytestring result of transcoding the file at *filepath* to mp3.
    An ID3 header is not included in the result.

    :param filepath: location of file
    :param quality: if int, pass to -q:a. if string, pass to -b:a
                    -q:a roughly corresponds to libmp3lame -V0, -V1...
    :param slice_start: (optional) transcode a slice, starting at this many seconds
    :param slice_duration: (optional) when used with slice_start, the number of seconds in the slice

    Raise:
      * IOError: problems during transcoding
      * ValueError: invalid params, transcoder not found
    """

    err_output = None
    cmd_path = locate_mp3_transcoder()
    cmd = [cmd_path, '-i', filepath]

    if slice_duration is not None:
        cmd.extend(['-t', str(slice_duration)])
    if slice_start is not None:
        cmd.extend(['-ss', str(slice_start)])

    if isinstance(quality, int):
        cmd.extend(['-q:a', str(quality)])
    elif isinstance(quality, basestring):
        cmd.extend(['-b:a', quality])
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
            err_output = ("(return code: %r)\n" % proc.returncode) + err_output.decode("ascii")
            raise IOError  # handle errors in except

    except (OSError, IOError) as e:

        err_msg = "transcoding command (%r) failed: %s. " % (' '.join(cmd), e)

        if 'No such file or directory' in str(e):
            err_msg += '\nffmpeg or avconv must be installed and in the system path.'

        if err_output is not None:
            err_msg += "\nstderr: '%s'" % err_output

        log.exception('transcoding failure:\n%s', err_msg)

        raise IOError(err_msg)

    else:
        return audio_out


def truncate(x, max_els=100, recurse_levels=0):
    """Return a 'shorter' truncated x of the same type, useful for logging.
    recurse_levels is only valid for homogeneous lists/tuples.
    max_els ignored for song dictionaries."""

    # Coerce tuple to list to ease truncation.
    is_tuple = False
    if isinstance(x, tuple):
        is_tuple = True
        x = list(x)

    try:
        if len(x) > max_els:
            if isinstance(x, str):
                return x[:max_els] + '...'
            elif isinstance(x, basestring):
                return x[:max_els] + b'...'

            if isinstance(x, dict):
                if 'id' in x and 'titleNorm' in x:
                    # assume to be a song dict
                    trunc = dict((k, x.get(k)) for k in ['title', 'artist', 'album'])
                    trunc['...'] = '...'
                    return trunc
                else:
                    return dict(
                        itertools.chain(
                            itertools.islice(x.items(), 0, max_els),
                            [('...', '...')]))

            if isinstance(x, list):
                trunc = x[:max_els] + ['...']
                if recurse_levels > 0:
                    trunc = [truncate(e, recurse_levels - 1) for e in trunc[:-1]]
                if is_tuple:
                    trunc = tuple(trunc)
                return trunc

    except TypeError:
        # does not have len
        pass

    return x


@dual_decorator
def empty_arg_shortcircuit(return_code='[]', position=1):
    """Decorate a function to shortcircuit and return something immediately if
    the length of a positional arg is 0.

    :param return_code: (optional) simple expression to eval as the return value - default is a list
    :param position: (optional) the position of the expected list - default is 1.
    """

    # The normal pattern when making a collection an optional arg is to use
    # a sentinel (like None). Otherwise, you run the risk of the collection
    # being mutated - there's only one, not a new one on each call.
    # Here we've got multiple things we'd like to
    # return, so we can't do that. Rather than make some kind of enum for
    # 'accepted return values' I'm just allowing freedom to return basic values.
    # ast.literal_eval only can evaluate most literal expressions (e.g. [] and {})

    @decorator
    def wrapper(function, *args, **kw):
        if len(args[position]) == 0:
            return ast.literal_eval(return_code)
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
            # args are a tuple, can't assign into them
            args = list(args)
            args[position] = [args[position]]
            args = tuple(args)

        return function(*args, **kw)

    return wrapper


@decorator
def require_subscription(function, *args, **kwargs):
    self = args[0]

    if not self.is_subscribed:
        raise NotSubscribed("%s requires a subscription." % function.__name__)

    return function(*args, **kwargs)


# Modification of recipe found at
# https://wiki.python.org/moin/PythonDecoratorLibrary#Cached_Properties.
class cached_property(object):
    """Version of @property decorator that caches the result with a TTL.

    Tracks the property's value and last refresh time in a dict attribute
    of a class instance (``self._cache``) using the property name as the key.
    """

    def __init__(self, ttl=0):
        self.ttl = ttl

    def __call__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__

        return self

    def __get__(self, inst, owner):
        now = time.time()

        try:
            value, last_update = inst._cache[self.__name__]

            if (self.ttl > 0) and (now - last_update > self.ttl):
                raise AttributeError
        except (KeyError, AttributeError):
            value = self.fget(inst)

            try:
                cache = inst._cache
            except AttributeError:
                cache = inst._cache = {}

            cache[self.__name__] = (value, now)

        return value

    def __set__(self, inst, value):
        raise AttributeError("Can't set cached properties")

    def __delete__(self, inst):
        try:
            del inst._cache[self.__name__]
        except (KeyError, AttributeError):
            if not inst._cache:
                inst._cache = {}


# Used to mark a field as unimplemented.
@property
def NotImplementedField(self):
    raise NotImplementedError
