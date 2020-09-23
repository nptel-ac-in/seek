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

"""Utility to add theme specific code."""

__author__ = 'Thejesh GN (tgn@google.com)'


from common import tags
from models import courses
from models import custom_modules
from modules.course_theme import settings

MODULE_NAME = 'Course Theme Library'


# Module registration
custom_module = None


def register_module():
    """Registers this module in the registry."""
    global_routes = []
    settings.CourseThemeSettings.register()

    global custom_module
    custom_module = custom_modules.Module(
        MODULE_NAME, 'Provides library to register theme related assets/code',
        global_routes, [])
    return custom_module
