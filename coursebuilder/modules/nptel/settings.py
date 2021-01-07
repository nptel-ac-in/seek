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

"""Classes and methods for NPTEL Settings."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


from common import tags
from common.schema_fields import FieldArray
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from models import courses
from modules.courses import settings as course_settings
from modules.nptel import service_account
from modules.subjective_assignments import drive_service


NPTEL_SECTION = 'nptel'
OAUTH_SECTION = '%s:oauth' % NPTEL_SECTION

DUMP_FOLDER_ID = 'dump_folder_id'

def dump_folder_validator(value, errors):
    if not value:
        return True
    if value.strip():
        return drive_service.DriveManager.is_drive_folder_accessible(
            value, errors)
    return True


def nptel_key(key):
    return '%s:%s' % (NPTEL_SECTION, key)

class NptelSettings(object):
    dump_folder = SchemaField(nptel_key(DUMP_FOLDER_ID),
                    'Google Drive Folder Id For Dumps', 'string', optional=True,
                    description="""Id of Google Drive folder where all
                    course dumps will be stored.""",
                    validator=dump_folder_validator)


    @classmethod
    def get_fields(cls):
        nptel_fields = set()
        nptel_fields.add(lambda c: cls.dump_folder)
        return nptel_fields


    @classmethod
    def register(cls):
        courses.Course.OPTIONS_SCHEMA_PROVIDERS[
            NPTEL_SECTION] += cls.get_fields()
        course_settings.CourseSettingsHandler.register_settings_section(
                                        NPTEL_SECTION, title='NPTEL')


    @classmethod
    def unregister(cls):
        for field in cls.get_fields():
            courses.Course.OPTIONS_SCHEMA_PROVIDERS[
                NPTEL_SECTION].remove(field)
            courses.Course.OPTIONS_SCHEMA_PROVIDERS[
                NPTEL_THEME_SECTION].remove(field)
