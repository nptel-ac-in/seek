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

describe('ButterBar', function() {
  var popup, message, close, butterBar;

  beforeEach(function() {
    jasmine.getFixtures().fixturesPath = 'base/';
    loadFixtures(
        'tests/unit/javascript_tests/assets_lib_butterbar/fixture.html');
    popup = $('#gcb-butterbar-top').get(0);
    message = $('#gcb-butterbar-message').get(0);
    close = $('#gcb-butterbar-close').get(0);
    butterBar = new ButterBar(popup, message, close);
  });

  it('can display text', function() {
    butterBar.showMessage('Hello, World');
    expect(message.textContent).toBe('Hello, World');
    expect(message.innerText).toBe('Hello, World');
    expect(popup.className).toContain('shown');
  });
  it('can be hidden', function() {
    butterBar.hide();
    expect(popup.className).not.toContain('shown');
    butterBar.showMessage('Hello, World!');
    butterBar.hide();
    expect(popup.className).not.toContain('shown');
  });
  it('hides automatically when called with cbShowMsgAutoHide', function() {
    window.clearTimeout = jasmine.createSpy('window.clearTimeout');
    window.setTimeout = jasmine.createSpy('window.setTimeout').andCallFake(
      cbHideMsg);
    cbShowMsgAutoHide('Hello, World!');
    expect(window.clearTimeout).not.toHaveBeenCalled();
    expect(window.setTimeout).toHaveBeenCalledWith(cbHideMsg, 5000);
    expect(popup.className).not.toContain('shown');
  });
  it('restarts timeout when cbShowMsgAutoHide is called twice', function() {
    window.clearTimeout = jasmine.createSpy('window.clearTimeout');
    window.setTimeout = jasmine.createSpy('window.setTimeout').andReturn(101);
    cbShowMsgAutoHide('Hello, World!');
    cbShowMsgAutoHide('Hello, World!');
    expect(window.clearTimeout).toHaveBeenCalledWith(101);
    expect(window.setTimeout.calls.length).toBe(2);
  });
});
