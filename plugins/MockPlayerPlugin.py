from datatypes.MediaPlayerState import MediaPlayerState
from plugins.MediaPlayerPlugin import MediaPlayerPlugin

class MockPlayerPlugin(MediaPlayerPlugin):
  MOCK_TRACKS = [{
    # Test song with album on Last.fm that doesn't match Apple Music album
    'track_title': 'Don\'t Stop',
    'artist_name': 'Kuuro',
    'album_title': 'Don\'t Stop - Single',
    'track_start': 0,
    'track_finish': 100
  }, {
    # Test song with no album
    'track_title': 'Where It\'s At',
    'artist_name': 'Beck',
    'track_start': 0,
    'track_finish': 100
  }, {
    # Test consecutive tracks with the same title
    'track_title': 'Alone',
    'artist_name': 'Marshmello',
    'track_start': 0,
    'track_finish': 100
  }, {
    # Test consecutive tracks with the same title
    'track_title': 'Alone',
    'artist_name': 'Alan Walker',
    'track_start': 0,
    'track_finish': 100
  }, {
    # Test Last.fm corrections API
    'track_title': 'Waters (feat. Phluze) [Elbor edit]',
    'artist_name': 'Elbor',
    'album_title': 'Waters (Elbor edit) [feat. Phluze] - single',
    'track_start': 0,
    'track_finish': 100
  }, {
    # Test song with no artist
    'track_title': 'localtrack.mp3',
    'track_start': 0,
    'track_finish': 100
  }, {
    # Test song with 3 artists
    'track_title': 'Flames',
    'artist_name': 'R3HAB, ZAYN & Jungleboi',
    'album_title': 'Flames (The EP)',
    'track_start': 0,
    'track_finish': 100
  }, {
    # Test artist with diacritical marks in name
    'track_title': 'Grapevine',
    'artist_name': 'Tiësto',
    'album_title': 'Grapevine - Single',
    'track_start': 0,
    'track_finish': 221
  }, {
    # Test track with censored name
    'track_title': 'C**o',
    'artist_name': 'Jason Derulo, Puri & Jhorrmountain',
    'album_title': 'C**o - Single',
    'track_start': 0,
    'track_finish': 221
  }, {
    # Test track with super long title
    'track_title': 'Welcome to the Party (feat. Zhavia Ward) [From the "Deadpool 2" Original Motion Picture Soundtrack]',
    'artist_name': 'Diplo, French Montana & Lil Pump',
    'album_title': 'Welcome to the Party (feat. Zhavia Ward) [From the "Deadpool 2" Original Motion Picture Soundtrack] - Single',
    'track_start': 0,
    'track_finish': 221
  }, {
    # Test track with super long list of artists
    'track_title': 'Interstate 5 (feat. Azure Onyxscore, Hum4n01d, Arimyth, Mr. Serpent, console.frog, SpaghettiSauce, INDIR3CT & Glacial Viper)',
    'artist_name': 'Auxy Collective',
    'album_title': 'Interstate 5 (feat. Azure Onyxscore, Hum4n01d, Arimyth, Mr. Serpent, console.frog, SpaghettiSauce, INDIR3CT & Glacial Viper) - Single',
    'track_start': 0,
    'track_finish': 221
  }]

  def __init__(self):
    self.current_track = {}
    self.track_index = -1
    self.player_position = 0

  def get_state(self):
    if self.track_index != -1:
      track = self.MOCK_TRACKS[self.track_index % len(self.MOCK_TRACKS)]

      return MediaPlayerState(True, self.player_position, **track)
    
    return MediaPlayerState()
