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

// GoogleDriveTagParent refers to top, but karma tests run inside of an iframe.
// Bind top to window so this difference doesn't cause breakage.
// TODO(johncox): get rid of this when we write real tests using iframs.
top = window;

describe('core tags module', function() {

  window.cb_global = {
    schema: {
      properties: {
        'document-id': {
          '_inputex': {
            'api-key': 'api-key-value',
            'client-id': 'client-id-value',
            'type-id': 'type-id-value',
            'xsrf-token': 'xsrf-token-value'
          }
        }
      }
    }
  };
  window.disableAllControlButtons = function() {};
  window.enableAllControlButtons = function() {};

  describe('parent and child frame tests', function() {
    // TODO(johncox): tests.
  });

});
