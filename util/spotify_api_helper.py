import re

from loguru import logger
import requests

from datatypes.SpotifyArtist import SpotifyArtist

CLIENT_ID = '26452cc6850d4d1abbd2adb5a6ffccb4'
CLIENT_SECRET = 'b3aee1fc6a584eb89555582ea9bd9d66'
token = ''

def get_token():
  resp = requests.post('https://accounts.spotify.com/api/token', data={
  'grant_type': 'client_credentials'
  }, auth=(CLIENT_ID, CLIENT_SECRET))

  return resp.json()['access_token']

def search_tracks(query):
  return requests.get('https://api.spotify.com/v1/search', params={
    'q': query,
    'type': 'track'
  }, headers={
    'Accept': 'application/json',
    'Authorization': f'Bearer {token}'
  }).json()

def get_images(track_title, artist_name, album_title=''):
  global token

  stripped_track_title = re.sub(r'[^A-Za-z0-9 -]+', '', track_title.lower())
  stripped_track_title = stripped_track_title.replace('feat', '')
  stripped_artist_name = artist_name.lower().replace('&', '')
  query = f'{stripped_track_title} {stripped_artist_name}'

  search_results = search_tracks(query)

  if 'error' in search_results:
    if search_results['error']['message'] == 'The access token expired':
      logger.trace('Refreshed Spotify access token')
      token = get_token()
      search_results = search_tracks(query)

  track = None

  if not search_results.get('tracks').get('items'):
    logger.warning(f'No Spotify search results for: {query} (originally {artist_name} - {track_title})')
    return

  track = sorted(search_results['tracks']['items'], key=lambda k: k['popularity'], reverse=True)[0]

  album_image = track['album']['images'][0]['url']
  album_image_small = track['album']['images'][-1]['url']
  artists = []

  for artist in track['artists']:
    artist_resp = requests.get(f'https://api.spotify.com/v1/artists/{artist["id"]}', headers={
      'Accept': 'application/json',
      'Authorization': f'Bearer {token}'
    })

    artist_json = artist_resp.json()

    artist_image = artist_json['images'][0]['url'] if artist_json['images'] else ''
    
    artists.append(
      SpotifyArtist(
        name=artist_json['name'], 
        spotify_url=artist_json['external_urls']['spotify'], 
        image_url=artist_image
      )
    )

  return artists, album_image, album_image_small

if not token:
  token = get_token()
