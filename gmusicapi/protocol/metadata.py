# -*- coding: utf-8 -*-

"""
All known information on metadata is exposed in ``gmusicapi.protocol.metadata.md_expectations``.

This holds a mapping of *name* to *Expectation*, where *Expectation* has
the following fields:

*name*
  key name in the song dictionary (equal to the *name* keying ``md_expectations``).

*type*:
    a string holding a `validictory <https://github.com/sunlightlabs/validictory>`__ type.

    Possible values:
      :'string':
          str and unicode objects
      :'integer':
          ints, longs
      :'number':
          ints, longs and floats
      :'boolean':
          bools
      :'object':
          dicts
      :'array':
          lists and tuples
      :'null':
          ``None``
      :'any':
          any type is possible

*mutable*:
  ``True`` if client can change the value.

*optional*:
  ``True`` if the key is not guaranteed to be present.

*volatile*:
  ``True`` if the key's value can change between observations without client mutation.

*depends_on*:
  the name of the key we transform to take our value from, or ``None``.

  These fields can never be changed: they are automatically set to
  a modified form of some other field's value.
  See *dependent_transformation* for more information.

*dependent_transformation*:
  ``None``, or a function ``lambda dependent_value: our_value``.

  For example, the ``artistNorm`` field is automatically set to the lowercase
  of the ``artist`` field.
  So, ``artistNorm.depends_on == 'artist'``, and the *dependent_transformation* for
  ``artistNorm`` can be written as ``lambda artist: artist.lower()``.

*allowed_values*:
  sequence of allowed values.

*explanation*:
  an explanatory string, typically empty for obvious fields.

The above information is used to generate the documentation below.
If you find an example to clarify these expectations, please `submit an issue
<https://github.com/simon-weber/Unofficial-Google-Music-API/issues>`__.
"""

from collections import defaultdict, namedtuple


_Expectation = namedtuple(
    '_Expectation',
    [
        'name', 'type', 'mutable', 'optional', 'volatile',
        'depends_on', 'dependent_transformation',
        'allowed_values', 'explanation'
    ]
)


class Expectation(_Expectation):
    """Instantiated to represent information about a single metadata key."""
    # This class just wraps the namedtuple to provide easy construction and some methods.

    def __new__(cls, name, type, mutable, optional, volatile=False,
                depends_on=None, dependent_transformation=None,
                allowed_values=None, explanation=''):
        return cls.__bases__[0].__new__(
            cls,
            name, type, mutable, optional, volatile,
            depends_on, dependent_transformation,
            allowed_values, explanation
        )

    def get_schema(self):
        """Return a validictory schema for this key."""
        schema = {}
        schema["type"] = self.type
        if self.type == "string":
            schema["blank"] = True  # allow blank strings
        if self.optional:
            schema["required"] = False

        return schema

