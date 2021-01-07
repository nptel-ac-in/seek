# Copyright 2018 Google Inc. All Rights Reserved.
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

"""Contains Handlers for the Progressive Web App For NPTEL"""

__author__ = ['Rishav Thakker (rthakker@google.com)',
              'Sagar Kothari (sagarkothari@google.com)']
import os
import datetime
import base64

from controllers import utils as controller_utils
from common import utils as common_utils
from models import transforms
from common import tags
from common import safe_dom
from common import users
from models import models
from modules.courses import unit_outline
from models import roles
from models import courses
from models import course_list
from models import course_category
from models import progress as progress_model
from models.models import Student
from modules.explorer import student as modules_student
from modules.announcements import announcements
from modules.pwa import notifications as push_notif

from google.appengine.ext.webapp import template

class CourseHandler(controller_utils.ApplicationHandler):

    def __init__(self, *args, **kwargs):
        super(CourseHandler, self).__init__(*args, **kwargs)
        self.payload = {}

    def get_course(self):
        """Get current course."""
        if not hasattr(self, 'course') or not self.course:
            self.course = courses.Course(self)
        return self.course

    def render_html(self, input_html):
        if isinstance(input_html, basestring):
            return tags.html_to_safe_dom(
                input_html, self).sanitized
        elif isinstance(input_html, safe_dom.SafeDom):
            return input_html.sanitized

    def strip_and_render_course_environ(self, environ):
        """
        Strips the course environ according to the logged in user's
        privileges and what is required in the frontend, etc.
        """
        if environ['course']:
            to_render = ['blurb','instructor_details','extra_info']
            for i in to_render:
                environ['course'][i]=self.render_html(environ['course'][i])
        return environ

    def set_initial_payload(self):
        """Adds the course environment to the payload"""
        environ = self.app_context.get_environ()
        self.payload[controller_utils.COURSE_INFO_KEY] = (
            self.strip_and_render_course_environ(environ))

    def get(self):
        """Handles GET requests for getting course page for a particular course."""
        course = self.app_context.get_environ()['course']
        video_id = None
        image_or_video_data = unicode(
            course.get('main_image', {}).get('url'))
        if image_or_video_data:
            video_id = common_utils.find_youtube_video_id(image_or_video_data)

        self.set_initial_payload()
        is_enrolled=False
        user = users.get_current_user()
        if user:
            student = Student.get_enrolled_student_by_user(user)
            if student:
                is_enrolled=True

        self.payload.update({
            'can_register': self.app_context.get_environ(
                )['reg_form']['can_register'],
            'video_id': video_id,
            'is_enrolled': is_enrolled
        })

        transforms.send_json_response(
            self, 200, "Success", self.payload)


class LessonHandler(CourseHandler):

    EXTRA_CONTENT = []

    def get(self):
        """Handles GET requests for getting a particular lesson in a course"""
        self.set_initial_payload()
        try:
            student = None
            user = users.get_current_user()
            is_enrolled = False
            if user:
                student = models.Student.get_enrolled_student_by_user(user)
                if student:
                    is_enrolled=True
            student = student or models.TransientStudent()

            # What unit/lesson IDs are wanted for this request?
            selected_ids = []
            if 'unit' in self.request.params:
                selected_ids.append(self.request.get('unit'))
                if 'lesson' in self.request.params:
                    selected_ids.append(self.request.get('lesson'))


            # Build up an object giving this student's view on the course.
            course = self.get_course()
            student_view = unit_outline.StudentCourseView(
                course, student, selected_ids)

            # If the location in the course selected by GET arguments is not
            # available, redirect to the course overview page.
            active_elements = student_view.get_active_elements()
            if not active_elements:
                self.redirect('/m/course')
                return
            unit = active_elements[0].course_element
            if (not unit.show_contents_on_one_page and
                len(active_elements) < len(selected_ids)):
                self.redirect('/m/course')
                return
            lesson = assessment = None
            if len(active_elements) > 1:
                if active_elements[1].kind == 'lesson':
                    lesson = active_elements[1].course_element
                else:
                    assessment = active_elements[1].course_element

            # These attributes are needed in order to render questions (with
            # progress indicators) in the lesson body. They are used by the
            # custom component renderers in the assessment_tags module.
            self.student = student
            self.unit_id = unit.unit_id
            display_content = None
            course_availability = course.get_course_availability()
            settings = self.app_context.get_environ()
            if (unit.show_contents_on_one_page and
                'confirmation' not in self.request.params):
                display_content = self._show_all_contents(student, unit, student_view)

            # Following code sets read receipts for the particular lesson
            # on the website. Which means that the lesson is already seen.
            self.get_course().get_progress_tracker().put_html_accessed(student,
            int(self.request.get('unit')),int(self.request.get('lesson')))

            extra_content_pay = []
            for extra_content_hook in self.EXTRA_CONTENT:
                extra_content = extra_content_hook(
                    self.app_context, course, unit, lesson, assessment,
                    student_view, student)
                if extra_content is not None:
                    extra_content_pay.append(extra_content)

            self.payload.update({
                'unit' : transforms.instance_to_dict(unit),
                'unit_id': unit.unit_id,
                'lesson': transforms.instance_to_dict(lesson),
                'lesson_objectives' : self.render_html(lesson.objectives),
                'course_availability' : course_availability,
                'extra_content' : self.render_html(extra_content_pay),
                'display_content' : self.render_html(display_content),
                'is_enrolled' : is_enrolled
            })

            transforms.send_json_response(
                self, 200, "Success", self.payload)

        finally:
            pass

    def _show_all_contents(self, student, unit, student_view):
        # This shows all the content from the lesson page.
        # Extend this function in future to add unit header and footer if required.
        is_admin = roles.Roles.is_course_admin(self.app_context)
        course = self.get_course()
        display_content = []
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
        return display_content

