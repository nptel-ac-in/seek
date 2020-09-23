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

// Defer execution to jQuery ready.
jQuery(function($) {
  // Resize child frames to the size of their contents every 75ms.
  setInterval(function() {
    $('iframe.gcb-needs-resizing').each(function(elem) {
      try {
        $(this).height($(this).contents().height());
      } catch(error) {
        // Eat errors, which are likely caused by the iframe child changing to
        // a domain that makes cross-frame operations impossible.
        // TODO(johncox): add a renderer layer to patch over this for
        // iframes containing ContentChunk payloads (for example, by making all
        // links open in a target=_blank).
      }
    });
  }, 75);
});
