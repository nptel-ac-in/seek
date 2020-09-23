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

basePath = '../../../..';

files = [
  JASMINE,
  JASMINE_ADAPTER,

  // Test files
  'tests/unit/javascript_tests/modules_oeditor/*.js',

  // Files to test
  'modules/oeditor/oeditor.js',
  'modules/oeditor/popup.js',
  'modules/oeditor/rte.js'
];

exclude = [
  '**/karma.conf.js'
];

browsers = ['PhantomJS'];
singleRun = true;