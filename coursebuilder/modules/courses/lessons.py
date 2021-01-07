# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handlers for generating various frontend pages."""

__author__ = 'Saifu Angto (saifu@google.com)'

import copy
import datetime
import urllib
import urlparse
import uuid

from common import crypto
from common import jinja_utils
from common import safe_dom
from common.crypto import XsrfTokenManager

from controllers import utils as controller_utils
from common import utils as common_utils
from models import counters
from models import course_list
from models import courses
from models import custom_modules
from models import models
from models import review as models_review
from models import roles
from models import student_work
from models import transforms
from models import utils
from common import utils as common_utils
from models.config import ConfigProperty
from models.counters import PerfCounter
from models.models import Student
from models.models import StudentProfileDAO
from modules.nptel import timezones
from models.review import ReviewUtils
from models.student_work import StudentWorkUtils
from modules.student_questions import student_questions
from modules import courses as courses_module
from modules.assessments import assessments
from modules.courses import unit_outline
from modules.review import domain
from tools import verify

from google.appengine.ext import db


COURSE_EVENTS_RECEIVED = counters.PerfCounter(
    'gcb-course-events-received',
    'A number of activity/assessment events received by the server.')

COURSE_EVENTS_RECORDED = counters.PerfCounter(
    'gcb-course-events-recorded',
    'A number of activity/assessment events recorded in a datastore.')

ENABLE_HANGOUTS = ConfigProperty(
    'enable_hangouts_on_unit_pages', bool, (
        'Should we show hangout button on unit pages.'),
    True)

EXAM_REGISTRATION_URL = ConfigProperty(
    'exam_registration_url', str, 'External Exam Registration URL',
    default_value="", label="External Exam Registration URL", multiline=False)

UNIT_PAGE_TYPE = 'unit'
ACTIVITY_PAGE_TYPE = 'activity'
ASSESSMENT_PAGE_TYPE = 'assessment'
ASSESSMENT_CONFIRMATION_PAGE_TYPE = 'test_confirmation'

TAGS_THAT_TRIGGER_BLOCK_COMPLETION = ['attempt-activity']
TAGS_THAT_TRIGGER_COMPONENT_COMPLETION = ['tag-assessment']
TAGS_THAT_TRIGGER_HTML_COMPLETION = ['attempt-lesson']


def _get_first_lesson(handler, unit_id):
    """Returns the first lesson in the unit."""
    lessons = handler.get_course().get_lessons(unit_id)
    return lessons[0] if lessons else None


def _get_selected_unit_or_first_unit(handler):
    # Finds unit requested or a first unit in the course.
    u = handler.request.get('unit')
    unit = handler.get_course().find_unit_by_id(u)
    if not unit:
        units = handler.get_course().get_units()
        for current_unit in units:
            if verify.UNIT_TYPE_UNIT == current_unit.type:
                unit = current_unit
                break
    return unit


def _get_selected_or_first_lesson(handler, unit):
    # Find lesson requested or a first lesson in the unit.
    l = handler.request.get('lesson')
    lesson = None
    if not l:
        lesson = _get_first_lesson(handler, unit.unit_id)
    else:
        lesson = handler.get_course().find_lesson_by_id(unit, l)
    return lesson


def extract_unit_and_lesson(handler):
    """Loads unit and lesson specified in the request."""

    unit = _get_selected_unit_or_first_unit(handler)
    if not unit:
        return None, None
    return unit, _get_selected_or_first_lesson(handler, unit)


def get_unit_and_lesson_id_from_url(handler, url):
    """Extracts unit and lesson ids from a URL."""
    url_components = urlparse.urlparse(url)
    query_dict = urlparse.parse_qs(url_components.query)

    if 'unit' not in query_dict:
        return None, None

    unit_id = query_dict['unit'][0]

    lesson_id = None
    if 'lesson' in query_dict:
        lesson_id = query_dict['lesson'][0]
    else:
        lesson_id = _get_first_lesson(handler, unit_id).lesson_id

    return unit_id, lesson_id


def is_progress_recorded(handler, student):
    if student.is_transient:
        return False
    if controller_utils.CAN_PERSIST_ACTIVITY_EVENTS:
        return True
    course = handler.get_course()
    units = handler.get_track_matching_student(student)
    for unit in units:
        if unit.manual_progress:
            return True
        for lesson in course.get_lessons(unit.unit_id):
            if lesson.manual_progress:
                return True
    return False


