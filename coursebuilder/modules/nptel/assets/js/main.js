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

function submitOnEnter(evt, input) {
  var keyCode = evt.keyCode;
  if (keyCode == 13) {
    $(input).closest('form').submit();
    return false;
  }
  else {
    return true;
  }
}
$(function() {
  $('input.gcb-search-box').keypress(function(evt) {
    submitOnEnter(evt, 'input.gcb-search-box');
  });
  $('.gcb-search-result.youtube img').click(function() {
    if ($(this).hasClass('shown')) {
      $(this).addClass('hidden').removeClass('shown');
    }
    $(this).siblings('iframe').addClass('shown').removeClass('hidden');
  });
});

function element(id) {
  return document.getElementById(id);
}

// Update a particular HTML element with a new value
function updateInnerHTML(elmId, value) {
  element(elmId).innerHTML = value;
}

function updateValue(elmId, value) {
  element(elmId).value = value;
}

function toggleSubUnitNavBar(id) {
  var bar = element(id);
  if (bar) {
    if (bar.className == 'subunit_navbar_other') {
      bar.className = 'subunit_navbar_current';
    } else {
      bar.className = 'subunit_navbar_other';
    }
  }
}

function formatRetreivedQuestions(top_el, response, forum_id, forum_domain) {
  var response_dict = eval(response);
  top_el.innerHTML = '';
  var questions_list = response_dict['questions'];
  for (var question_index in questions_list) {
    var question = questions_list[question_index];
    var question_link = document.createElement('a');
    question_link.setAttribute('href',
        'https://groups.google.com' + forum_domain +
        '/forum/?fromgroups#searchin/' + forum_id + '/' + question['key']);
    question_link.setAttribute('target', '_blank');
    question_link.setAttribute('onClick',
        'incCount("' + question['key'] + '"); return true;');
    question_link_text = '[' + question['time'] + '] ' + question['question'];
    var linkTextNode = document.createTextNode(question_link_text);
    question_link.appendChild(linkTextNode);

    var question_node = document.createElement('div');
    question_node.setAttribute('class', 'gcb-retrieved-question');
    question_node.setAttribute('id', 'retrieved-question-' + question_index);
    question_node.appendChild(question_link);
    top_el.appendChild(question_node);
  }
}

// Client functions that call a server rpc and provide callbacks
function submitQuestionClient(resource_id) {
  data = {
    'video_timestamp': getCurrentVideoTimeInSecs(),
    'question': element('doubtQuestionField').value,
    'short_description': element('doubtSummaryField').value,
    'resource_id': resource_id
  };
  ajax_server.submit_question(data);
}

function onSubmitSuccess() {
  ytplayer.playVideo();
  updateValue('doubtQuestionField', '');
  updateValue('doubtSummaryField', '');
  element('doubtForm').style.display = 'none';
  element('lessonDoubtButton').style.display = 'table';
  element('retrievedQuestions').style.display = 'none';
}

function cancel() {
  ytplayer.playVideo();
  element('doubtForm').style.display = 'none';
  element('lessonDoubtButton').style.display = 'table';
  element('retrievedQuestions').style.display = 'none';
}

function retrieveQuestions(resource_id) {
  ytplayer.pauseVideo();
  ajax_server.relevant_questions({
      'video_timestamp': getCurrentVideoTimeInSecs(),
      'resource_id': resource_id});
}

function retrieveAll() {
  element('retrievedQuestions').innerHTML = '';
  ytplayer.pauseVideo();
  ajax_server.all_questions();
}

function viewDoubtForm() {
  ytplayer.pauseVideo();
  element('retrievedQuestions').style.display = 'none';
  element('doubtForm').style.display = 'inline';
}

function incCount(question_id) {
  ajax_server.inc_count({'key': question_id});
}

// This function is called when an error is thrown by the player
function onPlayerError(errorCode) {}

