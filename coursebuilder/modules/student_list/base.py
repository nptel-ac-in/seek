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

"""Base class for student list"""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import logging
from google.appengine.ext import db
from models import models
from models import transforms

class StudentListBase(object):
    NAME = 'Manage Students'
    DASHBOARD_NAV = 'student_list'
    DASHBOARD_TAB = 'student_list'
    DASHBOARD_CATEGORY = 'analytics'
    DETAILS_ACTION = 'student_details'
    ENROLL_ACTION = 'student_details_enroll'
    UNENROLL_ACTION = 'student_details_unenroll'
    ADMIN_NAME = 'Manage Student Profiles'
    ADMIN_TAB = 'student_list_admin'
    ADMIN_NAV = 'student_list_admin'
    ADMIN_CATEGORY = 'analytics'
    ADMIN_SUBGROUP = 'advanced'
    ADMIN_DETAILS_ACTION = 'student_details_admin'

    @classmethod
    def add_new_student_from_profile(cls, profile, handler, labels=None):
        """Adds a new student object from its profile object for a course"""

        additional_fields = transforms.dumps({
            'form01': profile.nick_name
        })
        student_by_uid = models.Student.get_by_user_id(profile.user_id)
        is_valid_student = (
            student_by_uid is None or student_by_uid.user_id == profile.user_id)
        assert is_valid_student, ('Student\'s profile and user id do not match')

        student = models.StudentProfileDAO._add_new_student_for_current_user(
            profile.user_id, profile.email, profile.nick_name, additional_fields,
            labels
        )

        try:
            models.StudentProfileDAO._send_welcome_notification(
                handler, student)
        except Exception as e:
            logging.error(
                'Unable to send welcome notification, error: %s', str(e))
