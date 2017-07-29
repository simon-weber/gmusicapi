#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from setuptools import setup, find_packages
import sys
import warnings

dynamic_requires = []
# Python 2.7 is supported. Python 3 support is experimental
if sys.version_info[0] > 2:
    warnings.warn("gmusicapi Python 3 support is experimental", RuntimeWarning)
else:
    if sys.version_info[:3] < (2, 7, 9):
        warnings.warn("gmusicapi does not officially support versions below "
                      "Python 2.7.9", RuntimeWarning)

# try to continue anyway

# This hack is from http://stackoverflow.com/a/7071358/1231454;
# the version is kept in a seperate file and gets parsed - this
# way, setup.py doesn't have to import the package.

VERSIONFILE = 'gmusicapi/_version.py'

version_line = open(VERSIONFILE).read()
version_re = r"^__version__ = u['\"]([^'\"]*)['\"]"
match = re.search(version_re, version_line, re.M)
if match:
    version = match.group(1)
else:
    raise RuntimeError("Could not find version in '%s'" % VERSIONFILE)

setup(
    name='gmusicapi',
    version=version,
    author='Simon Weber',
    author_email='simon@simonmweber.com',
    url='http://pypi.python.org/pypi/gmusicapi/',
    packages=find_packages(),
    scripts=[],
    license=open('LICENSE').read(),
    description='An unofficial api for Google Play Music.',
    long_description=(open('README.rst').read() + '\n\n' +
                      open('HISTORY.rst').read()),
    install_requires=[
        'validictory >= 0.8.0, != 0.9.2',         # error messages
        'decorator >= 3.3.1',                     # > 3.0 likely work, but not on pypi
        'mutagen >= 1.34',                        # EasyID3 TPE2 mapping to albumartist
        ('requests >= 1.1.0, != 1.2.0,'           # session.close, memory view TypeError
         '!= 2.2.1, != 2.8.0, != 2.8.1,'
         '!= 2.12.0, != 2.12.1, != 2.12.2,'       # idna regression broke streaming urls
         '!= 2.18.2'),                            # SSLError became ConnectionError
        'python-dateutil >= 1.3, != 2.0',         # 2.0 is python3-only
        'proboscis >= 1.2.5.1',                   # runs_after
        'protobuf >= 3.0.0',
        'oauth2client >= 1.1',                    # TokenRevokeError
        'mock >= 0.7.0',                          # MagicMock
        'appdirs >= 1.1.0',                       # user_log_dir
        'gpsoauth >= 0.2.0',                      # mac -> android_id, validation, pycryptodome
        'MechanicalSoup >= 0.4.0',
        'six >= 1.9.0',                           # raise_from on Python 3
        'future',
    ] + dynamic_requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    include_package_data=True,
    zip_safe=False,
)
