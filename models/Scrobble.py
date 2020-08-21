from datetime import datetime

from datatypes.Track import Track
from datatypes.Artist import Artist
from datatypes.Album import Album
import util.LastFmApiWrapper as lastfm

class Scrobble:
  lastfm = None

  def __init__(self, track_title, artist_name, album_name, timestamp=datetime.now()):
    '''Entry in scrobble history with track information and a timestamp'''

    # Create Track instance with associated Artist and Album instances
    artist = Artist(artist_name)
    album = Album(album_name)
    self.track = Track(track_title, artist, album)
    
    # Automatically generated
    self.timestamp = timestamp

    # All scrobbles should store a reference to the same lastfm api wrapper instance
    if not Scrobble.lastfm:
      Scrobble.lastfm = lastfm.get_static_instance()

  def load_lastfm_data(self):
    '''Request info from Last.fm about the track, album, and artist'''

    lastfm_track = Scrobble.lastfm.get_track_info(self)['track']
    self.track.lastfm_url = lastfm_track['url']
    self.track.lastfm_plays = int(lastfm_track['userplaycount'])
    self.track.lastfm_is_loved = bool(lastfm_track['userloved']) # Convert 0/1 to bool
    # self.track.lastfm_tags = lastfm_track['toptags']['tag']

    lastfm_artist = Scrobble.lastfm.get_artist_info(self)['artist']
    self.track.artist.name = lastfm_artist['name']
    self.track.artist.lastfm_url = lastfm_artist['url']
    self.track.artist.lastfm_global_listeners = int(lastfm_artist['stats']['listeners'])
    self.track.artist.lastfm_global_plays = int(lastfm_artist['stats']['playcount'])
    self.track.artist.lastfm_plays = int(lastfm_artist['stats']['userplaycount'])
    self.track.artist.bio = lastfm_artist['bio']['content'].split(' <')[0].strip() # Remove read more on Last.fm link because a QML Link component is used instead
    # self.track.artist.lastfm_tags = lastfm_artist['tags']['tag']
    
    lastfm_album = Scrobble.lastfm.get_album_info(self)['album']
    self.track.album.title = lastfm_album['name']
    self.track.album.lastfm_url = lastfm_album['url']
    self.track.album.lastfm_plays = int(lastfm_album['userplaycount'])
    self.track.album.image_url = lastfm_album['image'][4]['#text'] # Pick mega size in images array
    self.track.album.image_url_small = lastfm_album['image'][1]['#text'] # Pick medium size in images array

    self.track.has_lastfm_data = True