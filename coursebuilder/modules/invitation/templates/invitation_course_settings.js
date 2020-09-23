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
  // Hide the other invitation inputs when the "Enable Invitations checkbox"
  // is unchecked.

  var checkbox = $("div.invitation-enable > input[type=\"checkbox\"]");

  function updateInvitationFields() {
    if (checkbox.prop("checked")) {
      $(".invitation-data").parent().show();
    } else {
      $(".invitation-data").parent().hide();
    }
  }

  function init() {
    checkbox.click(updateInvitationFields);
    updateInvitationFields();
  }

  init();
});
