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

import logging
import jinja2
import os
import datetime

from google.appengine.ext import db

from models import roles
from models import transforms
from models import models
from modules.watch_time import record_watchtime

from modules.student_list import base
from modules.student_list import handlers

class StudentListDashboardHandler(base.StudentListBase,
                                  handlers.InteractiveTableHandler):
    """Handler for Student List"""

    SEARCH_STR_PARAM = 'email'
    DEFAULT_ORDER = 'email'

    # TODO(rthakker) make search by user_id default.
    # Also need to edit the templates accordingly.
    # if not search_str:
    #     search_str = handler.request.get('email')
    #     get_by_search_str_fn = models.StudentProfileDAO.get_profile_by_email

    @classmethod
    def get_by_search_str(cls, email):
        obj, unique = models.Student.get_first_by_email(email)
        if not unique:
            logging.error('Multiple students with email: %s', email)
        return obj

    @classmethod
    def run_query(cls, cursor=None):
        if cursor:
            return db.Query(models.Student, cursor=cursor)
        return db.Query(models.Student)

    @classmethod
    def display_html(cls, handler):

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            return 'Forbidden'

        course = handler.get_course()
        if not course:
            handler.error(404)
            handler.render_page({
                'page_title': cls.NAME,
                'main_content': 'Course not found'
            })
            return

        template_value = dict()

        cls.LIST_ACTION = handler.get_action_url(
            cls.DASHBOARD_CATEGORY + '_' + cls.DASHBOARD_NAV)
        cls.DETAILS_ACTION = handler.get_action_url(
            cls.DETAILS_ACTION)

        if not cls.generate_table(handler, template_value):
            handler.error(400)
            handler.render_page({
                'page_title': cls.NAME,
                'main_content': 'Invalid parameters'
            })
            return

        # parse the student scores
        template_value['student_scores_list'] = []
        for student in template_value['objects']:
            scores = {}
            if student.scores:
                scores = transforms.loads(student.scores)
            template_value['student_scores_list'].append(scores)


        # List of all units
        units = course.get_units()
        template_value['units'] = units


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
            cls.DASHBOARD_CATEGORY + '_' + cls.DASHBOARD_NAV)
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
            in_action=cls.DASHBOARD_NAV)

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
            in_action=cls.DASHBOARD_NAV)

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
            in_action=cls.DASHBOARD_NAV)