class CourseHandler(controller_utils.BaseHandler):
    """Handler for generating course page."""

    # A list of callback functions which modules can use to add extra content
    # panels at the bottom of the page. Each function should return a string
    # or a SafeDom node, or return None to indicate it does not want to add
    # any content.
    #
    # Arguments are:
    # - The current application context
    # - The current course
    # - The StudentCourseView governing this student's view of what course
    #   content is accessible.
    # - The current student.  Note that this may be a TransientStudent, but
    #   will not be None.
    EXTRA_CONTENT = []

    @classmethod
    def get_child_routes(cls):
        """Add child handlers for REST."""
        return [(EventsRESTHandler.URL, EventsRESTHandler)]

    def get_user_student_profile(self):
        user = self.personalize_page_and_get_user()
        if user is None:
            student = controller_utils.TRANSIENT_STUDENT
            profile = None
        else:
            student = models.Student.get_enrolled_student_by_user(user)
            profile = models.StudentProfileDAO.get_profile_by_user(user)
            self.template_value['has_global_profile'] = profile is not None
            if not student:
                student = controller_utils.TRANSIENT_STUDENT
        return user, student, profile

    def get(self):
        """Handles GET requests."""
        models.MemcacheManager.begin_readonly()
        profile = None
        try:
            user = self.personalize_page_and_get_user()
            if user is None:
                student = controller_utils.TRANSIENT_STUDENT
            else:
                student = Student.get_enrolled_student_by_user(user)
                profile = StudentProfileDAO.get_profile_by_user_id(
                    user.user_id())
                if self.needs_profile_update(profile):
                    self.redirect('/profile?action=edit&force=true', normalize=False)
                    return
                if self.needs_to_view_announcements(student, self.app_context):
                    self.redirect('/announcements?force=true')
                    return

                self.template_value['has_global_profile'] = profile is not None
                if not student:
                    student = controller_utils.TRANSIENT_STUDENT

            if (student.is_transient and
                not self.app_context.get_environ()['course']['browsable']):
                self.redirect('/preview')
                return

            # If we are on this page due to visiting the course base URL
            # (and not base url plus "/course"), redirect registered students
            # to the last page they were looking at.
            last_location = self.get_redirect_location(student)
            if last_location:
                self.redirect(last_location)
                return

            tracker = self.get_progress_tracker()
            units = self.get_track_matching_student(student)
            self.template_value['units'] = units
            self.template_value['show_registration_page'] = True


            if student and not student.is_transient:
                self.template_value['course_progress'] = (
                    tracker.get_course_progress(student))
            elif user:
                if not profile:
                    profile = StudentProfileDAO.get_profile_by_user_id(
                        user.user_id())
                additional_registration_fields = self.app_context.get_environ(
                    )['reg_form']['additional_registration_fields']
                if profile is not None and not additional_registration_fields:
                    self.template_value['show_registration_page'] = False
                    self.template_value['register_xsrf_token'] = (
                        XsrfTokenManager.create_xsrf_token('register-post'))


            self.template_value['old_browser'] = self.is_old_browser()
            self.template_value['lessons_dict'] = self.get_unit_lessons_dict()
            self.template_value['unit_dict'] = self.get_unit_sub_unit_dict()
            self.template_value['enable_hangouts'] = ENABLE_HANGOUTS.value
            self.template_value['exam_registration_url'] = EXAM_REGISTRATION_URL.value
            self.template_value['transient_student'] = student.is_transient
            self.template_value['progress'] = tracker.get_unit_progress(student)
            self.template_value['category'] = self.app_context.category
            course = self.app_context.get_environ()['course']
            course = self.app_context.get_environ()['course']
            image_or_video_data = unicode(
                course.get('main_image', {}).get('url'))

            # Backward compatibility
            # TODO(rthakker) remove this when not required anymore
            if not image_or_video_data:
                image_or_video_data = unicode(
                    course.get('main_video', {}).get('url'))

            if image_or_video_data:
                video_id = common_utils.find_youtube_video_id(image_or_video_data)
                if video_id:
                    self.template_value['show_video'] = True
                    self.template_value['video_id'] = video_id
                else:
                    self.template_value['show_image'] = True

            self.template_value['is_progress_recorded'] = is_progress_recorded(
                self, student)
            self.template_value['navbar'] = {'course': True}
            course = self.get_course()
            course_availability = course.get_course_availability()
            settings = self.app_context.get_environ()
            self._set_show_registration_settings(settings, student, profile,
                                                 course_availability)
            self._set_show_image_or_video(settings)
            self.set_common_values(settings, student, course,
                                    course_availability)
        finally:
            models.MemcacheManager.end_readonly()
        self.render('course.html')

    def _set_show_image_or_video(self, settings):
        show_image_or_video = unicode(
            settings['course'].get('main_image', {}).get('url'))
        if show_image_or_video:
            video_id = common_utils.find_youtube_video_id(show_image_or_video)
            if video_id:
                self.template_value['show_video'] = True
                self.template_value['video_id'] = video_id
            else:
                self.template_value['show_image'] = True

    def _set_show_registration_settings(self, settings, student, profile,
                                        course_availability):
        if (roles.Roles.is_course_admin(self.app_context) or
            course_availability in (
                courses.COURSE_AVAILABILITY_REGISTRATION_REQUIRED,
                courses.COURSE_AVAILABILITY_REGISTRATION_OPTIONAL)):
            self.template_value['show_registration_page'] = True

        if not student or student.is_transient and profile:
            additional_registration_fields = self.app_context.get_environ(
                )['reg_form']['additional_registration_fields']
            if profile is not None and not additional_registration_fields:
                self.template_value['show_registration_page'] = False
                self.template_value['register_xsrf_token'] = (
                    crypto.XsrfTokenManager.create_xsrf_token('register-post'))

    def set_common_values(self, settings, student, course,
                           course_availability):
        self.template_value['transient_student'] = student.is_transient
        self.template_value['navbar'] = {'course': True}
        student_view = unit_outline.StudentCourseView(course, student)
        self.template_value['course_outline'] = student_view.contents
        self.template_value['course_availability'] = course_availability
        self.template_value['show_lessons_in_syllabus'] = (
            settings['course'].get('show_lessons_in_syllabus', False))

        self.template_value['extra_content'] = []
        for extra_content_hook in self.EXTRA_CONTENT:
            extra_content = extra_content_hook(
                self.app_context, course, student_view, student)
            if extra_content is not None:
                self.template_value['extra_content'].append(extra_content)