#: All the expectations.
_all_expts = [
    Expectation(name, 'string', mutable=True, optional=False) for name in
    (
        'composer', 'album', 'albumArtist', 'genre', 'name', 'artist', 'comment',
    )
] + [
    Expectation(name, 'integer', mutable=True, optional=True) for name in
    (
        'disc', 'year', 'track', 'totalTracks', 'totalDiscs', 'explicitType',
    )
] + [
    Expectation(name, type_str, mutable=False, optional=False, explanation=explain)
    for (name, type_str, explain) in
    (
        ('durationMillis', 'integer',
         'length of a song in milliseconds.'),

        ('id', 'string',
         'a per-user unique id for this song; sometimes referred to as *server id* or *song id*.'),

        ('creationDate', 'integer', ''),
        ('type', 'integer',
         'An enum: 1: free/purchased, 2: uploaded/not matched, 6: uploaded/matched'),

        ('beatsPerMinute', 'integer',
         "the server does not calculate this - it's just what was in track metadata"),

        ('subjectToCuration', 'boolean', 'meaning unknown.'),
        ('curatedByUser', 'boolean', 'meaning unknown'),
        ('curationSuggested', 'boolean', 'meaning unknown'),
    )
] + [
    Expectation(name, type_str, mutable=False, optional=True, explanation=explain)
    for (name, type_str, explain) in
    (
        ('storeId', 'string', 'an id of a matching track in the Play Store.'),
        ('reuploading', 'boolean', 'scan-and-match reupload in progress.'),
        ('albumMatchedId', 'string', 'id of matching album in the Play Store?'),
        ('pending', 'boolean', 'unsure; server processing (eg for store match) pending?'),
        ('url', 'string', 'meaning unknown.'),
        ('bitrate', 'integer', "bitrate in kilobytes/second (eg 320)."),
        ('playlistEntryId', 'string', 'identifies position in the context of a playlist.'),
        ('albumArtUrl', 'string', "if present, the url of an image for this song's album art."),
        ('artistMatchedId', 'string', 'id of a matching artist in the Play Store?'),
        ('albumPlaybackTimestamp', 'integer', 'UTC/microsecond timestamp: the last time this album was played?'),   # noqa
        ('origin', 'array', '???'),
        ('artistImageBaseUrl', 'string', 'like albumArtUrl, but for the artist. May be blank.'),
        ('recentTimestamp', 'integer', 'UTC/microsecond timestamp: meaning unknown.'),
        ('deleted', 'boolean', ''),
        ('matchedId', 'string', 'meaning unknown; related to scan and match?'),
        ('previewToken', 'string', 'meaning unknown'),
        ('lastPlaybackTimestamp', 'integer', 'UTC/microseconds: last time the track was played'),
        ('lastRatingChangeTimestamp', 'integer', 'UTC/microseconds: last time the track was rated'),
    )
] + [
    Expectation(name + 'Norm', 'string', mutable=False, optional=False,
                depends_on=name,
                dependent_transformation=lambda x: x.lower(),
                explanation="automatically set to lowercase of *%s*." % name)
    for name in
    (
        'artist', 'albumArtist', 'album'
    )
] + [
    # 0, 1, 5: no, down, up thumbs
    Expectation('rating', 'integer', mutable=True,
                optional=False, allowed_values=tuple(range(6)),
                explanation='0 == no thumb, 1 == down thumb, 5 == up thumb.'),

    Expectation('lastPlayed', 'integer', mutable=False, optional=True, volatile=True,
                explanation='UTC/microsecond timestamp'),

    Expectation('playCount', 'integer', mutable=True, optional=False),

    Expectation('title', 'string', mutable=False, optional=False,
                depends_on='name', dependent_transformation=lambda x: x,
                explanation='misleading! automatically set to *name*.'),

    Expectation('titleNorm', 'string', mutable=False, optional=False,
                depends_on='name', dependent_transformation=lambda x: x.lower(),
                explanation='misleading! automatically set to lowercase of *name*.'),
]

# Create the dict for client code. If they look up something we don't know about,
# give them a flexible immutable key.
_immutable_key = lambda: Expectation('unknown', 'any', mutable=False, optional=True)  # noqa
md_expectations = defaultdict(_immutable_key)
for expt in _all_expts:
    md_expectations[expt.name] = expt


# This code is a super-hack. KnownMetadataFields exists _purely_ for documentation.

# We want dynamic documentation based on _all_expts, but __doc__ isn't a writable field
# for non-{function, class, module} objects. So, we create a dummy class and dynamically
# create its docstring to be arbitrary reST that documents our expectations.

def detail_line(e):
    """Given an expectation, return a readable one-line explanation of it."""
    fields = [fname for fname in ('mutable', 'optional', 'volatile')
              if getattr(e, fname, None)]

    if e.depends_on:
        fields.append("depends_on=%s" % e.depends_on)

    line = ', '.join(fields)
    if line:
        line = "*(%s)*" % line

    return line

# Note the hackiness of this class.
dynamic_docs = """
**This class exists only for documentation; do not try to import it.**

Instead, client code should use ``gmusicapi.protocol.metadata.md_expectations``.

See `the code <https://github.com/simon-weber/Unofficial-Google-Music-API/blob
/develop/gmusicapi/protocol/metadata.py>`__ for an explanation of this hack.
Ideas to clean this up are welcomed.

"""

# Create a reST definition list dynamically.
dynamic_docs += '\n\n'.join(
    ("*{name}*\n"
     "  {type} {details}\n\n"
     "  {explanation}").format(
        name=e.name,
        type=e.type,
        details=detail_line(e),
        explanation=e.explanation,
    ) for e in sorted(_all_expts, key=lambda e: e.name)
)


KnownMetadataFields = type('KnownMetadataFields', (defaultdict,), {'__doc__': dynamic_docs})