class CourselistHandler(CourseHandler):

    def get(self):
        """ handles GET request for getting all the open and public courses from
        the CourseList"""
        try:
            courses = course_list.CourseListDAOForExplorer.get_course_list(include_closed=False)
            all_courses = []
            for i in range(len(courses)):
                if courses[i].availability != 'private':
                    all_courses.append(transforms.instance_to_dict(courses[i]))
            self.payload.update({
                'course_list' : all_courses
            })
            transforms.send_json_response(
                self, 200, "Success", self.payload)
        finally:
            pass


class ProfileHandler(push_notif.PushNotificationBase,
                     controller_utils.ApplicationHandler):

    def __init__(self, *args, **kwargs):
        super(ProfileHandler, self).__init__(*args, **kwargs)
        self.payload = {}

    def update_push_token(self, profile):
        token = self.request.get('push_token')
        if token is not None:
            return self.register_token(token, profile)

    def get(self):
        """Handles GET request to get profile details for the particular User"""
        try:
            user = users.get_current_user()
            profile = None
            loggedout = ""
            status_code = 404
            status_message = "Server_error"

            if not user:
                destURL = base64.urlsafe_b64encode("profile")
                url = '{0}'.format(IndexHandler.URL)
                self.payload.update({
                    'loginurl':users.create_login_url(url+"?desturl="+destURL+"#/profile"),
                })
                status_code = 401
                status_message = "Unauthorized"
            else:
                profile = self.get_profile_for_user(user)
                self.update_push_token(profile)
                if not profile:
                    status_message = "Profile Not Found"
                else:
                    self.payload.update({
                        'name' : profile.nick_name,
                        'state': profile.state_of_residence,
                        'country': profile.country_of_residence,
                        'mobile': profile.mobile_number,
                        'college_id': profile.college_id,
                        'college': profile.name_of_college,
                        'college_roll_no': profile.college_roll_no,
                        'profession': profile.profession,
                        'city': profile.city_of_residence,
                        'age': profile.age_group,
                        'graduationYear': profile.graduation_year,
                        'email' : profile.email,
                    })
                    status_code = 200
                    status_message = "Success"

            transforms.send_json_response(
                self, status_code, status_message, self.payload)

        finally:
            pass

class CourseOutlineHandler(CourseHandler):
    def __init__(self, *args, **kwargs):
        super(CourseOutlineHandler,self).__init__(*args,**kwargs)
        self.playload = {}

    def get(self):
        """Handles GET request for getting the course outline"""
        # Currently this only handles units and lessons. Assignments to be added.
        try:
            units_payload = {}
            lessons_payload = {}
            if self.get_course().get_course_availability() != "private":
                units = self.get_course().get_units()
                if units:
                    for i in units:
                        if i.type == 'U' and i.availability == 'course':
                            unit = {}
                            unit['title'] = i.title
                            unit['availability'] = i.availability
                            unit['unit_id'] = i.unit_id
                            units_payload[i.unit_id] = unit
                            lessons  = self.get_course().get_lessons(i.unit_id)
                            if lessons:
                                for k in lessons:
                                    if k.availability == 'course':
                                        lesson = {}
                                        lesson['title']=k.title
                                        lesson['unit_id']=i.unit_id
                                        lesson['availability']=k.availability
                                        lesson['lesson_id']=k.lesson_id
                                        lessons_payload[k.lesson_id] = lesson

                children_order = self.get_course().get_children_order()

            self.payload.update({
                'units' : units_payload,
                'lessons': lessons_payload,
                'order': children_order
            })

            transforms.send_json_response(
                self, 200, "Success", self.payload)
        finally:
            pass

