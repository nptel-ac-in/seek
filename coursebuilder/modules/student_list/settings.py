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

"""Admin module for service account."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import os
import jinja2

from google.appengine.ext import db
from google.appengine.api import namespace_manager
import appengine_config

from models import roles
from models import transforms
from models import models
from models import course_list
from modules.student_list import base

class StudentListBaseAdminHandler(base.StudentListBase):

    @classmethod
    def get_student_list(cls, handler):
        """Displays a list of students from their StudentProfile objects"""

        if not roles.Roles.is_super_admin():
            handler.error(403)
            handler.render_page({
                'page_title': cls.NAME,
                'main_content': 'Unauthorized'
            })
            return

        try:
            cursor = handler.request.get('cursor')
            old_cursor = handler.request.get('old_cursor')
            no_of_entries = int(handler.request.get('num', '50'))
            reverse_query = handler.request.get('reverse_query')
        except ValueError:
            handler.error(400)
            handler.render_page({
                'page_title': cls.NAME,
                'main_content': 'Invalid parameters'
            })

        order = handler.request.get('order', 'email')

        template_value = dict()

        # Get a list of student profiles
        student_profiles = None
        query = None
        new_cursor = None

        namespace_manager.set_namespace(appengine_config.DEFAULT_NAMESPACE_NAME)

        try:
            if cursor:
                query = db.Query(models.PersonalProfile, cursor=cursor)
            else:
                query = db.Query(models.PersonalProfile)

            if reverse_query:
                query = query.order(cls.get_reverse_order(order))
            else:
                query = query.order(order)

            student_profiles = query.fetch(no_of_entries)

            if reverse_query:
                student_profiles.reverse()
                new_cursor = cursor
                cursor = query.cursor()
            else:
                new_cursor = query.cursor()
        except db.PropertyError:
            handler.error(400)
            handler.render_page({
                'page_title': cls.NAME,
                'main_content': 'Invalid parameters'
            })

        template_value['student_profiles'] = student_profiles

        template_value['new_cursor'] = new_cursor
        template_value['cursor'] = cursor
        template_value['no_of_entries'] = no_of_entries
        template_value['order'] = order.replace('-', '')
        template_value['invert_order'] = order[0] == '-'

        template_value['list_action'] = '/admin/global?tab=' + cls.ADMIN_TAB
        template_value['details_action'] = '/admin/global?action=%s&tab=%s' % (
            cls.ADMIN_DETAILS_ACTION, cls.ADMIN_TAB)

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/profile_list.html',
                [os.path.dirname(__file__)]).render(template_value))

        handler.render_page({
            'page_title': cls.NAME,
            'main_content': content
        })

    @classmethod
    def get_student_details(cls, handler):
        """GET endpoint for Student Profile Details"""

        if not roles.Roles.is_super_admin():
            handler.error(403)
            handler.render_page({
                'page_title': cls.NAME,
                'main_content': 'Unauthorized'
            })
            return

        key = handler.request.get('key')
        if not key:
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '400 No email or user id provided'
            })
            return

        namespace_manager.set_namespace(appengine_config.DEFAULT_NAMESPACE_NAME)

        profile = models.PersonalProfile.get(key)
        if not profile:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '404 Student not found in this course'
            })
            return

        template_value = dict()

        # parse the profile's enrollment info
        if profile.enrollment_info:
            template_value['enrollment_info'] = transforms.loads(
                profile.enrollment_info)

        template_value['profile'] = profile

        # List of all Courses
        courses = course_list.CourseList.all().fetch(None)
        template_value['courses'] = courses

        template_value['back_action'] = '/admin/global?tab=' + cls.ADMIN_TAB

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/profile_details.html',
                [os.path.dirname(__file__)]).render(template_value))

        handler.render_page({
            'page_title': handler.format_title(cls.NAME),
            'main_content': content},
            in_action=cls.ADMIN_DETAILS_ACTION,
            in_tab=cls.ADMIN_TAB)
