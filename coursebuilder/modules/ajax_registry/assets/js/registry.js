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

/**
 * @fileoverview Utility to add AJAX handler to pages.
 */

function element(id) {
  return document.getElementById(id);
}

// Update a particular HTML element with a new value
function updateInnerHTML(elmId, value) {
  element(elmId).innerHTML = value;
}

function updateValue(elmId, value) {
  element(elmId).value = value;
}

function getSelectValue(id) {
  var selectEl = element(id);
  return selectEl.options[selectEl.selectedIndex].value;
}


function my_error( jqXHR,  textStatus,  errorThrown ){
console.log(textStatus);
console.log(errorThrown);
}

// Server object that will contain the callable methods
ajax_server = {};

// Adds a stub function that will pass the arguments to the AJAX call
//
// functionName: the name of the server's AJAX function to call
// callback: function to run after completion of ajax request
// xsrf_token: XSRF token to be passed for POST requests. If this is not present
// then we assume that the ajax request is a GET request.
function installFunction(end_point, functionName, callback, xsrf_token) {
  ajax_server[functionName] = function(opt_arg) {
    var type = xsrf_token ? 'POST' : 'GET';
    var async = (callback != null);

    var data = {};
    data.action = functionName;
    if (xsrf_token) {
      data.xsrf_token = xsrf_token;
    }
    data.time = new Date().getTime();
    if (opt_arg) {
      $.extend(data, opt_arg);
    }
    $.ajax(end_point, {
      type: type,
      async: async,
      data: data,
      dataType: 'json',
      success: callback,
      error: my_error,
    });
  };
}

function noopCallback() {}
