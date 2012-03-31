#!/user/bin/env python

#Copyright 2012 Simon Weber.

#This file is part of gmusicapi - the Unofficial Google Music API.

#Gmusicapi is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Gmusicapi is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with gmusicapi.  If not, see <http://www.gnu.org/licenses/>.


from gmusicapi.api import Api
from getpass import getpass

def init():
    """Makes an instance of the api and attempts to login with it.
    Returns the authenticated api.
    """
    
    api = Api() 
    
    logged_in = False
    attempts = 0

    while not logged_in and attempts < 3:
        email = raw_input("Email: ")
        password = getpass()

        logged_in = api.login(email, password)
        attempts += 1

    return api

def main():
    """Demonstrates some api features."""

    #Make a new instance of the api and prompt the user to log in.
    api = init()

    if not api.is_authenticated():
        print "Sorry, those credentials weren't accepted."
        return

    print "Successfully logged in."
    print

    #Get all of the users songs.
    #library is a big list of dictionaries, each of which contains a single song.
    print "Loading library...",
    library = api.get_all_songs()
    print "done."

    print len(library), "tracks detected."
    print

    #Show some info about a song. There is no guaranteed order;
    # this is essentially a random song.
    first_song = library[0]
    print "The first song I see is '{}' by '{}'.".format(
        first_song["name"],
        first_song["artist"])


    #We're going to create a new playlist and add a song to it.
    #Songs are uniquely identified by 'song ids', so let's get the id:
    song_id = first_song["id"]

    print "I'm going to make a new playlist and add that song to it."
    print "Don't worry, I'll delete it when we're finished."
    print
    playlist_name = raw_input("Enter a name for the playlist: ")

    #Like songs, playlists have unique ids.
    #Note that Google Music allows more than one playlist of the
    # exact same name, so you'll always have to work with ids.
    playlist_id = api.create_playlist(playlist_name)
    print "Made the playlist."
    print

    #Now lets add the song to the playlist, using their ids:
    api.add_songs_to_playlist(playlist_id, song_id)
    print "Added the song to the playlist."
    print

    #We're all done! The user can now go and see that the playlist is there.
    raw_input("You can now check on Google Music that the playlist exists. \n When done, press enter to delete the playlist:")
    api.delete_playlist(playlist_id)
    print "Deleted the playlist."


    #It's good practice to logout when finished.
    api.logout()
    print "All done!"

if __name__ == '__main__':
    main()
