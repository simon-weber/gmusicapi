# -*- coding: utf-8 -*-

"""Tools for manipulating client-received Google Music data."""
from __future__ import print_function, division, absolute_import, unicode_literals
from builtins import *  # noqa

import operator
import re
import collections

from collections import Counter
from functools import reduce


def get_id_pairs(track_list):
    """Create a list of (sid, eid) tuples from a list of tracks.
    Tracks without an eid will have an eid of None."""

    return [(t["id"], t.get("playlistEntryId")) for t in track_list]


def find_playlist_changes(orig_tracks, modified_tracks):
    """Finds the changes between two playlists.

    Returns a tuple of (deletions, additions, staying).
    Deletions and additions are both Counters of (sid, eid) tuples;
    staying is a set of (sid, eid) tuples.

    :param old: the original playlist.
    :param modified: the modified playlist."""

    s_pairs = get_id_pairs(orig_tracks)

    # Three cases for desired pairs:
    # 1: (sid, eid from this playlist): either no action or add
    #    (if someone adds a dupe from the same playlist)
    # 2: (sid, eid not from this playlist): add
    # 3: (sid, None): add
    d_pairs = get_id_pairs(modified_tracks)

    # Counters are multisets.
    s_count = Counter(s_pairs)
    d_count = Counter(d_pairs)

    to_del = s_count - d_count
    to_add = d_count - s_count
    to_keep = set(s_count & d_count)  # guaranteed to be counts of 1

    return (to_del, to_add, to_keep)


def filter_song_md(song, md_list=['id'], no_singletons=True):
    """Returns a list of desired metadata from a song.
    Does not modify the given song.

    :param song: Dictionary representing a GM song.
    :param md_list: (optional) the ordered list of metadata to select.
    :param no_singletons: (optional) if md_list is of length 1, return the data,
      not a singleton list.
    """

    filtered = [song[md_type] for md_type in md_list]

    if len(md_list) == 1 and no_singletons:
        return filtered[0]
    else:
        return filtered


def build_song_rep(song, md_list=['title', 'artist', 'album'], divider=" - "):
    """Returns a string of the requested metadata types.
    The order of md_list determines order in the string.

    :param song: Dictionary representing a GM song.
    :param md_list: (optional) list of valid GM metadata types.
    :param divider: (optional) string to join the metadata.
    """

    filtered = filter_song_md(song, md_list, no_singletons=False)

    return divider.join(filtered)


def reorder_to(l, order):
    """Returns a list, reordered to a specific ordering.

    :param l: the list to reorder. It is not modified.
    :param order: a list containing the new ordering,
                  eg [2,1,0] to reverse a list of length 3
    """

    # Zip on ordering, sort by it, then remove ordering.
    return [el[1] for el in sorted(zip(order, l), key=lambda el: el[0])]


def build_queries_from(f, regex, cap_types, cap_pr, encoding='ascii'):
    """Returns a list of queries from the given file.
    Queries have the form [(<query>, <metadata type>), ...]

    :param f: opened file, ready to read.
    :param regex: a compiled regex to capture query info from file lines.
    :param cap_types: the GM metadata types of the regex captures.
    :param cap_pr: the priority of the captures.
    :param encoding: (optional) encoding of the file.
    """

    queries = []

    for line in f:
            matches = regex.match(line)

            if matches:
                # Zip captures to their types and order by priority to build a query.
                query = reorder_to(
                    list(zip(matches.groups(), cap_types)),
                    cap_pr)

                queries.append(query)

    return queries


def build_query_rep(query, divider=" - "):
    """Build a string representation of a query, without metadata types"""

    return divider.join([el[0] for el in query])


# Not mine. From: http://en.wikipedia.org/wiki/Function_composition_(computer_science)
def compose(*funcs, **kfuncs):
    """Compose a group of functions (f(g(h(..)))) into (fogoh...)(...)"""
    return reduce(lambda f, g: lambda *args, **kaargs: f(g(*args, **kaargs)), funcs)


