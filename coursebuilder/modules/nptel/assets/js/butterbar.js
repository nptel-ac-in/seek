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

function ButterBar(popup, message, close) {
  this.popup = popup;
  this.message = message;
  this.close = close;
}
ButterBar.prototype.showMessage = function(text) {
  this.message.textContent = text;  // FF, Chrome
  this.message.innerText = text;    // IE
  if (! $(this.popup).hasClass("shown")) {
    $(this.popup).addClass("shown");
  }
  if (this.close != null) {
    this.close.onclick = cbHideMsg;
  }
  window.onscroll = ButterBar.keepInView;
};
ButterBar.prototype.hide = function() {
  if ($(this.popup).hasClass("shown")) {
    $(this.popup).removeClass("shown");
  }
};
ButterBar.prototype.setCloseButtonVisible = function(visible) {
  if (visible) {
    $(this.close).css('display', null);
  } else {
    $(this.close).css('display', 'none');
  }
}
ButterBar.getButterBar = function() {
  return new ButterBar(document.getElementById("gcb-butterbar-top"),
    document.getElementById("gcb-butterbar-message"),
    document.getElementById("gcb-butterbar-close"));
};
function cbShowMsg(text) {
  var butterBar = ButterBar.getButterBar();
  butterBar.setCloseButtonVisible(true);
  butterBar.showMessage(text);
}
function cbShowAlert(text) {
  // An alert should not be closed; hide the close button
  var butterBar = ButterBar.getButterBar();
  butterBar.setCloseButtonVisible(false);
  butterBar.showMessage(text);
}
function cbHideMsg() {
  ButterBar.getButterBar().hide();
}
ButterBar.keepInView = function() {
  var popup = ButterBar.getButterBar().popup;
  var container = popup.parentElement;

  container.style.top = null;
  $(container).removeClass('fixed');

  var offset = $(popup).offset().top;
  if (offset - $(document).scrollTop() <= 10) {
    $(container).addClass('fixed');
    container.style.top = (10 - popup.offsetTop) + "px";
  }
};
