import logging
import os
import requests
from typing import List

from PySide2 import QtCore, QtNetwork

from shared.components.NetworkImage import NetworkImage

from util.lastfm import LastfmApiWrapper, LastfmSession
from util.art_provider import ArtProvider
from util.spotify_api import SpotifyApiWrapper
from util import db_helper
from datatypes.Scrobble import Scrobble

class ApplicationViewModel(QtCore.QObject):
  # Qt Property changed signals
  is_logged_in_changed = QtCore.Signal()
  is_offline_changed = QtCore.Signal()

  # Event signals responded to by QML
  openOnboarding = QtCore.Signal()
  closeOnboarding = QtCore.Signal()
  isInMiniModeChanged = QtCore.Signal()
  preloadProfileAndFriends = QtCore.Signal()
  showNotification = QtCore.Signal(str, str)

  def __init__(self) -> None:
    QtCore.QObject.__init__(self)

    self.scrobble_history: List[Scrobble] = []
    self.is_logged_in: bool = False
    self.is_offline: bool = False

    self.preferences = {
      'initial_history_length': int(os.environ.get('INITIAL_HISTORY_ITEMS', 30))
      # 'media_plugin_choice' # can be mock
    }

    # Initialize helper classes
    self.lastfm = LastfmApiWrapper()
    self.spotify_api = SpotifyApiWrapper()
    self.art_provider = ArtProvider(self.lastfm, self.spotify_api)
    
    # Store whether the application window is in mini mode
    self._is_in_mini_mode: bool = None

    # Create network request manager and expose it to all NetworkImage instances
    self.network_manager = QtNetwork.QNetworkAccessManager()
    NetworkImage.NETWORK_MANAGER = self.network_manager

    # Connect to SQLite
    db_helper.connect()
  

  # --- Methods ---


  def log_in_with_onboarding_data(self, session: LastfmSession, media_player_preference: str) -> None:
    '''Save new login details to db, log in, and close onboarding'''

    self.lastfm.log_in_with_session(session)

    # Save Last.fm details and app preferences to the database
    db_helper.save_lastfm_session_to_database(session)
    db_helper.save_default_preferences_to_database(media_player_preference)

    # Close onboarding and start app
    self._set_is_logged_in(True)
    self.closeOnboarding.emit()
  
  # Needs better name
  def update_is_offline(self) -> None:
    try:
      requests.get('https://1.1.1.1')
      self._set_is_offline(False)
    except requests.exceptions.ConnectionError:
      self._set_is_offline(True)
  

  # --- Slots ---


  @QtCore.Slot()
  def attemptLogin(self) -> None:
    '''Try to log in using info from database, open onboarding if it doesn't exist'''

    # Try to get session key and username from database
    session = db_helper.get_lastfm_session()

    if session:
      # Set Last.fm wrapper session key and username from database
      self.lastfm.log_in_with_session(session)
      self._set_is_logged_in(True)
      logging.info(f'Logged in as {session.username}')
    else:
      self.openOnboarding.emit()
  
  @QtCore.Slot()
  def toggleMiniMode(self) -> None:
    self._is_in_mini_mode = not self._is_in_mini_mode
    self.isInMiniModeChanged.emit()
    db_helper.set_preference('is_in_mini_mode', self._is_in_mini_mode)
  

  # --- Private Methods ---


  def _set_is_logged_in(self, is_logged_in: bool) -> None:
    if is_logged_in:
      # Load mini moce preference from database
      self._is_in_mini_mode = db_helper.get_preference('is_in_mini_mode')
      self.isInMiniModeChanged.emit()

    self.is_logged_in = is_logged_in
    self.is_logged_in_changed.emit()

  def _set_is_offline(self, is_offline: bool) -> None:
    self.is_offline = is_offline
    self.is_offline_changed.emit()
  

  # --- Qt Properties ---


  isInMiniMode = QtCore.Property(
    type=bool,
    fget=lambda self: self._is_in_mini_mode,
    notify=isInMiniModeChanged
  )

  isLoggedIn = QtCore.Property(
    type=bool,
    fget=lambda self: self.is_logged_in,
    notify=is_logged_in_changed
  )