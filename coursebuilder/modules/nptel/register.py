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

"""Utility to add nptel specific code."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import json

from controllers.utils import BaseHandler
from controllers.utils import ReflectiveRequestHandler
from controllers import utils

from common import tags
from models import courses
from models import custom_modules
from modules.nptel import analytics
from modules.nptel import settings
from modules.nptel import transform

MODULE_NAME = 'NPTEL Library'


# Module registration
custom_module = None

class StudentProgressHandler(BaseHandler, ReflectiveRequestHandler):
    """Handles the click to 'Progress' link in the nav bar."""
    default_action = 'get_progress'
    get_actions = [ default_action ]

    def get_get_progress(self):
        progress = dict()
        user = self.get_user()
        if user:
            progress = self.get_progress_tracker().get_all_progress(user.user_id())
        self.response.out.write(json.dumps(progress, sort_keys=True))


def register_module():
    """Registers this module in the registry."""

    global_routes = [
        ('/modules/nptel/assets/.*', tags.ResourcesHandler),
        ('/modules/nptel/generate_student_report', analytics.GenerateStudentReportHandler),
        ('/modules/nptel/dump_qualified_students', analytics.DumpQualifiedStudents),
        ('/modules/nptel/dump_student_profile', analytics.DumpProfilesHandler),
        ('/modules/nptel/reindex_student_profile', analytics.ReIndexStudentProfileHandler),
        ('/modules/nptel/reindex_pa', transform.ReFormatProgrammingAssignmentsHandler),
        ('/modules/nptel/save_course', analytics.SaveCourseSettingsHandler),
        ('/modules/nptel/all_courses_profile_data_dump', analytics.AllCoursesProfileDumpHandler),
    ]

    nptel_routes = [
        ('/student/progress', StudentProgressHandler),
    ]

    settings.NptelSettings.register()

    courses.DEFAULT_COURSE_YAML_DICT['reg_form']['welcome_email'] = ''
    courses.DEFAULT_COURSE_YAML_DICT['course']['auto_subscribe_to_forum'] = False

    global custom_module
    custom_module = custom_modules.Module(
        MODULE_NAME, 'Provides library to register nptel related assets/code',
        global_routes, nptel_routes)
    return custom_module
