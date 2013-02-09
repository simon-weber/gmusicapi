#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages

import re

VERSIONFILE = 'gmusicapi/version.py'

version_line = open(VERSIONFILE).read()
version_re = r"^__version__ = ['\"]([^'\"]*)['\"]"
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
    long_description=open('README.md').read(),
    install_requires=[
        'validictory == 0.9.0',
        'decorator == 3.3.2',
        'mutagen == 1.21',
        'protobuf == 2.4.1',
        'chardet == 2.1.1',
        'requests == 1.1.0',
        #for testing album art:
        #'hachoir-core == 1.3.3',
        #'hachoir-parser == 1.3.4',
        #'hachoir-metadata == 1.3.3',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    include_package_data=True,
    zip_safe=False,
)