var ytplayer;
var timer;
var timer2;
var videoId;
var startTime = [];
var endTime = [];
function getCurrentVideoTimeInSecs() {
  duration = '0';
  if (ytplayer) {
    duration = (ytplayer.getCurrentTime()).toString();
    decimallocation = duration.indexOf('.');
    if (decimallocation != 0) {
      duration = duration.substr(0, decimallocation);
    }
  }
  return duration;
}

function onPlayerStateChange(event) {
  if (event.data == YT.PlayerState.PLAYING) {
     timer = setInterval(recordWatchDuration, 500);
     timer2 = setInterval(sendWatchDuration, 1000);
     if (startTime.length != endTime.length) {
       startTime[startTime.length - 1] = parseInt(ytplayer.getCurrentTime());
     } else {
       startTime[startTime.length] = parseInt(ytplayer.getCurrentTime());
     }
     element('retrievedQuestions').style.display = 'none';
     element('doubtForm').style.display = 'none';
     element('lessonDoubtButton').style.display = 'table';
  } else {
     sendWatchDuration();
     clearInterval(timer);
     clearInterval(timer2);
  }
}

function recordWatchDuration() {
  endTime[startTime.length - 1] = parseInt(ytplayer.getCurrentTime());
}

function sendWatchDuration() {
  if (startTime.length > 0) {
    ajax_server.record_video_watchtime({
      'start': startTime,
      'end': endTime,
      'duration': ytplayer.getDuration(),
      'resource_id': videoId});
  }
}

function loadIFramePlayer(vID, div_id) {
  ytplayer = new YT.Player(div_id, {
  height: '500px',
  width: '100%',
  videoId: vID,
  events: {
    'onStateChange': onPlayerStateChange
    }
  });
  videoId = vID;
}

installFunction('student/progress', 'get_progress', onProgressSuccess, null);

COMPLETED = 'Completed';
function setProgressState(el, state) {
  if (!el) return;
  if (state == 2) {
    el.src = '/modules/nptel/assets/img/completed.png';
    el.alt = COMPLETED;
    el.title = COMPLETED;
  } else if (state == 1) {
    el.src = '/modules/nptel/assets/img/in_progress.png';
    el.alt = 'In Progress';
    el.title = 'In Progress';
  }
}

function isUnitUncomplete(unit) {
  status_markers = unit.getElementsByClassName('gcb-progress-icon');
  for (var el = 0; el < status_markers.length; ++el) {
    var marker_el = status_markers[el];
    if (marker_el.alt != COMPLETED) return true;
  }
  return false;
}

function showFirstUncompleteUnit(el) {
  var unit_nodes = el.getElementsByClassName('unit_navbar');
  for (var unit_index in unit_nodes) {
    var unit = unit_nodes[unit_index];
    if (isUnitUncomplete(unit)) {
      toggleSubUnitNavBar('sub' + unit.getAttribute('id'));
      return;
    }
  }
}

function onProgressSuccess(response) {
  var response_dict = eval(response);
  for (var uid in response_dict) {
    var state = response_dict[uid];
    if (typeof state == 'object') {
      for (var t in state) {
        var el = element('progress-state-' + t + '-' + uid);
        setProgressState(el, state[t]);
      }
    } else {
      var el = element('progress-state-' + uid);
      setProgressState(el, state);
    }
  }
  var open_units = document.getElementsByClassName('subunit_navbar_current');
  if (!open_units || open_units.length == 0) {
    var navbar = element('course_navbar');
    if (navbar) {
      showFirstUncompleteUnit(navbar);
    }
  }
}
function showPopupDiv(id) {
  divb = element(id);
  divb.className = 'visiblePopupDiv gcb-aside';
}
function hidePopupDiv(id) {
  divb = element(id);
  divb.className = 'invisiblePopupDiv';
}

if (!String.prototype.trim) {
 String.prototype.trim = function() {
  return this.replace(/^\s+|\s+$/g,'');
 }
}


showMenu = function() {
  var div = document.getElementById('logout-div');
  div.style.display = 'inline-block'
}
hideMenu = function() {
  var div = document.getElementById('logout-div');
  div.style.display = 'none'
}
