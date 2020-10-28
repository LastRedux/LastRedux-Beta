import os
from datetime import datetime

from loguru import logger
from PySide2 import QtCore

from plugins.MockPlayerPlugin import MockPlayerPlugin
from plugins.AppleMusicPlugin import AppleMusicPlugin
from datatypes.Scrobble import Scrobble
from tasks.FetchNewMediaPlayerStateTask import FetchNewMediaPlayerStateTask
from tasks.LoadAdditionalScrobbleDataTask import LoadAdditionalScrobbleDataTask
from tasks.SubmitTrackIsLovedChanged import SubmitTrackIsLovedChanged
from tasks.FetchRecentScrobblesTask import FetchRecentScrobblesTask
from tasks.SubmitScrobbleTask import SubmitScrobbleTask
from tasks.UpdateNowPlayingTask import UpdateNowPlayingTask
import util.LastfmApiWrapper as lastfm

class HistoryViewModel(QtCore.QObject):
  # Constants
  __INITIAL_SCROBBLE_HISTORY_COUNT = 30

  # Qt Property changed signals
  current_scrobble_data_changed = QtCore.Signal()
  current_scrobble_percentage_changed = QtCore.Signal()
  is_using_mock_player_plugin_changed = QtCore.Signal()
  is_in_mini_mode_changed = QtCore.Signal()
  selected_scrobble_changed = QtCore.Signal()
  selected_scrobble_index_changed = QtCore.Signal()
  should_show_loading_indicator_changed = QtCore.Signal()
  
  # Scrobble history list model signals
  pre_append_scrobble = QtCore.Signal()
  post_append_scrobble = QtCore.Signal()
  scrobble_album_image_changed = QtCore.Signal(int)
  scrobble_lastfm_is_loved_changed = QtCore.Signal(int)
  begin_refresh_history = QtCore.Signal()
  end_refresh_history = QtCore.Signal()

  showNotification = QtCore.Signal(str, str)

  def __init__(self):
    QtCore.QObject.__init__(self)
    
    # Initialize media player plugin
    self.media_player = MockPlayerPlugin() if os.environ.get('MOCK') else AppleMusicPlugin()

    # Track window mode
    self.is_in_mini_mode = bool(os.environ.get('MINI_MODE'))

    # Get instance of lastfm api wrapper
    self.lastfm_instance = lastfm.get_static_instance()
    
    # Store Scrobble objects that have been submitted
    self.scrobble_history = []

    # Keep track of whether the history view is loading data
    self.__should_show_loading_indicator = False

    # Keep track of how many scrobbles have their additional data loaded from Last.fm and Spotify
    self.__scrobbles_with_additional_data_count = 0

    # Hold a Scrobble object for currently playing track (will later be submitted)
    self.__current_scrobble = None
    
    # Hold the index of the selected scrobble in the sidebar
    self.__selected_scrobble_index = None # -1 for current scrobble, None for no scrobble, numbers > 0 for history items
    
    # Hold the Scrobble object at the __selected_scrobble_index
    # This can either be a copy of the current scrobble or one in the history
    self.selected_scrobble = None

    # Keep track of whether the current scrobble has hit the threshold for scrobbling (to submit when current track changes)
    self.__current_scrobble_percentage = 0
    self.__should_submit_current_scrobble = None

    # Cached data from the media player for the currently playing track
    self.__cached_media_player_data = {
      'furthest_player_position_reached': None,
      'track_start': None,
      'track_finish': None,
      'is_current_track_valid': None,
      'ticks_since_track_changed': 0
    }

    # Load in recent scrobbles from Last.fm and process them
    if not os.environ.get('NO_HISTORY'):
      self.__should_show_loading_indicator = True
      self.should_show_loading_indicator_changed.emit()

      fetch_recent_scrobbles_task = FetchRecentScrobblesTask(self.lastfm_instance, self.__INITIAL_SCROBBLE_HISTORY_COUNT)
      fetch_recent_scrobbles_task.finished.connect(self.__process_fetched_recent_scrobbles)
      QtCore.QThreadPool.globalInstance().start(fetch_recent_scrobbles_task)

    if os.environ.get('SUBMIT_SCROBBLES'):
      logger.info('Scrobble submission is enabled')

    # Start polling interval to check for new media player state
    timer = QtCore.QTimer(self)
    timer.timeout.connect(self.__load_new_media_player_state)
    polling_interval = 100 if os.environ.get('FAST_POLLING') else 1000
    timer.start(polling_interval)

    # Load media player state immediately
    self.__load_new_media_player_state()

  # --- Qt Property Getters and Setters ---
  
  def get_current_scrobble_data(self):
    '''Return data about the currently playing track in the active media player'''
    
    if self.__current_scrobble:
      return {
        'hasLastfmData': self.__current_scrobble.has_lastfm_data,
        'trackTitle': self.__current_scrobble.title,
        'artistName': self.__current_scrobble.artist.name,
        'lastfmIsLoved': self.__current_scrobble.lastfm_is_loved,
        'albumImageUrl': self.__current_scrobble.album.image_url_small # The scrobble history album arts are small so we don't want to render the full size art
      }
    
    # Return None if there isn't a curent scrobble (such as when the app is first loaded or if there is no track playing)
    return None

  def get_current_scrobble_percentage(self):
    return self.__current_scrobble_percentage
  
  def get_is_using_mock_player_plugin(self):
    return isinstance(self.media_player, MockPlayerPlugin)

  def get_is_in_mini_mode(self):
    return self.is_in_mini_mode
    
  def get_selected_scrobble_index(self):
    '''Make the private selected scrobble index variable available to the UI'''
    
    if self.__selected_scrobble_index is None:
      # -2 represents no selection because Qt doesn't understand Python's None value
      return -2

    return self.__selected_scrobble_index
  
  def set_selected_scrobble_index(self, new_index):
    self.__selected_scrobble_index = new_index

    # Tell the UI that the selected index changed, so it can update the selection highlight in the sidebar to the correct index
    self.selected_scrobble_index_changed.emit()

    # Update selected_scrobble (Scrobble type) according to the new index
    if new_index == -1: # If the new selection is the current scrobble
      self.selected_scrobble = self.__current_scrobble
    else:
      self.selected_scrobble = self.scrobble_history[new_index]

      # Load additional scrobble data if it isn't already present
      self.__load_additional_scrobble_data(self.selected_scrobble)
    
    # Tell the UI that the selected scrobble was changed, so views like the scrobble details pane can update accordingly
    self.selected_scrobble_changed.emit()

  # --- Slots ---
  
  @QtCore.Slot(int)
  def toggleLastfmIsLoved(self, index):
    scrobble = None

    # -1 refers to current scrobble
    if index == -1:
      scrobble = self.__current_scrobble
    else:
      scrobble = self.scrobble_history[index]

    if not scrobble.has_lastfm_data:
      return
    
    new_is_loved = not scrobble.lastfm_is_loved

    if index == -1:
      scrobble.lastfm_is_loved = new_is_loved
    
    # Update any scrobbles in the scrobble history array that match the scrobble that changed
    for history_item in self.scrobble_history:
      if scrobble.equals(history_item):
        history_item.lastfm_is_loved = new_is_loved

    self.__emit_scrobble_ui_update_signals(scrobble)
    
    # Tell Last.fm about our new is_loved value
    submit_track_is_loved_task = SubmitTrackIsLovedChanged(self.lastfm_instance, scrobble, new_is_loved)
    QtCore.QThreadPool.globalInstance().start(submit_track_is_loved_task)

  @QtCore.Slot()
  def toggleMiniMode(self):
    self.is_in_mini_mode = not self.is_in_mini_mode
    self.is_in_mini_mode_changed.emit()

  # --- Mock Slots ---

  @QtCore.Slot()
  def MOCK_playNextSong(self):
    self.media_player.track_index += 1
    self.media_player.player_position = 0

  @QtCore.Slot()
  def MOCK_moveTo75Percent(self):
    self.media_player.player_position = self.__cached_media_player_data['track_finish'] * 0.75

  # --- Private Functions ---

  @QtCore.Slot()
  def __load_new_media_player_state(self):
    '''Fetch information about current track from media player in a background thread and load it into the app'''

    # Create thread task with reference to the media player
    load_new_media_player_state_task = FetchNewMediaPlayerStateTask(self.media_player)

    # Process the new media player state after the data is returned
    load_new_media_player_state_task.finished.connect(self.__process_new_media_player_state)

    # Add task to global thread pool and run
    QtCore.QThreadPool.globalInstance().start(load_new_media_player_state_task)

  def __submit_scrobble(self, scrobble):
    '''Add a scrobble object to the history array and submit it to Last.fm'''
    
    # Tell scrobble history list model that a change will be made
    self.pre_append_scrobble.emit()

    # Prepend the new scrobble to the scrobble_history array in the view model
    self.scrobble_history.insert(0, scrobble)

    # Tell scrobble history list model that a change was made in the view model
    # The list model will call the data function in the background to get the new data
    self.post_append_scrobble.emit()

    # Shift down the selected scrobble index if new scrobble has been added to the top
    # This is because if the user has a scrobble in the history selected and a new scrobble is submitted, it will display the wrong data if the index isn't updated
    # Change __selected_scrobble_index instead of calling set___selected_scrobble_index because the selected scrobble shouldn't be redundantly set to itself and still emit selected_scrobble_changed (wasting resources)
    if self.__selected_scrobble_index and self.__selected_scrobble_index != -1:
      # Shift down the selected scrobble index by 1
      self.__selected_scrobble_index += 1

      # Tell the UI that the selected index changed, so it can update the selection highlight in the sidebar to the correct index
      self.selected_scrobble_index_changed.emit()

    # Submit scrobble to Last.fm in background thread task
    if os.environ.get('SUBMIT_SCROBBLES'):
      submit_scrobble_task = SubmitScrobbleTask(self.lastfm_instance, self.__current_scrobble)
      QtCore.QThreadPool.globalInstance().start(submit_scrobble_task)

    # TODO: Decide what happens when a scrobble that hasn't been fully downloaded is submitted. Does it wait for the data to load for the plays to be updated or should it not submit at all?
    if scrobble.has_lastfm_data:
      scrobble.lastfm_plays += 1
      scrobble.artist.lastfm_plays += 1

      # Refresh scrobble details pane if the submitted scrobble is selected
      if self.selected_scrobble == scrobble:
        self.selected_scrobble_changed.emit()

  @QtCore.Slot(list)
  def __process_fetched_recent_scrobbles(self, lastfm_recent_scrobbles):
    # Tell the history list model that we are going to change the data it relies on
    self.begin_refresh_history.emit()

    for lastfm_scrobble in lastfm_recent_scrobbles:
      # Don't include currently playing track to scrobble history
      if lastfm_scrobble.get('@attr') and lastfm_scrobble.get('@attr').get('nowplaying'):
        continue

      scrobble = Scrobble(
        lastfm_scrobble['name'], 
        lastfm_scrobble['artist']['name'], 
        lastfm_scrobble['album']['#text'], 
        datetime.fromtimestamp(int(lastfm_scrobble['date']['uts']))
      )
      
      self.scrobble_history.append(scrobble)
      self.__load_additional_scrobble_data(scrobble)

    # Tell the history list model that we finished changing the data it relies on
    self.end_refresh_history.emit()

  @QtCore.Slot(dict)
  def __process_new_media_player_state(self, new_media_player_state):
    '''Update cached media player state and replace track if the media player track has changed'''

    # Alert the user of any errors that occured while trying to get media player state
    try:
      if new_media_player_state.error_message:
        raise Exception(new_media_player_state.error_message)

      is_current_track_valid = bool(new_media_player_state.track_title and new_media_player_state.artist_name)

      if is_current_track_valid:
        self.__cached_media_player_data['is_current_track_valid'] = True
      else:
        # Skip if the problem has already been caught and the user has been notified
        if not self.__cached_media_player_data['is_current_track_valid']:
          return

        self.__cached_media_player_data['is_current_track_valid'] = False
        raise Exception('Track title and artist metadata are required')
    except Exception as e:
      self.showNotification.emit('Error loading current track', str(e))
      logger.debug('Error loading media player state: ' + str(e))
      return

    if new_media_player_state.has_track_loaded:
      current_track_changed = (
        not self.__current_scrobble
        or new_media_player_state.track_title != self.__current_scrobble.title
        or new_media_player_state.artist_name != self.__current_scrobble.artist.name
        or new_media_player_state.album_title != self.__current_scrobble.album.title
      )

      if current_track_changed:
        # If the title didn't change, but the artist title or album title did, that could mean that the media player is providing bad data so wait 3 media player poll ticks to be sure
        # Don't check if there insn't a current scrobble yet
        if self.__current_scrobble:
          if self.__cached_media_player_data['ticks_since_track_changed'] < 3:
            if new_media_player_state.track_title == self.__current_scrobble.title:
              logger.debug('Skipping potentially bad media player data:')
              logger.debug(f'New track: {new_media_player_state.artist_name} - {new_media_player_state.track_title}')
              logger.debug(f'Current track: {self.__current_scrobble.artist.name} - {self.__current_scrobble.title}')
              self.__cached_media_player_data['ticks_since_track_changed'] += 1
              return

        # Submit the last scrobble when the current track changes if it hit the scrobbling threshold
        if self.__should_submit_current_scrobble:
          self.__submit_scrobble(self.__current_scrobble)

        self.__update_scrobble_to_match_new_media_player_data(new_media_player_state)
      
      # Refresh cached media player data for currently playing track
      player_position = new_media_player_state.player_position

      # Only update the furthest reached position in the track if it's further than the last recorded furthest position
      # This is because if the user scrubs backward in the track, the scrobble progress bar will stop moving until they reach the previous furthest point reached in the track
      # TODO: Add support for different scrobble submission styles such as counting seconds of playback
      if player_position >= self.__cached_media_player_data['furthest_player_position_reached']:
        self.__cached_media_player_data['furthest_player_position_reached'] = player_position
      
      self.__current_scrobble_percentage = self.__determine_current_scrobble_percentage()

      # Update scrobble progress bar UI
      self.current_scrobble_percentage_changed.emit()
    else: # There is no track loaded (player is stopped)
      if self.__current_scrobble:
        self.__current_scrobble = None

        # Update the UI in current scrobble sidebar item
        self.current_scrobble_data_changed.emit()

        # If the current scrobble is selected, deselect it
        if self.__selected_scrobble_index == -1:
          self.__selected_scrobble_index = None
          self.selected_scrobble = None
          
          # Update the current scrobble highlight and song details pane views
          self.selected_scrobble_index_changed.emit()
          self.selected_scrobble_changed.emit()
  
  def __determine_current_scrobble_percentage(self):
    '''Determine the percentage of the track that has played compared to a user-set percentage of the track length'''

    if not self.__current_scrobble:
      return 0

    # Compensate for custom track start and end times
    # TODO: Only do this if the media player is Apple Music/iTunes
    relative_position = self.__cached_media_player_data['furthest_player_position_reached'] - self.__cached_media_player_data['track_start']
    relative_track_length = self.__cached_media_player_data['track_finish'] - self.__cached_media_player_data['track_start']
    min_scrobble_length = relative_track_length * 0.75 # TODO: Grab the percentage from the settings database
    
    # Prevent scenarios where the relative position is negative
    relative_position = max(0, relative_position)

    scrobble_percentage = relative_position / min_scrobble_length

    # Prevent scenarios where the relative player position is greater than the relative track length (don't let the percentage by greater than 1)
    scrobble_percentage = min(scrobble_percentage, 1)

    # Submit current scrobble if the scrobble percentage (progress towards the scrobble threshold) is 100%
    if not self.__should_submit_current_scrobble and scrobble_percentage == 1:
      # TODO: Only submit when the song changes or the app is closed
      self.__should_submit_current_scrobble = True
      logger.debug(f'{self.__current_scrobble.title}: Ready for submission to Last.fm')

    return scrobble_percentage

  def __update_scrobble_to_match_new_media_player_data(self, new_media_player_state):
    '''Set __current_scrobble to a new Scrobble object created from the currently playing track, update the playback data for track start/finish, and update the UI'''

    # Initialize a new Scrobble object with the currently playing track data
    # This will set the Scrobble's timestamp to the current date
    self.__current_scrobble = Scrobble(new_media_player_state.track_title, new_media_player_state.artist_name, new_media_player_state.album_title)

    logger.trace(f'Now playing: {new_media_player_state.artist_name} - {new_media_player_state.track_title} | {new_media_player_state.album_title}')

    # Reset flag so new scrobble can later be submitted
    self.__should_submit_current_scrobble = False

    # Update UI content in current scrobble sidebar item
    self.current_scrobble_data_changed.emit()

    # Tell Last.fm to update the user's now playing status
    if not os.environ.get('MOCK'):
      update_now_playing_task = UpdateNowPlayingTask(self.lastfm_instance, self.__current_scrobble)
      QtCore.QThreadPool.globalInstance().start(update_now_playing_task)

    # Reset player position to temporary value until a new value can be recieved from the media player
    self.__cached_media_player_data['furthest_player_position_reached'] = 0

    # Refresh selected_scrobble with new __current_scrobble object if the current scrobble is selected, because otherwise the selected scrobble will reflect old data
    if self.__selected_scrobble_index == -1:
      self.selected_scrobble = self.__current_scrobble

      # Update details pane view
      self.selected_scrobble_changed.emit()
    elif self.__selected_scrobble_index is None:
      self.__selected_scrobble_index = -1
      self.selected_scrobble = self.__current_scrobble
      
      # Update the current scrobble highlight and song details pane views
      self.selected_scrobble_index_changed.emit()

      # Update details pane view
      self.selected_scrobble_changed.emit()

    # Update cached media player track playback data
    self.__cached_media_player_data['track_start'] = new_media_player_state.track_start
    self.__cached_media_player_data['track_finish'] = new_media_player_state.track_finish

    self.__load_additional_scrobble_data(self.__current_scrobble)

  def __load_additional_scrobble_data(self, scrobble):
    '''Create thread task to get additional info about track from Last.fm in the background'''

    load_additional_scrobble_data_task = LoadAdditionalScrobbleDataTask(scrobble)

    # Connect the emit_scrobble_ui_update_signals signal in the task to the local slot with the same name
    load_additional_scrobble_data_task.emit_scrobble_ui_update_signals.connect(self.__emit_scrobble_ui_update_signals)
    load_additional_scrobble_data_task.finished.connect(self.__recent_scrobbles_done_loading)

    # Add task to global thread pool and run
    QtCore.QThreadPool.globalInstance().start(load_additional_scrobble_data_task)

  def __recent_scrobbles_done_loading(self):
    self.__scrobbles_with_additional_data_count += 1

    if self.__scrobbles_with_additional_data_count == self.__INITIAL_SCROBBLE_HISTORY_COUNT:
      self.__should_show_loading_indicator = False
      self.should_show_loading_indicator_changed.emit()

  def __emit_scrobble_ui_update_signals(self, scrobble):
    # Update scrobble data in details pane view if it's currently showing (when the selected scrobble is the one being updated)
    if scrobble.equals(self.selected_scrobble):
      self.selected_scrobble_changed.emit()
    
    # If scrobble is the current track, update current scrobble sidebar item to reflect actual is_loved status
    if scrobble.equals(self.__current_scrobble):
      self.current_scrobble_data_changed.emit()
    
    # Also update image of history item if scrobble is already in history (check every item for find index)
    for i, history_item in enumerate(self.scrobble_history):
      # TODO: Make separate signal that only updates is_loved data because the other data shown doesn't change
      if scrobble.equals(history_item):
        self.scrobble_album_image_changed.emit(i)
        self.scrobble_lastfm_is_loved_changed.emit(i)
        # No break just in case track is somehow scrobbled twice before image loads

  # --- Qt Properties ---
  
  # Make data about the currently playing track available to the view
  currentScrobbleData = QtCore.Property('QVariant', get_current_scrobble_data, notify=current_scrobble_data_changed)

  # Make current scrobble percentage available to the view
  currentScrobblePercentage = QtCore.Property(float, get_current_scrobble_percentage, notify=current_scrobble_percentage_changed)

  isUsingMockPlayerPlugin = QtCore.Property(bool, get_is_using_mock_player_plugin, notify=is_using_mock_player_plugin_changed)

  # Make the current scrobble index available to the view
  selectedScrobbleIndex = QtCore.Property(int, get_selected_scrobble_index, set_selected_scrobble_index, notify=selected_scrobble_index_changed)

  # TODO: Move this to an ApplicationViewModel
  miniMode = QtCore.Property(bool, get_is_in_mini_mode, notify=is_in_mini_mode_changed)

  shouldShowLoadingIndicator = QtCore.Property(bool, lambda self: self.__should_show_loading_indicator, notify=should_show_loading_indicator_changed)