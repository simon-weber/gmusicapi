from distutils.core import setup
from setuptools import find_packages

setup(
    name='UnofficialGoogleMusicAPI',
    version='0.1.0',
    author='Simon Weber',
    author_email='sweb090@gmail.com',
    packages=find_packages(),
    url='http://pypi.python.org/pypi/TowelStuff/',
    license='COPYING',
    description='An unofficial api for Google Play Music.',
    long_description=open('README.txt').read(),
    install_requires=[
        "validictory >= 0.8.1",
        "decorator >= 3.3.2",
        "mutagen >= 1.2.0",
        "protobuf >= 2.4.0"
    ]
)