class UnitHandler(controller_utils.BaseHandler):
    """Handler for generating unit page."""

    # A list of callback functions which modules can use to add extra content
    # panels at the bottom of the page. Each function should return a string
    # or None.  Arguments are:
    # - The current application context
    # - The current course
    # - The current unit (in the broad sense - this may be a unit or assessment
    #   or custom unit)
    # - The current lesson (or None, if no lessons or current unit displays
    #   all lessons on one page)
    # - The current assessment, if in a unit that has a pre- or post-
    #   assessment.
    # - The StudentCourseView governing this student's view of what course
    #   content is accessible.
    # - The current student.  Note that this may be a TransientStudent.
    EXTRA_CONTENT = []

    # The lesson title provider should be a function which receives the
    # app_context, the unit, and the lesson, and returns a jinja2.Markup or a
    # safe_dom object. If it returns None, the default title is used instead.
    _LESSON_TITLE_PROVIDER = None

    @classmethod
    def set_lesson_title_provider(cls, lesson_title_provider):
        if cls._LESSON_TITLE_PROVIDER:
            raise Exception('Lesson title provider already set by a module')
        cls._LESSON_TITLE_PROVIDER = lesson_title_provider

    def _default_lesson_title_provider(self, app_context, unit, lesson,
                                       unused_student):
        return safe_dom.Template(
            self.get_template('lesson_title.html'),
            unit=unit,
            lesson=lesson,
            can_see_drafts=custom_modules.can_see_drafts(app_context),
            is_course_admin=roles.Roles.is_course_admin(app_context),
            is_read_write_course=app_context.fs.is_read_write())

    def get(self):
        """Handles GET requests."""
        models.MemcacheManager.begin_readonly()
        try:
            student = None
            user = self.personalize_page_and_get_user()
            if user:
                student = models.Student.get_enrolled_student_by_user(user)
            student = student or models.TransientStudent()

            # What unit/lesson/assessment IDs are wanted for this request?
            selected_ids = []
            if 'unit' in self.request.params:
                selected_ids.append(self.request.get('unit'))
                if 'lesson' in self.request.params:
                    selected_ids.append(self.request.get('lesson'))
                elif 'assessment' in self.request.params:
                    selected_ids.append(self.request.get('assessment'))

            # Build up an object giving this student's view on the course.
            course = self.get_course()
            student_view = unit_outline.StudentCourseView(
                course, student, selected_ids)

            # If the location in the course selected by GET arguments is not
            # available, redirect to the course overview page.
            active_elements = student_view.get_active_elements()
            if not active_elements:
                self.redirect('/course')
                return
            unit = active_elements[0].course_element
            if (not unit.show_contents_on_one_page and
                len(active_elements) < len(selected_ids)):
                self.redirect('/course')
                return
            lesson = assessment = None
            if len(active_elements) > 1:
                if active_elements[1].kind == 'lesson':
                    lesson = active_elements[1].course_element
                else:
                    assessment = active_elements[1].course_element

            # Set template values for nav bar and page type.
            self.template_value['navbar'] = {'course': True}

            # Set template values for a unit and its lesson entities
            self.template_value['unit'] = unit
            self.template_value['unit_id'] = unit.unit_id

            self.template_value['lesson'] = lesson

            forum_email = self.get_course().get_course_forum_email()
            if forum_email is not None:
                self.template_value['forum_id'] = forum_email.split('@')[0]
                domain = forum_email.split('@')[1]
                if 'googlegroups.com' == domain:
                    self.template_value['forum_domain'] = ''
                else:
                    self.template_value['forum_domain'] = ('/a/' + domain)

            self.template_value['watch_time_xsrf_token'] = (
                XsrfTokenManager.create_xsrf_token('record_video_watchtime'))
            self.template_value['student_questions_module'] = False
            student_questions_module = student_questions.custom_module
            if student_questions_module is not None and forum_email is not None:
                if student_questions_module.enabled:
                    self.template_value['student_questions_module'] = True
                    self.template_value['submit_question_xsrf_token'] = (
                        XsrfTokenManager.create_xsrf_token('submit_question'))
                    self.template_value['inc_count_xsrf_token'] = (
                        XsrfTokenManager.create_xsrf_token('inc_count'))

            # These attributes are needed in order to render questions (with
            # progress indicators) in the lesson body. They are used by the
            # custom component renderers in the assessment_tags module.
            self.student = student
            self.unit_id = unit.unit_id

            course_availability = course.get_course_availability()
            settings = self.app_context.get_environ()
            self.template_value['course_outline'] = student_view.contents
            self.template_value['course_availability'] = course_availability
            if (unit.show_contents_on_one_page and
                'confirmation' not in self.request.params):
                self._show_all_contents(student, unit, student_view)
            else:
                # For all-on-one-page units, the student view won't believe
                # that pre/post assessments are separate, visibile things,
                # so we must separately load the appropriate assessment.
                if (unit.show_contents_on_one_page and
                    'confirmation' in self.request.params):
                    assessment = course.find_unit_by_id(
                        self.request.get('assessment'))
                self._show_single_element(student, unit, lesson, assessment,
                                          student_view)

            self.template_value['extra_content'] = []
            for extra_content_hook in self.EXTRA_CONTENT:
                extra_content = extra_content_hook(
                    self.app_context, course, unit, lesson, assessment,
                    student_view, student)
                if extra_content is not None:
                    self.template_value['extra_content'].append(extra_content)

            self._set_gcb_html_element_class()
        finally:
            models.MemcacheManager.end_readonly()
        self.render('unit.html')

    def _set_gcb_html_element_class(self):
        """Select conditional CSS to hide parts of the unit page."""

        # TODO(jorr): Add an integration test for this once, LTI producer and
        # consumer code is completely checked in.

        gcb_html_element_class = []

        if self.request.get('hide-controls') == 'true':
            gcb_html_element_class.append('hide-controls')

        if self.request.get('hide-lesson-title') == 'true':
            gcb_html_element_class.append('hide-lesson-title')

        self.template_value['gcb_html_element_class'] = (
            ' '.join(gcb_html_element_class))

    def _apply_gcb_tags(self, text):
        return jinja_utils.get_gcb_tags_filter(self)(text)

    def _show_all_contents(self, student, unit, student_view):
        is_admin = roles.Roles.is_course_admin(self.app_context)

        course = self.get_course()
        self.init_template_values(self.app_context.get_environ())

        display_content = []

        if unit.unit_header:
            display_content.append(self._apply_gcb_tags(unit.unit_header))

        children_order = course.get_children_order()
        for item in children_order:
            if item["id"] == unit.unit_id:
                children = item["children"]
                for child in children:
                    if child["section"] == "lesson":
                        lesson = course.find_lesson_by_id(None,child["id"])
                        if lesson and (course.is_lesson_available(unit, lesson) or is_admin):
                            self.lesson_id = lesson.lesson_id
                            self.lesson_is_scored = lesson.scored
                            template_values = copy.copy(self.template_value)
                            self.set_lesson_content(student, unit, lesson, student_view,
                                                    template_values)
                            display_content.append(self.render_template_to_html(
                                template_values, 'lesson_common.html'))
                            del self.lesson_id
                            del self.lesson_is_scored
                    else:
                        assessment = course.find_unit_by_id(child["id"])
                        if assessment and assessment.is_assessment() and (course.is_unit_available(assessment) or is_admin):
                            display_content.append(self.get_assessment_display_content(
                                student, unit, assessment,
                                student_view, {}))
                break


        if unit.unit_footer:
            display_content.append(self._apply_gcb_tags(unit.unit_footer))

        self.template_value['display_content'] = display_content

    def _showing_first_element(self, unit, lesson, assessment, is_activity):
        """Whether the unit page is showing the first element of a Unit."""

        course = self.get_course()
        children_order = course.get_children_order()
        for item in children_order:
            if str(item["id"]) == str(unit.unit_id):
                children = item["children"]
                for child in children:
                    if child["section"] == "lesson":
                        this_lesson = course.find_lesson_by_id(None,child["id"])
                        if this_lesson:
                            if lesson and lesson.lesson_id == this_lesson.lesson_id:
                                # If the first lesson has an activity, then we are showing
                                # the first element if we are showing the lesson, and not
                                # the activity.
                                return not is_activity
                            return False
                    else:
                        this_assessment = course.find_unit_by_id(child["id"])
                        if this_assessment and this_assessment.is_assessment():
                            return (assessment and
                                    str(assessment.unit_id) == str(this_assessment.unit_id))
                #we mateched item with unit and hence break
                break


        # If unit has assessment, no lessons,
        # then we're both at the first and last item.
        unit_lessons = course.get_lessons(unit.unit_id)
        sub_units = course.get_subunits(unit.unit_id)
        if not sub_units and not unit_lessons:
            return True

        return False

    def _showing_last_element(self, unit, lesson, assessment, is_activity):
        """Whether the unit page is showing the last element of a Unit."""

        course = self.get_course()
        children_order = course.get_children_order()
        for item in children_order:
            if str(item["id"]) == str(unit.unit_id):
                children = item["children"]
                for child in reversed(children):
                    if child["section"] == "lesson":
                        this_lesson = course.find_lesson_by_id(None,child["id"])
                        if this_lesson:
                            if lesson and lesson.lesson_id == this_lesson.lesson_id:
                                # If the first lesson has an activity, then we are showing
                                # the first element if we are showing the lesson, and not
                                # the activity.
                                return not is_activity
                            return False
                    else:
                        this_assessment = course.find_unit_by_id(child["id"])
                        if this_assessment and this_assessment.is_assessment():
                            return (assessment and
                                    str(assessment.unit_id) == str(this_assessment.unit_id))
                #we mateched item with unit and hence break
                break


        # If unit has assessment, no lessons,
        # then we're both at the first and last item.
        unit_lessons = course.get_lessons(unit.unit_id)
        sub_units = course.get_subunits(unit.unit_id)
        if not sub_units and not unit_lessons:
            return True

        return False

    def _show_single_element(self, student, unit, lesson, assessment,
                             student_view):
        # Add markup to page which depends on the kind of content.

        # need 'activity' to be True or False, and not the string 'true' or None
        is_activity = (self.request.get('activity') != '' or
                       '/activity' in self.request.path)
        display_content = []
        if (unit.unit_header and
            self._showing_first_element(unit, lesson, assessment, is_activity)):

            display_content.append(self._apply_gcb_tags(unit.unit_header))
        if assessment:
            if 'confirmation' in self.request.params:
                self.set_confirmation_content(student, unit, assessment,
                                              student_view)
                self.template_value['assessment_name'] = (
                    self.template_value.get('assessment_name').lower())
                display_content.append(self.render_template_to_html(
                    self.template_value, 'test_confirmation_content.html'))
            else:
                display_content.append(self.get_assessment_display_content(
                    student, unit, assessment, student_view,
                    self.template_value))
        elif lesson:
            self.lesson_id = lesson.lesson_id
            self.lesson_is_scored = lesson.scored
            if is_activity:
                self.set_activity_content(student, unit, lesson, student_view)
            else:
                self.set_lesson_content(student, unit, lesson,
                                        student_view, self.template_value)
            display_content.append(self.render_template_to_html(
                    self.template_value, 'lesson_common.html'))
        if (unit.unit_footer and
            self._showing_last_element(unit, lesson, assessment, is_activity)):

            display_content.append(self._apply_gcb_tags(unit.unit_footer))
        self.template_value['display_content'] = display_content

    def get_assessment_display_content(self, student, unit, assessment,
                                       student_view, template_values):
        template_values['page_type'] = ASSESSMENT_PAGE_TYPE
        template_values['assessment'] = assessment
        outline_element = student_view.find_element(
            [unit.unit_id, assessment.unit_id])
        if outline_element:
            template_values['back_button_url'] = outline_element.prev_link
            template_values['next_button_url'] = outline_element.next_link
        assessment_handler = assessments.AssessmentHandler()
        assessment_handler.app_context = self.app_context
        assessment_handler.request = self.request
        return assessment_handler.get_assessment_content(
            student, self.get_course(), assessment, as_lesson=True)

    def set_confirmation_content(self, student, unit, assessment,
                                 student_view):
        course = self.get_course()
        self.template_value['page_type'] = ASSESSMENT_CONFIRMATION_PAGE_TYPE
        self.template_value['unit'] = unit
        self.template_value['assessment'] = assessment
        self.template_value['is_confirmation'] = True
        self.template_value['assessment_name'] = assessment.title
        self.template_value['score'] = (
            course.get_score(student, str(assessment.unit_id)))
        self.template_value['is_last_assessment'] = (
            course.is_last_assessment(assessment))
        self.template_value['overall_score'] = (
            course.get_overall_score(student))
        self.template_value['result'] = course.get_overall_result(student)
        # Confirmation page's prev link goes back to assessment itself, not
        # assessment's previous page.
        outline_element = student_view.find_element(
            [unit.unit_id, assessment.unit_id])
        if outline_element:
            self.template_value['back_button_url'] = outline_element.link
            self.template_value['next_button_url'] = outline_element.next_link

    def set_activity_content(self, student, unit, lesson, student_view):
        self.template_value['page_type'] = ACTIVITY_PAGE_TYPE
        self.template_value['lesson'] = lesson
        self.template_value['lesson_id'] = lesson.lesson_id
        outline_element = student_view.find_element(
            [unit.unit_id, lesson.lesson_id])
        if outline_element:
            self.template_value['back_button_url'] = outline_element.prev_link
            self.template_value['next_button_url'] = outline_element.next_link
        self.template_value['activity'] = {
            'title': lesson.activity_title,
            'activity_script_src': (
                self.get_course().get_activity_filename(unit.unit_id,
                                                        lesson.lesson_id))}
        self.template_value['page_type'] = 'activity'
        self.template_value['title'] = lesson.activity_title

        if student_view.is_progress_recorded():
            # Mark this page as accessed. This is done after setting the
            # student progress template value, so that the mark only shows up
            # after the student visits the page for the first time.
            self.get_course().get_progress_tracker().put_activity_accessed(
                student, unit.unit_id, lesson.lesson_id)

    def _get_lesson_title(self, unit, lesson, student):
        title = None
        if self._LESSON_TITLE_PROVIDER:
            title = self._LESSON_TITLE_PROVIDER(
                self.app_context, unit, lesson, student)
        if title is None:
            title = self._default_lesson_title_provider(
                self.app_context, unit, lesson, student)
        return title

    def set_lesson_content(self, student, unit, lesson, student_view,
                           template_values):
        template_values['page_type'] = UNIT_PAGE_TYPE
        template_values['unit'] = unit
        template_values['lesson'] = lesson
        template_values['lesson_id'] = lesson.lesson_id
        outline_element = student_view.find_element(
            [unit.unit_id, lesson.lesson_id])
        if outline_element:
            template_values['back_button_url'] = outline_element.prev_link
            template_values['next_button_url'] = outline_element.next_link
        template_values['page_type'] = 'unit'
        template_values['title'] = self._get_lesson_title(unit, lesson, student)

        if not lesson.manual_progress and student_view.is_progress_recorded():
            # Mark this page as accessed. This is done after setting the
            # student progress template value, so that the mark only shows up
            # after the student visits the page for the first time.
            self.get_course().get_progress_tracker().put_html_accessed(
                student, unit.unit_id, lesson.lesson_id)


