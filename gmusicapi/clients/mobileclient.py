from urlparse import urlparse, parse_qsl

from gmusicapi.clients.shared import _Base
from gmusicapi.protocol import mobileclient
from gmusicapi import session


class Mobileclient(_Base):
    """Allows library management and streaming by posing as the
    googleapis.com mobile clients.

    Uploading is not supported by this client (use the :class:`Musicmanager`
    to upload).
    """
    def __init__(self, debug_logging=True):
        self.session = session.Webclient()  # TODO change name; now shared

        super(Mobileclient, self).__init__(self.__class__.__name__, debug_logging)
        self.logout()

    def login(self, email, password):
        """Authenticates the webclient.
        Returns ``True`` on success, ``False`` on failure.

        :param email: eg ``'test@gmail.com'`` or just ``'test'``.
        :param password: password or app-specific password for 2-factor users.
          This is not stored locally, and is sent securely over SSL.

        Users of two-factor authentication will need to set an application-specific password
        to log in.
        """

        if not self.session.login(email, password):
            self.logger.info("failed to authenticate")
            return False

        self.logger.info("authenticated")

        return True

    def search(self, query, max_results=5):
        """Queries the server for songs and albums.

        :param query: a string keyword to search with. Capitalization and punctuation are ignored.
        :param max_results: Maximum number of items to be retrieved

        The results are returned in a dictionary, arranged by how they were found.
        ``artist_hits`` and ``song_hits`` return a list of
        :ref:`song dictionaries <songdict-format>`, while ``album_hits`` entries
        have a different structure.
        """

        #XXX provide an example
        res = self._make_call(mobileclient.Search, query, max_results)['entries']

        return {"album_hits": [hit for hit in res if hit['type'] == "3"],
                "artist_hits": [hit for hit in res if hit['type'] == "2"],
                "song_hits": [hit for hit in res if hit['type'] == "1"]}

    def get_artist(self, artistid, albums=True, top_tracks=0, rel_artist=0):
        """Retrieve artist data"""
        res = self._make_call(mobileclient.GetArtist, artistid, albums, top_tracks, rel_artist)
        return res

    def get_album(self, albumid, tracks=True):
        """Retrieve artist data"""
        res = self._make_call(mobileclient.GetAlbum, albumid, tracks)
        return res

    def get_track(self, trackid):
        """Retrieve artist data"""
        res = self._make_call(mobileclient.GetTrack, trackid)
        return res

    def get_stream_audio(self, song_id):
        """Returns a bytestring containing mp3 audio for this song.

            :param song_id: a single song id
        """

        urls = self.get_stream_urls(song_id)

        if len(urls) == 1:
            return self.session._rsession.get(urls[0]).content

        # AA tracks are separated into multiple files
        # the url contains the range of each file to be used

        range_pairs = [[int(s) for s in val.split('-')]
                       for url in urls
                       for key, val in parse_qsl(urlparse(url)[4])
                       if key == 'range']

        stream_pieces = []
        prev_end = 0

        for url, (start, end) in zip(urls, range_pairs):
            audio = self.session._rsession.get(url).content
            stream_pieces.append(audio[prev_end - start:])

            prev_end = end + 1

        return ''.join(stream_pieces)

    def get_stream_urls(self, song_id):
        """Returns a url that points to a streamable version of this song.

        :param song_id: a single song id.

        While acquiring the url requires authentication, retreiving the
        url contents does not.

        However, there are limitation as to how the stream url can be used:
            * the url expires after about a minute
            * only one IP can be streaming music at once.
              Other attempts will get an http 403 with
              ``X-Rejected-Reason: ANOTHER_STREAM_BEING_PLAYED``.

        *This is only intended for streaming*. The streamed audio does not contain metadata.
        Use :func:`get_song_download_info` to download complete files with metadata.
        """
        res = self._make_call(mobileclient.GetStreamUrl, song_id)

        try:
            return res['url']
        except KeyError:
            return res['urls']
