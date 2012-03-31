from distutils.core import setup
from setuptools import find_packages

setup(
    name='gmusicapi',
    version='2012.03.27',
    author='Simon Weber',
    author_email='simon@simonmweber.com',
    url='https://github.com/simon-weber/Unofficial-Google-Music-API',
    packages=find_packages(),
    scripts=['example.py'],
    license='COPYING',
    description='An unofficial api for Google Play Music.',
    long_description="""\
gmusicapi is an unofficial api for Google Play Music. Please see the `project page <https://github.com/simon-weber/Unofficial-Google-Music-API>`_ for details.

This api is not supported nor endorsed by Google, and could break at any time.
""",
    install_requires=[
        "validictory >= 0.8.1",
        "decorator >= 3.3.2",
        "mutagen >= 1.2.0",
        "protobuf >= 2.4.0"
    ],
    classifiers = [
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ],
    include_package_data=True,
    zip_safe=False,
)
