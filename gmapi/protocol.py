"""The protocol layer is a one-to-one mapping of calls to Google Music."""


class WC_Protocol:

    @staticmethod
    def addplaylist(title): 
        """Creates a new playlist.

        :param title: the title of the playlist to create.
        """

        return {"title": title}


    @staticmethod
    def addtoplaylist(playlist_id, song_ids):
        """Adds songs to a playlist.

        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids, or a single song id.
        """

        song_ids = wrap_single_string(song_ids)

        return {"playlistId": playlist_id, "songIds": song_ids} 


    @staticmethod
    def modifyplaylist(playlist_id, new_name):
        """Changes the name of a playlist.

        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """
        
        return {"playlistId": playlist_id, "playlistName": new_name}


    @staticmethod
    def deleteplaylist(playlist_id):
        """Deletes a playlist.

        :param playlist_id: id of the playlist to delete.
        """
        
        return {"id": playlist_id}

    @staticmethod
    def deletesong(song_ids):
        """Delete a song from the entire library.

        :param song_ids: a list of song ids, or a single song id.
        """
        
        song_ids = wrap_single_string(song_ids)

        return {"songIds": song_ids, "entryIds":[""], "listId": "all"}

    @staticmethod
    def loadalltracks(cont_token = None):
        """Loads tracks from the library.
        Since libraries can have many tracks, GM gives them back in chunks.
        Chunks will send a continuation token to get the next chunk.
        The first request needs no continuation token.
        The last response will not send a token.
        
        :param cont_token: (optional) token to get the next library chunk.
        """

        if not cont_token:
            return {}
        else:
            return {"continuationToken": cont_token}

    @staticmethod
    def multidownload(song_ids):
        """Get download links and counts for songs.

        :param song_ids: a list of song ids, or a single song id.
        """

        song_ids = wrap_single_string(song_ids)

        return {"songIds": song_ids}

    @staticmethod
    def search(query):
        """Searches for songs, artists and albums.
        GM ignores punctuation.

        :param query: the search query.
        """

        return {"q": query}


def wrap_single_string(item):
    """If item is a string, return [item]. Otherwise return item.

    :param item
    """

    return [item] if isinstance(item, basestring) else item
