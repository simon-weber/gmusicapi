#!/usr/bin/env python

# Copyright (c) 2012, Simon Weber
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of the contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Utility functions used across api code."""

import string
import re
import copy
from htmlentitydefs import name2codepoint

import mutagen
from decorator import decorator

from apilogging import LogController
log = LogController.get_logger("utils")

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

def empty_arg_shortcircuit(ret=[], position=1):
    """Decorate a function to shortcircuit and return something immediately if 
    the length of a positional arg is 0.

    :param ret: what to return when shortcircuiting
    :param position: (optional) the position of the expected list - defaults to 1.
    """

    @decorator
    def wrapper(function, *args, **kw):
        if len(args[position]) == 0:
            return ret
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
