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

"""Base class for mentor module."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import os
from common import jinja_utils

class MentorBase(object):
    NAME = 'Mentor'
    ADMIN_ADD_TAB = 'admin_add_mentors'
    DASHBOARD_NAV = 'mentor'
    DASHBOARD_SHOW_LIST_TAB = 'list_mentors'
    DASHBOARD_GET_ADD_TAB = 'get_add_mentors'
    DASHBOARD_ADD_MENTORS = 'add_mentors'
    DASHBOARD_REMOVE_MENTOR = 'remove_mentor'
    MENTOR_SECTION = 'mentor'
    ENABLE_KEY = 'enable_mentor_support'

    @classmethod
    def can_use_mentor_feature(cls, course):
        course_env = course.get_environ(course.app_context)
        if cls.MENTOR_SECTION in course_env:
            mentor_env = course_env[cls.MENTOR_SECTION]
            return mentor_env[cls.ENABLE_KEY] if cls.ENABLE_KEY in mentor_env else False


    @classmethod
    def get_template(self, template_name, dirs):
        """Sets up an environment and Gets jinja template."""
        return jinja_utils.get_template(
            template_name, dirs + [os.path.dirname(__file__)])
