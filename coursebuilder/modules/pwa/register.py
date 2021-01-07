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

"""Contain dashboard related classes for manual review."""

__author__ = ['Rishav Thakker (rthakker@google.com)',
              'Sagar Kothari (sagarkothari@google.com)']

from models import custom_modules
from . import handlers

custom_module = None

def register_module():
    """Registers this module in the registry."""

    global custom_module

    global_routes = [
        ('/m/allcourses', handlers.CourselistHandler),
        ('/m/profile', handlers.ProfileHandler),
        ('/m/mycourses', handlers.EnrolledCoursesHandler),
        ('/m/signout', handlers.SignOutHandler),
        (handlers.IndexHandler.URL, handlers.IndexHandler),
        ('/m/categories', handlers.CategoryHandler),

    ]
    course_routes = [
        ('/m/course',handlers.CourseHandler),
        ('/m/unit',handlers.LessonHandler),
        ('/m/courseoutline',handlers.CourseOutlineHandler),
        ('/m/progress',handlers.ProgressHandler),
        ('/m/announcement',handlers.AnnouncementHandler),
    ]
    custom_module = custom_modules.Module(
        'PWA',
        'A set of handlers for providing data to the PWA application',
        global_routes, course_routes)
    return custom_module
