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
      'Note: Deleting translations will take several seconds, ' +
      'and may time out.  If this happens, you can try ' +
      'deleting fewer languages at a time, or use the command ' +
      'line tool.  See .../modules/i18n_dashboard/jobs.py for ' +
      'complete instructions and sample command lines.');
  $('#cb-oeditor-form > fieldset')
      .append('<hr>')
      .append($('<div/>').text(notes));


  var saveCbShowMsg = cbShowMsg;
  cb_global.onSaveClick = function() {
    do_delete = confirm('Really delete translations for these languages?');
    if (do_delete) {
      // Here, we can't change the "saving..." message in OEditor, but
      // we can at least ensure that it disappears briskly.
      cbShowMsg = function() { ; }
    }
  }

  cb_global.onSaveComplete = function() {
    cbShowMsg = saveCbShowMsg;
  }
});