class ReviewDashboardHandler(controller_utils.BaseHandler):
    """Handler for generating the index of reviews that a student has to do."""

    def _populate_template(self, course, unit, review_steps):
        """Adds variables to the template for the review dashboard."""
        self.template_value['assessment_name'] = unit.title
        self.template_value['unit_id'] = unit.unit_id

        parent_unit = course.get_parent_unit(unit.unit_id)

        if parent_unit is not None:
            self.template_value['back_link'] = 'unit?unit=%s&assessment=%s' % (
                parent_unit.unit_id, unit.unit_id)
        else:
            self.template_value['back_link'] = (
                'assessment?name=%s' % unit.unit_id)

        self.template_value['event_xsrf_token'] = (
            crypto.XsrfTokenManager.create_xsrf_token('event-post'))
        self.template_value['review_dashboard_xsrf_token'] = (
            crypto.XsrfTokenManager.create_xsrf_token('review-dashboard-post'))

        self.template_value['REVIEW_STATE_COMPLETED'] = (
            domain.REVIEW_STATE_COMPLETED)

        self.template_value['review_steps'] = review_steps
        self.template_value['review_min_count'] = (
            unit.workflow.get_review_min_count())

        review_due_date = unit.workflow.get_review_due_date()
        if review_due_date:
            self.template_value['review_due_date'] = review_due_date.strftime(
                controller_utils.HUMAN_READABLE_DATETIME_FORMAT)

            time_now = datetime.datetime.now()
            self.template_value['due_date_exceeded'] = (
                time_now > review_due_date)
        else:
            self.template_value['due_date_exceeded'] = False

    def get(self):
        """Handles GET requests."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return

        course = self.get_course()
        rp = course.get_reviews_processor()
        unit, _ = extract_unit_and_lesson(self)
        if not unit:
            self.error(404)
            return

        self.template_value['navbar'] = {'course': True}

        if not course.needs_human_grader(unit):
            self.error(404)
            return

        # Check that the student has submitted the corresponding assignment.
        if not rp.does_submission_exist(unit.unit_id, student.get_key()):
            self.template_value['error_code'] = (
                'cannot_review_before_submitting_assignment')
            self.render('error.html')
            return

        review_steps = rp.get_review_steps_by(unit.unit_id, student.get_key())

        self._populate_template(course, unit, review_steps)
        required_review_count = unit.workflow.get_review_min_count()

        # The student can request a new submission if:
        # - all his/her current reviews are in Draft/Completed state, and
        # - he/she is not in the state where the required number of reviews
        #       has already been requested, but not all of these are completed.
        self.template_value['can_request_new_review'] = (
            len(review_steps) < required_review_count or
            models_review.ReviewUtils.has_completed_all_assigned_reviews(
                review_steps)
        )
        self.render('review_dashboard.html')

    def post(self):
        """Allows a reviewer to request a new review."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return

        if not self.assert_xsrf_token_or_fail(
                self.request, 'review-dashboard-post'):
            return

        course = self.get_course()
        unit, unused_lesson = extract_unit_and_lesson(self)
        if not unit:
            self.error(404)
            return

        rp = course.get_reviews_processor()
        review_steps = rp.get_review_steps_by(unit.unit_id, student.get_key())
        self.template_value['navbar'] = {'course': True}

        if not course.needs_human_grader(unit):
            self.error(404)
            return

        # Check that the student has submitted the corresponding assignment.
        if not rp.does_submission_exist(unit.unit_id, student.get_key()):
            self.template_value['error_code'] = (
                'cannot_review_before_submitting_assignment')
            self.render('error.html')
            return

        # Check that the review due date has not passed.
        time_now = datetime.datetime.now()
        review_due_date = unit.workflow.get_review_due_date()
        if review_due_date and time_now > review_due_date:
            self.template_value['error_code'] = (
                'cannot_request_review_after_deadline')
            self.render('error.html')
            return

        # Check that the student can request a new review.
        review_min_count = unit.workflow.get_review_min_count()
        can_request_new_review = (
            len(review_steps) < review_min_count or
            models_review.ReviewUtils.has_completed_all_assigned_reviews(
                review_steps))
        if not can_request_new_review:
            self.template_value['review_min_count'] = review_min_count
            self.template_value['error_code'] = 'must_complete_more_reviews'
            self.render('error.html')
            return

        self.template_value['no_submissions_available'] = True

        try:
            review_step_key = rp.get_new_review(unit.unit_id, student.get_key())
            redirect_params = {
                'key': review_step_key,
                'unit': unit.unit_id,
            }
            self.redirect('/review?%s' % urllib.urlencode(redirect_params))
        except Exception:  # pylint: disable=broad-except
            review_steps = rp.get_review_steps_by(
                unit.unit_id, student.get_key())
            self._populate_template(course, unit, review_steps)
            self.render('review_dashboard.html')


