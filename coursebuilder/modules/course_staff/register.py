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

"""Course staff module."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'
import logging
from models import custom_modules
from modules.course_staff import base
from modules.course_staff import evaluate
from modules.course_staff import manage
from modules.dashboard import dashboard

custom_module = None

def register_module():
    """Registers this module in the registry."""
    course_staff_handlers = [
        ('/course_staff', evaluate.EvaluationHandler)
    ]

    dashboard.DashboardHandler.add_custom_post_action(
        base.CourseStaffBase.DASHBOARD_ADD_COURSE_STAFF,
        manage.CourseStaffDashboardHandler.add_course_staff)
    dashboard.DashboardHandler.add_custom_post_action(
        base.CourseStaffBase.DASHBOARD_REMOVE_COURSE_STAFF,
        manage.CourseStaffDashboardHandler.remove_course_staff)

    dashboard.DashboardHandler.add_custom_post_action(
        base.CourseStaffBase.DASHBOARD_COURSE_STAFF_ALLOWED_TO_GRADE,
        manage.CourseStaffDashboardHandler.course_staff_allowed_to_grade)
    dashboard.DashboardHandler.add_custom_post_action(
        base.CourseStaffBase.DASHBOARD_COURSE_STAFF_NOT_ALLOWED_TO_GRADE,
        manage.CourseStaffDashboardHandler.course_staff_not_allowed_to_grade)

    dashboard.DashboardHandler.add_custom_post_action(
        base.CourseStaffBase.DASHBOARD_COURSE_STAFF_CAN_OVERRIDE,
        manage.CourseStaffDashboardHandler.course_staff_can_override)
    dashboard.DashboardHandler.add_custom_post_action(
        base.CourseStaffBase.DASHBOARD_COURSE_STAFF_CAN_NOT_OVERRIDE,
        manage.CourseStaffDashboardHandler.course_staff_can_not_override)

    # Place it under manage
    dashboard.DashboardHandler.add_sub_nav_mapping(
        "analytics", base.CourseStaffBase.DASHBOARD_SHOW_LIST_TAB,
        base.CourseStaffBase.NAME,
        action=base.CourseStaffBase.DASHBOARD_NAV,
        contents=manage.CourseStaffDashboardHandler.display_html)



    dashboard.DashboardHandler.add_nav_mapping(
        base.CourseStaffBase.DASHBOARD_NAV, base.CourseStaffBase.NAME)

    global custom_module
    custom_module = custom_modules.Module(
        'Course Staff Module', 'A set pages for course staff.',
        [], course_staff_handlers)
    return custom_module
