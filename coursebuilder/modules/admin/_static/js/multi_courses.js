$(function() {

  var AddMultiCoursePanel = function(title, xsrfToken, email) {
    this._xsrfToken = xsrfToken;
    this._documentBody = $(document.body);
    this._lightbox = new window.gcb.Lightbox();
    this._form = $(
        '<div class="add-course-panel">' +
        '  <h2 class="title"></h2>' +
        '  <div class="form-row">' +
        '    <label>Courses (urlpart, admin email, title)</label>' +
        '    <textarea name="all_courses"' +
        '        placeholder="urlpart, admin email, title"></textarea>' +
        '  </div>' +
        '  <div class="controls">' +
        '    <button class="gcb-button save-button">OK</button>' +
        '    <button class="gcb-button cancel-button">Cancel</button>' +
        '  </div>' +
        '  <div class="spinner hidden">' +
        '    <div class="background"></div>' +
        '    <span class="icon spinner md md-settings md-spin"></span>' +
        '  </div>' +
        '</div>');
    this._form.find('.title').text(title);
    this._all_courses = this._form.find('[name="all_courses"]')
    this._form.find('.save-button').click(this._save.bind(this));
    this._form.find('.cancel-button').click(this._close.bind(this));
    this._spinner = this._form.find('.spinner');

  };
  AddMultiCoursePanel.prototype.open = function() {
    this._lightbox
      .bindTo(this._documentBody)
      .setContent(this._form)
      .show();
  };
  AddMultiCoursePanel.prototype._save = function() {
    this._showSpinner();
    var payload = {
      type: 'add-multi-course',
      content: this._all_courses.val()
    };
    var request = {
      xsrf_token: this._xsrfToken,
      payload: JSON.stringify(payload)
    };
    $.ajax('/rest/courses/item', {
      method: 'PUT',
      data: {request: JSON.stringify(request)},
      dataType: 'text',
      error: this._saveError.bind(this),
      success: this._saveSuccess.bind(this),
      complete: this._saveComplete.bind(this)
    });
  };
  AddMultiCoursePanel.prototype._showSpinner = function() {
    this._spinner.removeClass('hidden');
  };
  AddMultiCoursePanel.prototype._hideSpinner = function() {
    this._spinner.addClass('hidden');
  };
  AddMultiCoursePanel.prototype._close = function() {
    this._lightbox.close();
  };
  AddMultiCoursePanel.prototype._saveError = function() {
    cbShowMsg('Something went wrong. Please try again.');
  };
  AddMultiCoursePanel.prototype._saveSuccess = function(data) {
    data = window.gcb.parseJsonResponse(data);
    console.log(data);
    if (data.status != 200) {
      var message = data.message || 'Something went wrong. Please try again.';
      cbShowMsg(message);
      return;
    }
    window.location.reload();
  };
  AddMultiCoursePanel.prototype._saveComplete = function() {
    this._hideSpinner();
  };

  function addMultiCourse() {
    var xsrfToken = $('#add_multiple_course').data('xsrfToken');
    var email = $('#add_multiple_course').data('email');
    new AddMultiCoursePanel('Add Multiple Course...', xsrfToken, email).open();
  }

  function bind() {
    $('#add_multiple_course').click(addMultiCourse);
  }
  function init() {
    bind();
  }

  init();
});
