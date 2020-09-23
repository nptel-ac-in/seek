/**
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

function gcbTagHtml5TrackVideo(instanceId) {
  var index = 0;
  var video = $('#' + instanceId)[0];
  var eventLogger = function(event) {
    var dataDict = {
      'instance_id': instanceId,
      'event_id': index,
      'position': video.currentTime,
      'rate': video.playbackRate,
      'default_rate': video.defaultPlaybackRate,
      'event_type': event.type
   }
    gcbTagEventAudit(dataDict, 'html5video-event');
    index += 1;
  };

  $(video).on([
    'loadstart',  // The user agent begins looking for media data
    'loadeddata', // Can render at the current position for the first time.
    'abort',  // The user agent stops fetching [...] but not due to an error.
    'error',  // An error occurs while fetching the media data.
    'play',  // Play requested.
    'pause',  // Pause requested.
    'playing',  // Playback is ready to start after pause or delay
    'waiting',  // Playback stopped because the next frame is not available
    // 'seeking' causes far too many events when position wiper is moved.
    'seeked',  // The current playback position was changed.
    'ended',  // The end of the media resource was reached.
    'ratechange',  // Playback rate or default rate have changed.
    ].join(' '), eventLogger);

}
