#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Expectations about track metadata.
Clients typically just use the dict md_expectations."""

from collections import defaultdict, namedtuple


"""
These properties define knowledge about different metadata keys.

    name: key in the song dictionary
    type: a validictory type. possible values:
            'string' - str and unicode objects
            'integer' - ints
            'number' - ints and floats
            'boolean' - bools
            'object' - dicts
            'array' - lists and tuples
            'null' - None
            'any' - any type is acceptable
    mutable: True if client can change the value
    optional: True if the key is not always in the dictionary
    volatile: True if the key can change between observations without a client change
    depends_on: name of the key we take our value from, or None
    dependent_transformation: lambda dependent_value: our_value, or None
    allowed_values: sequence of possible values
"""
_Expectation = namedtuple(
    '_Expectation',
    [
        'name', 'type', 'mutable', 'optional', 'volatile',
        'depends_on', 'dependent_transformation',
        'allowed_values'
    ]
)


class Expectation(_Expectation):
    """Instantiated to represent information about a single metadata key."""
    #This class just wraps the namedtuple to provide easy construction and some methods.

    def __new__(cls, name, type, mutable, optional, volatile=False,
                depends_on=None, dependent_transformation=None,
                allowed_values=None):
        return cls.__bases__[0].__new__(
            cls,
            name, type, mutable, optional, volatile,
            depends_on, dependent_transformation,
            allowed_values
        )

    def get_schema(self):
        """Return a validictory schema for this key."""
        schema = {}
        schema["type"] = self.type
        if self.type == "string":
            schema["blank"] = True  # allow blank strings by default
        if self.optional:
            schema["required"] = False

        return schema

_all_expts = [
    Expectation(name, 'string', mutable=True, optional=False) for name in
    (
        'composer', 'album', 'albumArtist', 'genre', 'name', 'artist', 'comment',
    )
] + [
    Expectation(name, 'integer', mutable=True, optional=True) for name in
    (
        'disc', 'year', 'track', 'totalTracks', 'totalDiscs'
    )
] + [
    Expectation(name, type, mutable=False, optional=False) for (name, type) in
    {
        'durationMillis': 'integer',
        'id': 'string',
        'deleted': 'boolean',
        'creationDate': 'integer',
        'type': 'integer',  # enum, values not known yet
        'beatsPerMinute': 'integer',
        'url': 'string',
        'subjectToCuration': 'boolean',  # ??
        'matchedId': 'string',  # related to scan and match?
        'recentTimestamp': 'integer',  # ??
    }.items()
] + [
    Expectation(name, type, mutable=False, optional=True) for (name, type) in
    {
        'storeId': 'string',  # matching track in the store
        'reuploading': 'boolean',  # scan and match reupload in progress
        'albumMatchedId': 'string',  # scan and match for entire album?
        'pending': 'boolean',  # unsure: server processing (eg for store match) pending?
        'url': 'string',  # ??
        'bitrate': 'integer',
        'playlistEntryId': 'string',  # only appears in context of a playlist
        'albumArtUrl': 'string',
    }.items()
] + [
    Expectation(name + 'Norm', 'string', mutable=False, optional=False,
                depends_on=name,
                dependent_transformation=lambda x: x.lower()) for name in
    (
        'artist', 'albumArtist', 'album'
    )
] + [
    # 0, 1, 5: no, down, up thumbs
    Expectation('rating', 'integer', mutable=True,
                optional=False, allowed_values=tuple(range(6))),

    Expectation('lastPlayed', 'integer', mutable=False, optional=True, volatile=True),
    Expectation('playCount', 'integer', mutable=True, optional=False),

    Expectation('title', 'string', mutable=False, optional=False,
                depends_on='name', dependent_transformation=lambda x: x),

    Expectation('titleNorm', 'string', mutable=False, optional=False,
                depends_on='name', dependent_transformation=lambda x: x.lower()),
]

#Create the dict for client code. If they look up something we don't know about,
# give them a flexible immutable key.
_immutable_key = lambda: Expectation('unknown', 'any', mutable=False, optional=True)
md_expectations = defaultdict(_immutable_key)
for expt in _all_expts:
    md_expectations[expt.name] = expt
