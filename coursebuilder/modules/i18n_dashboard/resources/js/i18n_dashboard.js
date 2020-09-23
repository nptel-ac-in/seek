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

// XSSI prefix. Must be kept in sync with models/transforms.py.
var xssiPrefix = ")]}'";

var xsrfToken = $("table.i18n-progress-table").data("isTranslatableXsrfToken");

/**
 * Parses JSON string that starts with an XSSI prefix.
 */
function parseResponse(s) {
  return JSON.parse(s.replace(xssiPrefix, ''));
}

function onTranslatableCheckboxClicked(evt) {
  var target = $(evt.target);
  var isChecked = target.prop("checked");
  var request = JSON.stringify({
    "xsrf_token": xsrfToken,
    "payload": {
      "resource_key": target.closest("tr").data("resource-key"),
      "value": isChecked
    }
  });

  $.ajax({
    url: "rest/modules/i18n_dashboard/is_translatable",
    type: "POST",
    data: {"request": request},
    dataType: "text",
    success: onTranslatableCheckboxResponse
  });

  if (isChecked) {
    target.closest("tr").removeClass('not-translatable');
  } else {
    target.closest("tr").addClass('not-translatable');
  }
}

function onTranslatableCheckboxResponse(data) {
  data = parseResponse(data);
  if (data.status != 200) {
    cbShowAlert(data.message);
    return;
  }
}

function bind() {
  $("input.is-translatable").click(onTranslatableCheckboxClicked);
}

bind();