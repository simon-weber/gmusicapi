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
    long_description=open('README.md').read(),
    install_requires=[
        "validictory >= 0.8.1",
        "decorator >= 3.3.2",
        "mutagen >= 1.2.0",
        "protobuf >= 2.4.0"
    ],
    include_package_data=True,
    zip_safe=False,
)
