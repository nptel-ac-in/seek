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

var KARMA_LIB = process.env.KARMA_LIB;

files = [
  JASMINE,
  JASMINE_ADAPTER,
  'https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js',
  KARMA_LIB + '/jasmine-jquery-1.5.2.js',

  // Test files
  'tests/unit/javascript_tests/modules_certificate/*.js',

  // Test resources
  {
    pattern: 'tests/unit/javascript_tests/modules_certificate/*.html',
    watched: true,
    included: false,
    served: true
  },

  // Files to test
  'modules/certificate/course_settings.js'
];

exclude = [
  '**/karma.conf.js'
];

browsers = ['PhantomJS'];
singleRun = true;