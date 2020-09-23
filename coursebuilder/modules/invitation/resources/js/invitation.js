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
  var XSRF_TOKEN = $("#invitation-div").data("xsrf-token");
  // XSSI prefix. Must be kept in sync with models/transforms.py.
  var XSSI_PREFIX = ")]}'";

  function parseJson(s) {
    return JSON.parse(s.replace(XSSI_PREFIX, ''));
  }

  function onSendButtonClick() {
    var request = JSON.stringify({
      "xsrf_token": XSRF_TOKEN,
      "payload": {
        "emailList": $("#email-list").val()
      }
    });
    $.ajax({
      type: "POST",
      url: "rest/modules/invitation",
      data: {"request": request},
      dataType: "text",
      success: onAjaxPostSuccess,
    });
  }

  function onAjaxPostSuccess(data) {
    var data = parseJson(data);
    if (data.status != 200) {
      cbShowMsg(data.message);
    } else {
      cbShowMsgAutoHide(data.message);
    }
  }

  function init() {
    $("#send-button").click(onSendButtonClick);
  }

  init();
});
