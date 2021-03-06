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

describe("questionnaire library", function () {

  beforeEach(function () {
    jasmine.getFixtures().fixturesPath = "base/";
    loadFixtures("tests/unit/javascript_tests/modules_questionnaire/" +
        "fixture.html");
    this.payload = JSON.parse(readFixtures(
        "tests/unit/javascript_tests/modules_questionnaire/form_data.json"));
    this.button = $("button.questionnaire-button");
    this.form = $("#standard-form form");
    this.key = "This-form-id"
    cbShowMsg = jasmine.createSpy("cbShowMsg");
    cbShowMsgAutoHide = jasmine.createSpy("cbShowMsgAutoHide");
    $.ajax = jasmine.createSpy("$.ajax");
    gcbTagEventAudit = jasmine.createSpy("gcbTagEventAudit");
  });

  it("populates the form from JSON blob", function() {
    setFormData(this.payload.form_data || {}, this.key);

    expect($(this.form).find("[name='fname']").val()).toEqual("A. Student");
    expect($(this.form).find("[name='age']").val()).toEqual("100");
    expect($(this.form).find("[name='date']").val()).toEqual("2014-09-17");
    expect($(this.form).find("[name='color']").val()).toEqual("#000000");
    expect($(this.form).find("[name='week']").val()).toEqual("2014-W37");
    expect($(this.form).find("[name='datetime']").val())
        .toEqual("test-date-time");
    expect($(this.form).find("[name='local']").val())
        .toEqual("2014-09-11T14:21");
    expect($(this.form).find("[name='month']").val()).toEqual("2014-09");
    expect($(this.form).find("[name='email']").val())
        .toEqual("test@example.com");
    expect($(this.form).find("[name='range']").val()).toEqual("5");
    expect($(this.form).find("[name='search']").val()).toEqual("test-search");
    expect($(this.form).find("[name='url']").val())
        .toEqual("http://www.google.com");
    expect($(this.form).find("[name='tel']").val()).toEqual("012334545");
    expect($(this.form).find("[name='time']").val()).toEqual("12:02");
    expect($(this.form).find("[name='select']").val()).toEqual("Apple");
    expect($(this.form).find("[name='radio']").val()).toEqual("male");
    expect($(this.form).find("[name='datalist']").val()).toEqual("Peas");
    expect($(this.form).find("[name='textarea']").val()).toEqual("A student.");
    expect($(this.form).find("[name='checkbox']").val())
        .toEqual("Bike" || "Walk");
  });

  it("executes the correct logic when data status is 200", function() {
    var postMessageDiv = $(this.button).parent().find("div.post-message");

    setFormData(this.payload.form_data || {}, this.key);
    expect(postMessageDiv.hasClass("hidden")).toBe(true);
    var data = ')]}\' {"status": 200, "message": "Response submitted"}';
    onAjaxPostFormData(data, this.button);
    expect(cbShowMsgAutoHide).toHaveBeenCalled();
    expect(postMessageDiv.hasClass("hidden")).toBe(false);
  });

  it("shows an error message on failure", function() {
    var postMessageDiv = $(this.button).parent().find("div.post-message");
    setFormData(this.payload.form_data || {}, this.key);
    var data = ')]}\' {"status": 403, "message": "Permission denied"}';
    onAjaxPostFormData(data, this.button);
    expect(cbShowMsg).toHaveBeenCalled();
    expect(postMessageDiv.hasClass("hidden")).toBe(true);
  });

  it("Send the right AJAX data", function() {
    setFormData(this.payload.form_data || {}, this.key);
    onSubmitButtonClick(this.key, "my-xsrf-token", this.button);

    expect($.ajax).toHaveBeenCalled();
    expect($.ajax.mostRecentCall.args.length).toBe(1);
    var ajaxArg = $.ajax.mostRecentCall.args[0];
    expect(ajaxArg.type).toBe("POST");
    expect(ajaxArg.url).toBe("rest/modules/questionnaire");
    expect(ajaxArg.dataType).toBe("text");
    expect(ajaxArg.data.request).toBe(JSON.stringify({
      xsrf_token: "my-xsrf-token",
      key: this.key,
      payload: {
        form_data: this.payload.form_data
      }
    }));

    expect(gcbTagEventAudit).toHaveBeenCalledWith({
      key: this.key,
      form_data: this.payload.form_data
    }, "questionnaire");
  });

  it("can disable the form", function() {
    setFormData(this.payload.form_data || {}, this.key);
    this.form.find('input,select,textarea').each(function() {
      expect($(this).prop("disabled")).toBe(false);
    });
    disableForm(this.button, this.key);
    this.form.find('input,select,textarea').each(function() {
      expect($(this).prop("disabled")).toBe(true);
    });
  });
});
