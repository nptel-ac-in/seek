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

"""Classes and methods for Programming Assignments Administration."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

from common.schema_fields import FieldArray
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from models import courses
from modules.dashboard import tabs
from modules.programming_assignments import base


def programming_assignment_key(key):
    return '%s:%s' % (base.ProgAssignment.SETTINGS_SECTION, key)

class ProgrammingAssignmentSettings(base.ProgAssignment):
    language_opts = FieldRegistry('Programming Language', '')
    language_opts.add_property(
        SchemaField(
            'language', 'Programming Language', 'string',
            select_data=base.ProgAssignment.PROG_LANG_FILE_MAP.items()))
    language_opts.add_property(
        SchemaField('build', 'Build extra args', 'string', optional=True))
    language_opts.add_property(
        SchemaField('exec', 'Execution extra args', 'string', optional=True))
    language_opts.add_property(
        SchemaField('time_limit', 'Time Limit', 'integer', optional=True))
    language_opts.add_property(
        SchemaField('memory_limit', 'Memory Limit', 'integer', optional=True))
    language_opts.add_property(
        SchemaField('process_limit', 'process Limit', 'integer', optional=True))
    language_opts.add_property(
        SchemaField('compilation_time_limit', 'Compilation Time Limit', 'integer', optional=True))
    language_opts.add_property(
        SchemaField('compilation_memory_limit', 'Compilation Memory Limit', 'integer', optional=True))
    language_opts.add_property(
        SchemaField('compilation_process_limit', 'Compilation process Limit', 'integer', optional=True))
    allowed_languages = FieldArray(
        programming_assignment_key('allowed_languages'),
        'Programming Languages for this Course',
        item_type=language_opts,
        extra_schema_dict_values={
            'sortable': False,
            'listAddLabel': 'Add Language',
            'listRemoveLabel': 'Delete',
            'minItems' : 1})

    @classmethod
    def register(cls):
        programming_settings_fields = set()
        programming_settings_fields.add(lambda c: cls.allowed_languages)
        courses.Course.OPTIONS_SCHEMA_PROVIDERS[
            cls.SETTINGS_SECTION] += programming_settings_fields
        tabs.Registry.register('settings', cls.DASHBOARD_NAV, cls.NAME,
                               cls.SETTINGS_SECTION)

    @classmethod
    def unregister(cls):
        programming_settings_fields = set()
        programming_settings_fields.add(lambda c: cls.allowed_languages)
        for field in programming_settings_fields:
            courses.Course.OPTIONS_SCHEMA_PROVIDERS[
                cls.SETTINGS_SECTION].remove(field)
