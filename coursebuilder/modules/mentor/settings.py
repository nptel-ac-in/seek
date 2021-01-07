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

"""Classes and methods for Mentor Settings."""

__author__ = 'Thejesh GN (tgn@google.com)'

from common.schema_fields import FieldArray
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from models import courses
from modules.mentor import base
from modules.courses import settings as course_settings


def mentor_key(key):
    return '%s:%s' % (base.MentorBase.MENTOR_SECTION, key)

class MentorSettings(base.MentorBase):
    enable_mentor_support = SchemaField(
        mentor_key(base.MentorBase.ENABLE_KEY),'Enable Mentor Support', 'boolean')


    @classmethod
    def get_fields(cls):
        mentor_fields = set()
        mentor_fields.add(lambda c: cls.enable_mentor_support)
        return mentor_fields

    @classmethod
    def register(cls):
        courses.DEFAULT_COURSE_YAML_DICT[cls.MENTOR_SECTION] = dict()
        courses.DEFAULT_COURSE_YAML_DICT[cls.MENTOR_SECTION]['enable_mentor_support'] = False
        courses.DEFAULT_EXISTING_COURSE_YAML_DICT[cls.MENTOR_SECTION] = { 
            'enable_mentor_support': False }
        courses.Course.OPTIONS_SCHEMA_PROVIDERS[
            cls.MENTOR_SECTION] += cls.get_fields()
        course_settings.CourseSettingsHandler.register_settings_section(
                                        cls.MENTOR_SECTION, title='Mentor')   
    @classmethod
    def unregister(cls):
        for field in cls.get_fields():
            courses.Course.OPTIONS_SCHEMA_PROVIDERS[
                cls.MENTOR_SECTION].remove(field)