class SongMatcher(object):
    """Matches GM songs to user-provided metadata."""

    def __init__(self, songs, log_metadata=['title', 'artist', 'album']):
        """Prepares songs for matching and determines logging options.

        :param songs: list of GM songs to match against.
        :param log_metadata: list of valid GM metadata types to show in the log.
                             order given will be order outputted.
        """

        # If match times are a problem, could
        # read to an indexed format here.
        self.library = songs

        # Lines of a log of how matching went.
        self.log_lines = []

        self.log_metadata = log_metadata

    def build_log(self):
        """Returns a string built from the current log lines."""

        encoded_lines = [line.encode('utf-8') for line in self.log_lines]
        return "\n".join(encoded_lines)

    def build_song_for_log(self, song):
        """Returns a string built from a song using log options.

        :param song:
        """

        return build_song_rep(song, self.log_metadata)

    class SearchModifier(object):
        """Controls how to query the library.
        Implementations define a comparator, and 2 functions
        (transformers) to modify the query and song data on the fly.

        Sometimes it makes sense to chain implementations.
        In this case, transformers are composed and the most
        outward comparator is used.
        """

        def __init__(self, q_t, s_t, comp):
            # Comparator - defines how to compare query and song data.
            # f(song data, query) -> truthy value
            self.comp = comp

            # Query and song transformers -
            # manipulate query, song before comparison.
            # f(unicode) -> unicode
            self.q_t = q_t

            self.s_t = s_t

    # Some modifiers that are useful in my library:
    # Ignore capitalization:
    ignore_caps = SearchModifier(
        # Change query and song to lowercase,
        # before comparing with ==.
        str.lower,
        str.lower,
        operator.eq
    )

    # Wildcard punctuation (also non ascii chars):
    ignore_punc = SearchModifier(
        # Replace query with a regex, where punc matches any (or no) characters.
        lambda q: re.sub(r"[^a-zA-Z0-9\s]", ".*", q),
        # Don't change the song.
        lambda s: s,
        # The comparator becomes regex matching.
        lambda sd, q: re.search(q, sd)
    )

    implemented_modifiers = (ignore_caps, ignore_punc)

    # The modifiers and order to be used in auto query mode.
    auto_modifiers = implemented_modifiers

    # Tiebreakers are used when there are multiple results from a query.
    @staticmethod
    def manual_tiebreak(query, results):
        """Prompts a user to choose a result from multiple.
        For use with query_library as a tiebreaker.
        Returns a singleton list or None.

        :param query: the original query.
        :param results: list of results.
        """

        print()
        print("Manual tiebreak for query:")
        print(build_query_rep(query).encode('utf-8'))
        print()
        print("Enter the number next to your choice:")
        print()
        print("0: None of these.")

        menu_lines = []
        key = 1

        for song in results:
            menu_lines.append(
                str(key) +
                ": " +
                build_song_rep(song).encode('utf-8'))

            key += 1

        print("\n".join(menu_lines))

        choice = -1

        while not (0 <= choice <= len(results)):
            try:
                choice = int(input("Choice: "))
            except ValueError:
                pass

        return None if choice == 0 else [results[choice - 1]]

    # Tiebreaker which does nothing with results.
    @staticmethod
    def no_tiebreak(query, results):
        return results

    # Exception thrown when a tie is broken.
    class TieBroken(Exception):
        def __init__(self, results):
            self.results = results

    # A named tuple to hold the frozen args when querying recursively.
    QueryState = collections.namedtuple('QueryState', 'orig t_breaker mods auto')

    def query_library(self, query, tie_breaker=no_tiebreak, modifiers=None, auto=False):
        """Queries the library for songs.
        returns a list of matches, or None.
        """

        if not modifiers:
            modifiers = []

        try:
            if not auto:
                return self.query_library_rec(query, self.library,
                                              self.QueryState(query, tie_breaker, modifiers, auto))
            else:
                # Auto mode attempts a search with the current modifiers.
                # If we get 1 result, we return it.
                # If we get no results, we add the next mod from auto_modifers and try again.
                # If we get many results, we branch and try with another modifier.
                # On no results, we tiebreak our old results.
                # Otherwise, we return the branched results.

                current_mods = modifiers[:]
                # Be ready to use any mods from the auto list which we aren't using already.
                future_mods = (m for m in self.auto_modifiers if m not in modifiers)

                while True:  # broken when future_mods runs out

                    # will not break ties in auto mode
                    results = self.query_library_rec(
                        query, self.library,
                        self.QueryState(query, tie_breaker, current_mods, auto))

                    if not results:
                        try:
                            current_mods.append(next(future_mods))
                        except StopIteration:
                            return results

                    elif len(results) == 1:
                        return results

                    else:
                        # Received many results from our current search.
                        # Branch; try more modifers to try and improve.
                        # If results, use them; otherwise tiebreak ours.
                        try:
                            current_mods.append(next(future_mods))
                        except StopIteration:
                            raise self.TieBroken(tie_breaker.__func__(query, results))

                        next_results = self.query_library(query, tie_breaker, current_mods, auto)

                        if not next_results:
                            raise self.TieBroken(tie_breaker.__func__(query, results))
                        else:
                            return next_results
        except self.TieBroken as tie:
            return tie.results

    def query_library_rec(self, query, library, state):
        """Returns a list of matches, or None.
        Recursive querying routine for query_library.
        """

        if len(query) == 0:
            return None

        # Composing applies right to left; currently mods are left to right.
        # Reverse then append the default modifier for proper compose order.
        mods_to_apply = [sm for sm in reversed(state.mods)]
        mods_to_apply.append(self.SearchModifier(
            lambda q: q,
            lambda sd: sd,
            operator.eq))

        # Create the transformers by composing all of them.
        q_t = compose(*list(map((lambda sm: sm.q_t), mods_to_apply)))
        s_t = compose(*list(map((lambda sm: sm.s_t), mods_to_apply)))

        # Use the most outward comparator.
        comp = mods_to_apply[0].comp

        q, md_type = query[0]

        # No need to repeatedly transform q.
        q_transformed = q_t(q)

        # GM limits libraries to 20k songs; this isn't a big performance hit.
        results = [s for s in library if comp(s_t(s[md_type]), q_transformed)]

        # Check for immediate return conditions.
        if not results:
            return None

        if len(results) == 1:
            return [results[0]]

        # Try to refine results by querying them with the next metadata in the query.
        next_query = query[1:]

        next_results = self.query_library_rec(next_query, results, state)

        if not next_results:
            # Don't break ties in auto mode; it's handled a level up.
            if not state.auto:
                raise self.TieBroken(state.t_breaker(state.orig, results))
            else:
                return results

        # Now we have multiple for both our query and the next.
        # Always prefer the next query to ours.
        return next_results

    def match(self, queries, tie_breaker=manual_tiebreak, auto=True):
        """Runs queries against the library; returns a list of songs.
        Match success is logged.

        :param query: list of (query, metadata type) in order of precedence.
                      eg [('The Car Song', 'title'), ('The Cat Empire', 'artist')]
        :param tie_breaker: (optional) tie breaker to use.
        :param modifiers: (optional) An ordered collection of SearchModifers.
          Applied during the query left to right.
        :param auto: (optional) When True, automagically manage modifiers to find results.
        """

        matches = []

        self.log_lines.append("## Starting match of " + str(len(queries)) + " queries ##")

        for query in queries:
            res = self.query_library(query, tie_breaker, auto=auto)

            if res:
                matches += res

            # Log the results.

            # The alert precedes the information for a quick view of what happened.
            alert = None
            if res is None:
                alert = "!!"
            elif len(res) == 1:
                alert = "=="
            else:
                alert = "??"

            # Each query shows the alert and the query.
            self.log_lines.append(alert + " " + build_query_rep(query))

            # Displayed on the line below the alert (might be useful later).
            extra_info = None

            if res:
                for song in res:
                    self.log_lines.append(
                        (extra_info if extra_info else (' ' * len(alert))) +
                        " " +
                        self.build_song_for_log(song))

            elif extra_info:
                self.log_lines.append(extra_info)

        return matches
