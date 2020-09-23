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

$(function() {
  var notes = (
      'Note: Downloading translation files will take several seconds, ' +
      'and may time out.  If this happens, you can try ' +
      'exporting fewer languages at a time, or use the command ' +
      'line tool.  See .../modules/i18n_dashboard/jobs.py for ' +
      'complete instructions and sample command lines.');
  $('#cb-oeditor-form > fieldset')
      .append('<hr>')
      .append($('<div/>').text(notes));


  cb_global.onSaveComplete = function() {
    cbShowMsgAutoHide(
        'Download of .zip file started; open your browser\'s ' +
        'Downloads window to track progress.')

    var requestData = JSON.stringify({
      'payload': JSON.stringify(cb_global.form.getValue()),
      'xsrf_token': cb_global.xsrf_token
    });

    var f = document.createElement('form');
    f.method = 'POST';
    f.action = cb_global.save_url;
    var i = document.createElement('input');
    i.name = 'request';
    i.setAttribute('value', requestData);
    f.appendChild(i);
    f.submit();
  };
});
