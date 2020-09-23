# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Contain dashboard related classes for student details."""

__authors__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

import jinja2
import os
import datetime

from google.appengine.ext import db

from models import roles
from models import transforms
from models import models
from controllers import utils
from modules.watch_time import record_watchtime

from modules.student_list import base

class StudentListDashboardHandler(base.StudentListBase):
    """Handler for Student List"""

    @classmethod
    def display_html(cls, handler):

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            return 'Forbidden'

        course = handler.get_course()
        if not course:
            handler.error(404)
            return 'Course not found'

        try:
            cursor = handler.request.get('cursor')
            old_cursor = handler.request.get('old_cursor')
            no_of_entries = int(handler.request.get('num', '50'))
            reverse_query = handler.request.get('reverse_query')
        except ValueError:
            handler.error(400)
            return 'Invalid parameters `start` and `num`'

        order = handler.request.get('order', 'email')
        # Since email is the key name, and we don't want the url to look like
        # &order=__key__, we replace 'email' with '__key__' when required.
        if order == 'email':
            order = '__key__'
        elif order == '-email':
            order = '-__key__'

        email = handler.request.get('email')

        template_value = dict()

        # Get a list of students
        students = None
        students_query = None
        new_cursor = None
        if email:
            # Settings offset and no_of_entries manually
            no_of_entries = 1
            student = models.Student.get_by_email(email)
            if student:
                students = [student]
            else:
                students = []

            template_value['search_email_query'] = email
            template_value['last_page'] = True
        else:
            try:
                students_query = None
                if cursor:
                    students_query = db.Query(models.Student, cursor=cursor)
                else:
                    students_query = db.Query(models.Student)

                if reverse_query:
                    students_query = students_query.order(
                        cls.get_reverse_order(order))
                else:
                    students_query = students_query.order(order)

                students = students_query.fetch(no_of_entries)

                if reverse_query:
                    students.reverse()
                    new_cursor = cursor
                    cursor = students_query.cursor()
                else:
                    new_cursor = students_query.cursor()

            except db.PropertyError:
                handler.error(400)
                return 'Invalid order by parameters'

        template_value['students'] = students

        # parse the student scores
        template_value['student_scores_list'] = []
        for student in students:
            scores = {}
            if student.scores:
                scores = transforms.loads(student.scores)
            template_value['student_scores_list'].append(scores)

        template_value['new_cursor'] = new_cursor
        template_value['cursor'] = cursor
        template_value['no_of_entries'] = no_of_entries
        template_value['order'] = order.replace('-', '').replace(
            '__key__', 'email')
        template_value['invert_order'] = order[0] == '-'


        # List of all units
        units = course.get_units()
        template_value['units'] = units

        template_value['list_action'] = handler.get_action_url(
            cls.DASHBOARD_NAV) + '&tab=' + cls.DASHBOARD_TAB
        template_value['details_action'] = handler.get_action_url(
            cls.DETAILS_ACTION)
        template_value['enroll_action'] = handler.get_action_url(
            cls.ENROLL_ACTION)
        template_value['enroll_xsrf'] = handler.create_xsrf_token(
            cls.ENROLL_ACTION)

        return jinja2.utils.Markup(
            handler.get_template(
                'templates/list.html',
                [os.path.dirname(__file__)]).render(template_value))

    @classmethod
    def get_details(cls, handler):
        """GET endpoint for Student Details"""
        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '403 Unauthorized'
            })
            return

        course = handler.get_course()
        if not course:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '404 Course not found'
            })
            return

        student = None
        key = handler.request.get('key')
        if not key:
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '400 No email or user id provided'
            })
            return

        student = models.Student.get(key)
        if not student:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '404 Student not found in this course'
            })
            return

        template_value = dict()

        # Parse the student scores
        if student.scores:
            template_value['student_scores'] = transforms.loads(
                student.scores)

        template_value['student'] = student

        # List of all units
        units = course.get_units()
        template_value['units'] = units

        # Watch time
        watch_time = models.StudentPropertyEntity.get(
            student, record_watchtime.RecordWatchTime.PROPERTY_NAME)

        if watch_time and watch_time.value:
            watch_time_dict = transforms.loads(watch_time.value)
            for resource_id, entity in watch_time_dict.iteritems():
                total_watched = sum(
                    [b-a for a, b in entity.get('watched', [])])
                entity['total_watched'] = total_watched
                if 'duration' in entity:
                    entity['total_watched_percent'] = (
                        '%.2f' % (total_watched*100.0/entity['duration']))
                else:
                    entity['total_watched_percent'] = '0.00'

                # Format the watched time in a pretty manner
                entity['watched_pretty'] = [
                    (datetime.timedelta(seconds=x[0]),
                    datetime.timedelta(seconds=x[1]))
                    for x in entity.get('watched', [])
                ]

                entity['duration_pretty'] = datetime.timedelta(
                    seconds=entity.get('duration', 0))

            template_value['watch_time'] = watch_time_dict

        template_value['back_action'] = handler.get_action_url(
            cls.DASHBOARD_NAV)
        template_value['enroll_action'] = handler.get_action_url(
            cls.ENROLL_ACTION)
        template_value['unenroll_action'] = handler.get_action_url(
            cls.UNENROLL_ACTION)
        template_value['enroll_xsrf'] = handler.create_xsrf_token(
            cls.ENROLL_ACTION)
        template_value['unenroll_xsrf'] = handler.create_xsrf_token(
            cls.UNENROLL_ACTION)

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/details.html',
                [os.path.dirname(__file__)]).render(template_value))

        handler.render_page({
            'page_title': handler.format_title(cls.NAME),
            'main_content': content},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_TAB)

    @classmethod
    def post_enroll(cls, handler):
        """POST endpoint to force-enroll a student"""

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '403 Unauthorized'
            })
            return

        profile = None
        email = handler.request.get('email')
        if not email:
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '400 No email or user id provided'
            })
            return


        profile = models.StudentProfileDAO.get_profile_by_email(email)
        if not profile:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '404 Student profile not found'
            })
            return

        cls.add_new_student_from_profile(profile, handler)

        handler.render_page({
            'page_title': handler.format_title(cls.NAME),
            'main_content': ('Successfully enrolled student %s'
                             % profile.email)},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_TAB)

    @classmethod
    def post_unenroll(cls, handler):
        """POST endpoint to force-unenroll a student."""

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '403 Unauthorized'
            })
            return

        key = handler.request.get('key')
        if not key:
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '400 No key specified'
            })
            return

        student = models.Student.get(key)
        if not student:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '404 Student not found'
            })
            return

        models.StudentProfileDAO.update(
            student.user_id, student.email, is_enrolled=False)

        handler.render_page({
            'page_title': handler.format_title(cls.NAME),
            'main_content': ('Successfully unenrolled student %s'
                             % student.email)},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_TAB)
