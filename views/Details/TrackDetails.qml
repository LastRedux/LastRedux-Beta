import QtQuick 2.14
import Qt.labs.platform 1.0

import '../../shared/components'
import '../../util/helpers.js' as Helpers

PictureBackground {
  id: root

  property bool isInMiniMode
  property bool isCurrentlyScrobbling
  property bool isTrackNotFound
  property string title
  property var lastfmUrl
  
  // var to support undefined
  property var lastfmGlobalListeners 
  property var lastfmGlobalPlays 
  property var lastfmPlays

  // var to support lists
  property var lastfmTags

  property string artistName
  property var artistLastfmUrl

  property var albumTitle
  property var albumLastfmUrl
  property url albumImageUrl

  source: albumImageUrl

  height: Math.max(albumImageView.y + albumImageView.height, tags.y + tags.height) + 30

  // --- Album Image ---

  Picture {
    id: albumImageView

    source: albumImageUrl

    width: 181

    anchors {
      top: parent.top
      left: parent.left

      margins: 30
    }
  }

  // --- Track Name ---

  PlaybackIndicator {
    id: playbackIndicator

    isLarge: true
    visible: isCurrentlyScrobbling && !isInMiniMode

    anchors {
      top: albumImageView.top
      left: albumImageView.right

      topMargin: 10
      leftMargin: 20
    }
  }

  Link {
    id: trackNameView
    
    elide: Text.ElideRight
    maximumLineCount: 2
    wrapMode: Text.Wrap

    isShadowEnabled: false
    style: kTitlePrimary
    text: title
    address: lastfmUrl

    anchors {
      top: playbackIndicator.top
      right: parent.right
      left: playbackIndicator.visible ? playbackIndicator.right : playbackIndicator.left

      rightMargin: 30
      leftMargin: playbackIndicator.visible ? 10 : 0
    }
  }

  // --- Artist Name ---

  Link {
    id: artistNameView

    elide: Text.ElideRight
    isShadowEnabled: false
    text: artistName
    address: artistLastfmUrl

    anchors {
      top: trackNameView.bottom
      right: trackNameView.right
      left: playbackIndicator.left

      topMargin: 5
    }
  }

  // --- Album Name ---
  
  Item {
    id: albumView
    visible: !!albumTitle

    height: albumTitleLeadingText.height

    anchors {
      top: artistNameView.bottom
      left: playbackIndicator.left
      right: trackNameView.right

      topMargin: 5
    }

    Label {
      id: albumTitleLeadingText

      style: kBodyPrimary
      isShadowEnabled: false
      text: 'from'

      anchors {
        left: parent.left
      }
    }

    Link {
      id: albumTitleView

      elide: Text.ElideRight
      isShadowEnabled: false
      text: albumTitle
      address: albumLastfmUrl

      // Position to the right of leading text
      anchors {
        right: parent.right
        left: albumTitleLeadingText.right
        
        leftMargin: 3
      }
    }
  }

  // --- Plays ---
  
  Flow {
    id: statistics
    
    spacing: 20
    visible: !isTrackNotFound

    anchors {
      top: albumView.visible ? albumView.bottom : artistNameView.bottom
      right: trackNameView.right
      left: playbackIndicator.left

      topMargin: 10
    }
    
    Statistic {
      isShadowEnabled: false
      title: 'Listeners'
      value: lastfmGlobalListeners === 0 ? 0 : (lastfmGlobalListeners || '---')
    }

    Statistic {
      isShadowEnabled: false
      title: 'Plays'
      value: lastfmGlobalPlays === 0 ? 0 : (lastfmGlobalPlays || '---')
    }

    Statistic {
      isShadowEnabled: false
      title: lastfmPlays === 1 ? 'Play in Library' : 'Plays in Library'
      value: lastfmPlays === 0 ? 0 : (lastfmPlays || '---')
      
      shouldAbbreviate: false
    }
  }

  // --- Tags ---
  
  Flow {
    id: tags

    spacing: 8
    
    anchors {
      top: statistics.bottom
      right: trackNameView.right
      left: playbackIndicator.left

      topMargin: 15
    }
    
    Repeater {
      model: lastfmTags

      delegate: Tag {
        name: modelData.name
        address: modelData.url
      }
    }
  }
}