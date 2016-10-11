#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import, unicode_literals
from builtins import *  # noqa

from getpass import getpass

from gmusicapi import Mobileclient


def ask_for_credentials():
    """Make an instance of the api and attempts to login with it.
    Return the authenticated api.
    """

    # We're not going to upload anything, so the Mobileclient is what we want.
    api = Mobileclient()

    logged_in = False
    attempts = 0

    while not logged_in and attempts < 3:
        email = input('Email: ')
        password = getpass()

        logged_in = api.login(email, password, Mobileclient.FROM_MAC_ADDRESS)
        attempts += 1

    return api


def demonstrate():
    """Demonstrate some api features."""

    api = ask_for_credentials()

    if not api.is_authenticated():
        print("Sorry, those credentials weren't accepted.")
        return

    print('Successfully logged in.')
    print()

    # Get all of the users songs.
    # library is a big list of dictionaries, each of which contains a single song.
    print('Loading library...', end=' ')
    library = api.get_all_songs()
    print('done.')

    print(len(library), 'tracks detected.')
    print()

    # Show some info about a song. There is no guaranteed order;
    # this is essentially a random song.
    first_song = library[0]
    print("The first song I see is '{}' by '{}'.".format(
        first_song['title'], first_song['artist']))

    # We're going to create a new playlist and add a song to it.
    # Songs are uniquely identified by 'song ids', so let's get the id:
    song_id = first_song['id']

    print("I'm going to make a new playlist and add that song to it.")
    print("I'll delete it when we're finished.")
    print()
    playlist_name = input('Enter a name for the playlist: ')

    # Like songs, playlists have unique ids.
    # Google Music allows more than one playlist of the same name;
    # these ids are necessary.
    playlist_id = api.create_playlist(playlist_name)
    print('Made the playlist.')
    print()

    # Now let's add the song to the playlist, using their ids:
    api.add_songs_to_playlist(playlist_id, song_id)
    print('Added the song to the playlist.')
    print()

    # We're all done! The user can now go and see that the playlist is there.
    # The web client syncs our changes in real time.
    input('You can now check on Google Music that the playlist exists.\n'
          'When done, press enter to delete the playlist:')
    api.delete_playlist(playlist_id)
    print('Deleted the playlist.')

    # It's good practice to logout when finished.
    api.logout()
    print('All done!')

if __name__ == '__main__':
    demonstrate()
