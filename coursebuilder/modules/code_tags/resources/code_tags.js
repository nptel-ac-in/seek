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

CodeMirror.modeURL = "/modules/code_tags/codemirror/mode/%N/%N.js";
$('code.codemirror-container-readonly').each(function() {
  var code = $(this).text();
  $(this).empty();
  var cmInstance = CodeMirror(this, {
    value: code,
    lineNumbers: true,
    readOnly: true
  });
  var mode = $(this).data('mode');
  cmInstance.setOption('mode', mode);
  CodeMirror.autoLoadMode(cmInstance, mode);
});