class ProgressHandler(CourseHandler):

    def __init__(self,*args,**kwargs):
        super(ProgressHandler,self).__init__(*args,**kwargs)
        self.payload = {}

    def get(self):
        """ Handles Get Request for returning the progress of a student for
        a particular course."""

        try:
            student = None
            user = users.get_current_user()
            status_code = 404
            status_message = "Server_error"
            if not user:
                destURL = base64.urlsafe_b64encode("mycourses")
                url = '{0}'.format(IndexHandler.URL)
                self.payload.update({
                    'loginurl':users.create_login_url(url+"?desturl="+destURL+"#/mycourses"),
                })
                status_code = 401
                status_message = "Unauthorized"
            else:
                student = models.Student.get_enrolled_student_by_user(user)
                if not student:
                    status_message = "Student Not found"
                else:
                    course = self.get_course()
                    self.payload.update({
                        'student_name' : student.name,
                        'student_email' : student.email,
                        'date_enrolled': student.enrolled_on.strftime
                        (controller_utils.HUMAN_READABLE_DATE_FORMAT),
                        'score_list': course.get_all_scores(student),
                        'overall_score': course.get_overall_score(student)
                    })
                    status_code = 200
                    status_message = "Success"
            transforms.send_json_response(
                self, status_code, status_message, self.payload)
        finally:
            pass

class EnrolledCoursesHandler(modules_student.BaseStudentHandler):
    def __init__(self,*args,**kwargs):
        super(EnrolledCoursesHandler,self).__init__(*args,**kwargs)
        self.payload = {}

    def get(self):
        """ Handles Get Request for returining the list of courses that student
        is already enrolled in"""
        try:
            user = users.get_current_user()
            status_code = 200
            status_message = "Success"
            if not user:
                destURL = base64.urlsafe_b64encode("mycourses")
                url = '{0}'.format(IndexHandler.URL)
                self.payload.update({
                    'loginurl':users.create_login_url(url+"?desturl="+destURL+"#/mycourses"),
                })
                status_code = 401
                status_message = "Unauthorized"
            else:
                allcourses = course_list.CourseListDAOForExplorer.get_course_list(include_closed=False)
                public_courses = []
                for course in allcourses:
                    if ((course.now_available and roles.Roles.is_user_whitelisted(
                    course)) or roles.Roles.is_course_admin(course)):
                            public_courses.append(course)
                mycourses = self.get_enrolled_courses(public_courses)
                courses = []
                for i in range(len(mycourses)):
                    courses.append(transforms.instance_to_dict(mycourses[i]))
                self.payload.update({
                    'courses' : courses
                })
            transforms.send_json_response(
                self, status_code, status_message, self.payload)
        finally:
            pass

class SignOutHandler(controller_utils.ApplicationHandler):
    def get(self):
        """ handle the get request to signout from the app"""
        try:
            user = users.get_current_user()
            if user:
                self.redirect(
                    users.create_logout_url(IndexHandler.URL), normalize=False)
                return
            else:
                self.redirect(IndexHandler.URL, normalize=False)
        finally:
            pass

class IndexHandler(controller_utils.ApplicationHandler):

    INDEX_PATH = 'pwa/_static/nptel-pwa/index.html'
    URL = '/m'

    def get(self):
        """ Handles the get Request for the first request to index"""
        try:
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.INDEX_PATH)
            self.response.out.write(template.render(path, {}))
        finally:
            pass

class CategoryHandler(controller_utils.ApplicationHandler):

    def __init__(self,*args,**kwargs):
        super(CategoryHandler,self).__init__(*args,**kwargs)
        self.payload = {}

    def get(self):
        """Handles get for getting all the visible course categories."""
        try:
            category_list = sorted(course_category.CourseCategoryDAO.get_category_list(visible_only=True),
              key=lambda category: category.category)
            all_categories =[]
            for category in category_list:
                all_categories.append(category.__dict__)
            self.payload.update({
                'categories' : all_categories
            })
            transforms.send_json_response(
                self, 200, "Success", self.payload)
        finally:
            pass
class AnnouncementHandler(CourseHandler,announcements.AnnouncementsHandlerMixin):
    def __init__(self,*args,**kwargs):
        super(AnnouncementHandler,self).__init__(*args,**kwargs)
        self.payload = {}

    def get(self):
        """Handles get for getting all the announcements for a course."""
        try:
            locale = self.app_context.get_current_locale()
            if locale == self.app_context.default_locale:
                locale = None
            id = 0
            items = announcements.AnnouncementEntity.get_announcements(locale=locale)
            template_items = []
            for item in items:
                if not item.is_draft:
                    item = transforms.entity_to_dict(item)
                    date = item.get('date')
                    if date:
                        date = datetime.datetime.combine(
                            date, datetime.time(0, 0, 0, 0))
                        item['date'] = (
                            date - datetime.datetime(1970, 1, 1)).total_seconds() * 1000
                        template_items.append(item);
            self.payload.update({
                'announcements' : template_items
            })
            transforms.send_json_response(
                self, 200, "Success", self.payload)
        finally:
            pass
