#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A script that will rewrite audiotest* metadata to match their filenames."""
from __future__ import print_function, division, absolute_import, unicode_literals
from builtins import *  # noqa

from glob import glob
import os

import mutagen

for fname in glob(u'audiotest*'):
    audio = mutagen.File(fname, easy=True)

    if audio is None:
        print('could not open', fname)
        continue

    # clear existing tags
    for key in list(audio.tags.keys()):
        del audio.tags[key]

    # write
    base = os.path.basename(fname)
    audio['title'] = base + ' title'
    audio['artist'] = base + ' artist'
    audio.save()

    # read back to verify
    audio = mutagen.File(fname, easy=True)  # assume it worked; it worked above
    print(fname)
    print('   ', audio.tags)
