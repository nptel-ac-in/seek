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

var tag = document.getElementsByName('tag')[0];
if (tag) {
  tag.onchange = function(event) {
    var value = cb_global.form.getValue();
    value.attributes = {};
    window.parent.frameProxy.setValue(value);

    var tagName = tag.options[tag.selectedIndex].value;
    window.location = getAddCustomTagUrl(cb_global, tagName,
        window.parent.frameProxy.getContext().excludedCustomTags);
  };

  // When adding elements of a list, be sure to refresh the page height.
  Y.all('.inputEx-List-link').on('click', function() {
    window.parent.frameProxy.refresh();
    var links = Y.all('.inputEx-List-link');
    if (links.size() >= 2) {
      links.item(links.size() - 2).on('click', function() {
        window.parent.frameProxy.refresh();
      });
    }
  });
}
document.getElementById('cb-oeditor-form').action = 'javascript: void(0)';