class ReviewHandler(controller_utils.BaseHandler):
    """Handler for generating the submission page for individual reviews."""

    # pylint: disable=too-many-statements
    def get(self):
        """Handles GET requests."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return

        course = self.get_course()
        rp = course.get_reviews_processor()
        unit, unused_lesson = extract_unit_and_lesson(self)

        if not course.needs_human_grader(unit):
            self.error(404)
            return

        review_step_key = self.request.get('key')
        if not unit or not review_step_key:
            self.error(404)
            return

        try:
            review_step_key = db.Key(encoded=review_step_key)
            review_step = rp.get_review_steps_by_keys(
                unit.unit_id, [review_step_key])[0]
        except Exception:  # pylint: disable=broad-except
            self.error(404)
            return

        if not review_step:
            self.error(404)
            return

        # Check that the student is allowed to review this submission.
        if not student.has_same_key_as(review_step.reviewer_key):
            self.error(404)
            return

        model_version = course.get_assessment_model_version(unit)
        assert model_version in courses.SUPPORTED_ASSESSMENT_MODEL_VERSIONS
        self.template_value['model_version'] = model_version
        if model_version == courses.ASSESSMENT_MODEL_VERSION_1_4:
            configure_assessment_view = self.configure_assessment_view_1_4
            configure_readonly_review = self.configure_readonly_review_1_4
            configure_active_review = self.configure_active_review_1_4
        elif model_version == courses.ASSESSMENT_MODEL_VERSION_1_5:
            configure_assessment_view = self.configure_assessment_view_1_5
            configure_readonly_review = self.configure_readonly_review_1_5
            configure_active_review = self.configure_active_review_1_5
        else:
            raise ValueError('Bad assessment model version: %s' % model_version)

        self.template_value['navbar'] = {'course': True}
        self.template_value['unit_id'] = unit.unit_id
        self.template_value['key'] = review_step_key

        submission_key = review_step.submission_key
        submission_contents = student_work.Submission.get_contents_by_key(
            submission_key)

        configure_assessment_view(unit, submission_contents)

        review_due_date = unit.workflow.get_review_due_date()
        if review_due_date:
            self.template_value['review_due_date'] = review_due_date.strftime(
                controller_utils.HUMAN_READABLE_DATETIME_FORMAT)

        review_key = review_step.review_key
        review_obj = rp.get_reviews_by_keys(
            unit.unit_id, [review_key])[0] if review_key else None
        time_now = datetime.datetime.now()
        show_readonly_review = (
            review_step.state == domain.REVIEW_STATE_COMPLETED or
            (review_due_date and time_now > review_due_date))

        self.template_value['due_date_exceeded'] = bool(
            review_due_date and time_now > review_due_date)

        if show_readonly_review:
            configure_readonly_review(unit, review=review_obj)
        else:
            # Populate the review form,
            configure_active_review(unit, review=review_obj)

        self.template_value['assessment_xsrf_token'] = (
            crypto.XsrfTokenManager.create_xsrf_token('review-post'))
        self.template_value['event_xsrf_token'] = (
            crypto.XsrfTokenManager.create_xsrf_token('event-post'))

        # pylint: disable=protected-access
        self.render('review.html', additional_dirs=[assessments._TEMPLATES_DIR])

    def configure_assessment_view_1_4(self, unit, submission_contents):
        readonly_student_assessment = \
            assessments.create_readonly_assessment_params(
                self.get_course().get_assessment_content(unit),
                student_work.StudentWorkUtils.get_answer_list(
                    submission_contents))
        self.template_value[
            'readonly_student_assessment'] = readonly_student_assessment

    def configure_assessment_view_1_5(self, unit, submission_contents):
        self.template_value['html_review_content'] = unit.html_content
        self.template_value['html_reviewee_answers'] = transforms.dumps(
            submission_contents)

    def configure_readonly_review_1_4(self, unit, review_contents):
        # Not being used anymore
        readonly_review_form = assessments.create_readonly_assessment_params(
            self.get_course().get_review_content(unit),
            student_work.StudentWorkUtils.get_answer_list(review_contents))
        self.template_value['readonly_review_form'] = readonly_review_form

    def configure_readonly_review_1_5(self, unit, review):
        self.template_value['readonly_review_form'] = True
        self.template_value['html_review_form'] = unit.html_review_form
        if review:
            self.template_value['html_review_answers'] = review.contents
            self.template_value['score'] = review.score
        else:
            self.template_value['html_review_answers'] = None
            self.template_value['score'] = None

    def configure_active_review_1_4(self, unit, review_contents):
        # Not being used anymore
        self.template_value['assessment_script_src'] = (
            self.get_course().get_review_filename(unit.unit_id))
        saved_answers = (
            student_work.StudentWorkUtils.get_answer_list(review_contents)
            if review_contents else [])
        self.template_value['saved_answers'] = transforms.dumps(saved_answers)

    def configure_active_review_1_5(self, unit, review):
        self.template_value['html_review_form'] = unit.html_review_form
        if review:
            self.template_value['html_review_answers'] = review.contents
            self.template_value['score'] = review.score
        else:
            self.template_value['html_review_answers'] = None
            self.template_value['score'] = None

    def post(self):
        """Handles POST requests, when a reviewer submits a review."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return

        if not self.assert_xsrf_token_or_fail(self.request, 'review-post'):
            return

        course = self.get_course()
        rp = course.get_reviews_processor()

        unit_id = self.request.get('unit_id')
        unit = self.find_unit_by_id(unit_id)
        if not unit or not course.needs_human_grader(unit):
            self.error(404)
            return

        review_step_key = self.request.get('key')
        if not review_step_key:
            self.error(404)
            return

        try:
            review_step_key = db.Key(encoded=review_step_key)
            review_step = rp.get_review_steps_by_keys(
                unit.unit_id, [review_step_key])[0]
        except Exception:  # pylint: disable=broad-except
            self.error(404)
            return

        # Check that the student is allowed to review this submission.
        if not student.has_same_key_as(review_step.reviewer_key):
            self.error(404)
            return

        self.template_value['navbar'] = {'course': True}
        self.template_value['unit_id'] = unit.unit_id

        # Check that the review due date has not passed.
        time_now = datetime.datetime.now()
        review_due_date = unit.workflow.get_review_due_date()
        if review_due_date and time_now > review_due_date:
            self.template_value['time_now'] = time_now.strftime(
                controller_utils.HUMAN_READABLE_DATETIME_FORMAT)
            self.template_value['review_due_date'] = (
                review_due_date.strftime(controller_utils.HUMAN_READABLE_DATETIME_FORMAT))
            self.template_value['error_code'] = 'review_deadline_exceeded'
            self.render('error.html')
            return

        mark_completed = (self.request.get('is_draft') == 'false')
        self.template_value['is_draft'] = (not mark_completed)

        review_payload = self.request.get('answers')
        review_score = float(self.request.get('score'))
        review_payload = transforms.loads(
            review_payload) if review_payload else []
        try:
            rp.write_review(
                unit.unit_id, review_step_key, review_payload, mark_completed, review_score)
            course.update_final_grades(student)
        except domain.TransitionError:
            self.template_value['error_code'] = 'review_already_submitted'
            self.render('error.html')
            return

        self.render('review_confirmation.html')


