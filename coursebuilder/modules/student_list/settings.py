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
from modules.student_list import handlers


class StudentListBaseAdminHandler(base.StudentListBase,
                                  handlers.InteractiveTableHandler):

    LIST_ACTION = 'admin?action=' + base.StudentListBase.ADMIN_TAB
    DETAILS_ACTION = 'admin?action=%s&tab=%s' % (
        base.StudentListBase.ADMIN_DETAILS_ACTION,
        base.StudentListBase.ADMIN_TAB)
    IN_ACTION = base.StudentListBase.ADMIN_TAB

    TEMPLATE_FILE = 'templates/profile_list.html'
    TEMPLATE_DIRS = [os.path.dirname(__file__)]

    SEARCH_STR_PARAM = 'email'
    DEFAULT_ORDER = 'email'
    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME

    # TODO(rthakker) make search by user_id default.
    # Also need to edit the templates accordingly.
    # if not search_str:
    #     search_str = handler.request.get('email')
    #     get_by_search_str_fn = models.StudentProfileDAO.get_profile_by_email

    @classmethod
    def get_by_search_str(cls, email):
        return models.StudentProfileDAO.get_profile_by_email(email)

    @classmethod
    def run_query(cls, cursor=None):
        if cursor:
            return db.Query(models.PersonalProfile, cursor=cursor)
        return db.Query(models.PersonalProfile)

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

        cls.classmethod_render_table(handler, dict())

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
        courses = course_list.CourseListDAO.get_course_list(
            include_closed=True)
        template_value['courses'] = courses

        template_value['back_action'] = '/modules/admin?tab=' + cls.ADMIN_TAB

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/profile_details.html',
                [os.path.dirname(__file__)]).render(template_value))

        handler.render_page({
            'page_title': handler.format_title(cls.NAME),
            'main_content': content},
            in_action=cls.ADMIN_DETAILS_ACTION)
