from abc import ABCMeta, abstractmethod

from PySide2 import QtCore

from datatypes import MediaPlayerState

# class FinalMeta(QtCore.QObject, ABCMeta):
#   pass

class MediaPlayerPlugin(QtCore.QObject):
  __metaclass__ = ABCMeta

  '''Emitted when the media player is not playing anything'''
  stopped = QtCore.Signal()

  '''Emitted when the media player is paused with an updated state'''
  paused = QtCore.Signal(MediaPlayerState)
  
  '''Emitted when the media player is playing with an updated state'''
  playing = QtCore.Signal(MediaPlayerState)

  def __init__(self) -> None:
    QtCore.QObject.__init__(self)

  @abstractmethod
  def get_player_position(self) -> float:
    '''Get the media players current playback position in secoonds'''
    
    pass

  @abstractmethod
  def is_open(self) -> bool:
    '''Return whether or not the media player is open'''
    
    pass

  @abstractmethod
  def force_initial_notification(self) -> None:
    '''Get a MediaPlayerState object without any system notification from the media player'''

    pass