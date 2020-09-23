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

"""Classes and methods for Explorer Page Settings."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

from common import tags
from common.schema_fields import FieldArray
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from models import courses
from modules.dashboard import tabs


EXPLORER_SECTION = 'explorer'

def course_explorer_key(key):
    return '%s:%s' % (EXPLORER_SECTION, key)

class CourseExplorerSettings(object):
    blurb = SchemaField(
        course_explorer_key('blurb'), 'Course Abstract', 'html', optional=True,
        description='Text, shown on the course homepage, that explains what '
        'the course is about.',
        extra_schema_dict_values={
            'supportCustomTags': tags.CAN_USE_DYNAMIC_TAGS.value,
            'excludedCustomTags': tags.EditorDenylists.COURSE_SCOPE})
    list_in_explorer = SchemaField(
        course_explorer_key('list_in_explorer'), 'List the course in explorer',
        'boolean')

    registration = SchemaField(
        'reg_form:registration', 'Student Registration', 'string', optional=True,
        select_data=[
            ('NOT_OPEN', 'Not Open'), ('OPENING_SHORTLY', 'Opening Shortly'),
            ('OPEN', 'Open'), ('CLOSED', 'Closed')],
        description='Set registration status for students.')

    closed = SchemaField(
        course_explorer_key('closed'), 'Course Closed', 'boolean', optional=True,
        description='Is course not currently running.')

    @classmethod
    def get_fields(cls):
        course_explorer_fields = set()
        course_explorer_fields.add(lambda c: cls.blurb)
        course_explorer_fields.add(lambda c: cls.list_in_explorer)
        course_explorer_fields.add(lambda c: cls.closed)
        return course_explorer_fields

    @classmethod
    def register(cls):
        courses.DEFAULT_COURSE_YAML_DICT[EXPLORER_SECTION] = dict()
        courses.DEFAULT_COURSE_YAML_DICT[EXPLORER_SECTION]['list_in_explorer'] = True
        courses.DEFAULT_COURSE_YAML_DICT[EXPLORER_SECTION]['blurb'] = ''

        courses.Course.OPTIONS_SCHEMA_PROVIDERS[
            EXPLORER_SECTION] += cls.get_fields()
        courses.Course.OPTIONS_SCHEMA_PROVIDERS[
            courses.Course.SCHEMA_SECTION_REGISTRATION] += [lambda c : cls.registration]
        tabs.Registry.register('settings', 'course_explorer', 'Explorer',
                               EXPLORER_SECTION)

    @classmethod
    def unregister(cls):
        for field in cls.get_fields():
            courses.Course.OPTIONS_SCHEMA_PROVIDERS[
                EXPLORER_SECTION].remove(field)
        courses.Course.OPTIONS_SCHEMA_PROVIDERS[
            courses.Course.SCHEMA_SECTION_REGISTRATION].remove(
                lambda c : cls.registration)
