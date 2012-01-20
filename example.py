import json

from gm_interface import GM_API
from getpass import getpass

def main():
    #Test features of the GM API.
    #Login, search for a song, select the first result, then create a new playlist and add that song to it.

    api = GM_API()
    
    logged_in = False

    while not logged_in:
        email = raw_input("Email: ")
        password = getpass()

        logged_in = api.login(email, password)

    query = raw_input("Search Query: ")
    search_results = api.search(query)
    
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
    
    playlist_id = res['id']
    print "Made new playlist named",res['title']

    res = api.addtoplaylist(playlist_id, song_id)

    print res
    print "Done!"
    
    api.logout()

if __name__ == '__main__':
    main()
