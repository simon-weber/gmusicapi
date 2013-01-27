#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Expectations about track metadata."""


class Expectation(object):
    """Instantiated to represent information about a single metadata key."""

    def __init__(self, name, type, mutable, optional, volatile=False,
                 depends_on=None, dependent_transformation=None,
                 allowed_values=None):
        """
        All params are available as fields after instantiation.

        :param name: key in the song dictionary
        :param type: a validictory type. possible values:
                       "string" - str and unicode objects
                       "integer" - ints
                       "number" - ints and floats
                       "boolean" - bools
                       "object" - dicts
                       "array" - lists and tuples
                       "null" - None
                       "any" - any type is acceptable
        :param mutable: True if client can change the value
        :param optional: True if the key is not always in the dictionary
        :param volatile: True if the key can change between observations without a client change
        :param depends_on: (optional) name of the key we take our value from
        :param dependent_transformation: (optional) lambda dependent_value: our_value
        :param allowed_values: (optional) list of possible values
        """
        self.name = name
        self.type = type
        self.mutable = mutable
        self.optional = optional
        self.volatile = volatile
        self.depends_on = depends_on
        self.dependent_transformation = dependent_transformation
        self.allowed_values = allowed_values

    def get_schema(self):
        """Return a validictory schema for this key."""
        schema = {}
        schema["type"] = self.type
        if self.type == "string":
            schema["blank"] = True  # allow blank strings by default
        if self.optional:
            schema["required"] = False

        return schema

all_expts = [
    Expectation(name, 'string', mutable=True, optional=False) for name in
    (
        'composer', 'album', 'albumArtist', 'genre', 'name', 'artist'
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
        'comment': 'string',
        'id': 'string',
        'deleted': 'boolean',
        'creationDate': 'integer',
        'type': 'integer',  # enum, values not known yet
        'beatsPerMinute': 'integer',
        'url': 'string',
        'subjectToCuration': 'boolean',  # ??
        'matchedId': 'string',  # related to scan and match?
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
    Expectation(name + 'Norm', type, mutable=False, optional=False,
                depends_on=name,
                dependent_transformation=lambda x: x.lower()) for name in
    (
        'artist', 'albumArtist', 'album'
    )
] + [
    # 0, 1, 5: no, down, up thumbs
    Expectation('rating', 'integer', mutable=True, optional=False, allowed_values=range(6)),

    Expectation('lastPlayed', 'integer', mutable=False, optional=True, volatile=True),
    Expectation('playCount', 'integer', mutable=True, optional=False),

    Expectation('title', 'string', mutable=False, optional=False,
                depends_on='name', dependent_transformation=lambda x: x),

    Expectation('titleNorm', 'string', mutable=False, optional=False,
                depends_on='title', dependent_transformation=lambda x: x.lower()),
]