class EventsRESTHandler(controller_utils.BaseRESTHandler):
    """Provides REST API for an Event."""

    URL = '/rest/events'
    NON_PII_RANDOMIZED_ID = 'session_id'
    XSRF_TOKEN = 'event-post'

    def get(self):
        """Returns a 404 error; this handler should not be GET-accessible."""
        self.error(404)
        return

    def _add_request_facts(self, payload_json):
        payload_dict = transforms.loads(payload_json)
        if 'loc' not in payload_dict:
            payload_dict['loc'] = {}
        loc = payload_dict['loc']
        loc['locale'] = self.get_locale_for(self.request, self.app_context)
        loc['language'] = self.request.headers.get('Accept-Language')
        loc['country'] = self.request.headers.get('X-AppEngine-Country')
        loc['region'] = self.request.headers.get('X-AppEngine-Region')
        loc['city'] = self.request.headers.get('X-AppEngine-City')
        lat_long = self.request.headers.get('X-AppEngine-CityLatLong')
        if lat_long:
            latitude, longitude = lat_long.split(',')
            loc['lat'] = float(latitude)
            loc['long'] = float(longitude)
        user_agent = self.request.headers.get('User-Agent')
        if user_agent:
            payload_dict['user_agent'] = user_agent
        payload_json = transforms.dumps(payload_dict).lstrip(
            models.transforms.JSON_XSSI_PREFIX)
        return payload_json

    def post(self):
        """Receives event and puts it into datastore."""

        COURSE_EVENTS_RECEIVED.inc()
        if not self.can_record_student_events():
            return

        request = transforms.loads(self.request.get('request'))
        if not self.assert_xsrf_token_or_fail(request, self.XSRF_TOKEN, {}):
            return

        user = self.get_user()
        if not user:
            return

        # For non-Students, the amount of logged PII is tiny - just
        # EventEntity.  We don't want to bother doing the full Wipeout support
        # dance for these users, so rather than record their actual user ID,
        # we instead make up a random string and record that.  This string
        # simply can not be traced back to a specific user.  The user may
        # clear cookies at any time and be 100% divorced from that session
        # identity in logs.  Further, when a user signs in as a student, their
        # previous course activity is not correlatable with their previous
        # non-registered activity.
        student = models.Student.get_enrolled_student_by_user(user)
        user_id = None
        if not student:
            user_id = self.request.cookies.get(self.NON_PII_RANDOMIZED_ID)
            if not user_id:
                user_id = 'RND_' + uuid.uuid4().hex
                self.response.set_cookie(
                    self.NON_PII_RANDOMIZED_ID, value=user_id,
                    path=self.app_context.get_slug())

        source = request.get('source')
        payload_json = request.get('payload')
        payload_json = self._add_request_facts(payload_json)
        models.EventEntity.record(source, user, payload_json, user_id)
        COURSE_EVENTS_RECORDED.inc()

        if student:
            self.process_event(student, source, payload_json)

    def process_event(self, student, source, payload_json):
        """Processes an event after it has been recorded in the event stream."""

        payload = transforms.loads(payload_json)

        if 'location' not in payload:
            return

        source_url = payload['location']

        if source in TAGS_THAT_TRIGGER_BLOCK_COMPLETION:
            unit_id, lesson_id = get_unit_and_lesson_id_from_url(
                self, source_url)
            if unit_id is not None and lesson_id is not None:
                self.get_course().get_progress_tracker().put_block_completed(
                    student, unit_id, lesson_id, payload['index'])
        elif source in TAGS_THAT_TRIGGER_COMPONENT_COMPLETION:
            unit_id, lesson_id = get_unit_and_lesson_id_from_url(
                self, source_url)
            cpt_id = payload['instanceid']
            if (unit_id is not None and lesson_id is not None and
                cpt_id is not None):
                self.get_course().get_progress_tracker(
                    ).put_component_completed(
                        student, unit_id, lesson_id, cpt_id)
        elif source in TAGS_THAT_TRIGGER_HTML_COMPLETION:
            # Records progress for scored lessons.
            unit_id, lesson_id = get_unit_and_lesson_id_from_url(
                self, source_url)
            course = self.get_course()
            unit = course.find_unit_by_id(unit_id)
            lesson = course.find_lesson_by_id(unit, lesson_id)
            if (unit_id is not None and
                lesson_id is not None and
                not lesson.manual_progress):
                self.get_course().get_progress_tracker().put_html_completed(
                    student, unit_id, lesson_id)


def on_module_enabled(unused_custom_module):
    # Conform with convention for sub-packages within modules/courses; this
    # file doesn't have any module-registration-time work to do.
    pass


def get_namespaced_handlers():
    return [
        ('/activity', UnitHandler),
        ('/course', CourseHandler),
        ('/review', ReviewHandler),
        ('/reviewdashboard', ReviewDashboardHandler),
        ('/unit', UnitHandler)]
