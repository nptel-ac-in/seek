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

"""Classes and methods to create and manage Programming Assignments."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


class CourseStaffBase(object):
    NAME = 'Course Staff'
    DASHBOARD_NAV = 'course_staff'
    DASHBOARD_SHOW_LIST_TAB = 'list_course_staff'
    DASHBOARD_ADD_COURSE_STAFF = 'add_course_staff'
    DASHBOARD_REMOVE_COURSE_STAFF = 'remove_course_staff'
    DASHBOARD_COURSE_STAFF_ALLOWED_TO_GRADE = 'course_staff_allowed_to_grade'
    DASHBOARD_COURSE_STAFF_NOT_ALLOWED_TO_GRADE = 'course_staff_not_allowed_to_grade'
    DASHBOARD_COURSE_STAFF_CAN_OVERRIDE = 'course_staff_can_override'
    DASHBOARD_COURSE_STAFF_CAN_NOT_OVERRIDE = 'course_staff_can_not_override'
