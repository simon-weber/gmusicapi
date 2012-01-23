#!/user/bin/env python

import gm_interface
from getpass import getpass

def init():
    """Makes an instance of the api and attempts to login with it.
    Returns the authenticated api.
    """

    api = gm_interface.Api()
    
    logged_in = False
    attempts = 0

    while not logged_in and attempts < 3:
        email = raw_input("Email: ")
        password = getpass()

        logged_in = api.login(email, password)
        attempts += 1

    return api

def main():
    """Demonstrates all api features.
    Logs in, gets library, searches for a song, selects the first result, 
    then creates a new playlist and adds that song to it.
    Finally, it renames and deletes the playlist.
    """

    api = init()

    print "Loading library...",
    library = api.load_library()
    print "done"

    print len(library), "tracks detected."
    print
    
    query = raw_input("Search Query: ")
    search_results = api.search(query)
        
    #Note that this only looks at hits on songs.
    #Songs matched on artist/album hits are discarded by selecting ['songs'].
    songs = search_results['results']['songs']
    if len(songs) == 0:
        print "No songs from that search."
        return

    song = songs[0]
    print "Selected", song['title'],"by",song['artist']
    song_id = song['id']


    playlist_name = raw_input("New playlist name: ")
    res = api.addplaylist(playlist_name)

    if not res['success']:
        print "Failed to make the playlist."
        return

    print "Made new playlist named",res['title']


    playlist_id = res['id']
    res = api.addtoplaylist(playlist_id, song_id)
    print "Added to playlist."

    res = api.modifyplaylist(playlist_id, "a different name")
    print "Modified playlist name."

    raw_input("Press enter to delete the playlist.")
    res = api.deleteplaylist(playlist_id)
    print "Deleted playlist."

    print "Done!"
    
    api.logout()

if __name__ == '__main__':
    main()
