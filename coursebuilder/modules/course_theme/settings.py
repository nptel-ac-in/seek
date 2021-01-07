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

"""Classes and methods for Theme Settings."""

__author__ = 'Thejesh GN (tgn@google.com)'

from common import tags
from common.schema_fields import FieldArray
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from models import courses
from modules.courses import settings as course_settings

THEME_SECTION = 'course_theme'

def course_theme_key(key):
    return '%s:%s' % (THEME_SECTION, key)

class CourseThemeSettings(object):
    theme_opts = FieldRegistry('THEME', '')

    theme_opts_background_color = SchemaField(
    course_theme_key('background_color'), 'Header Background Color', 'string',
    optional=True,
    description='Color of the header background on the course homepage. Default is a90909')

    theme_opts_logo_url=SchemaField(
    course_theme_key('logo_url'), 'Header logo url', 'string',
    optional=True,
    description='URL of the logo in course page')

    theme_opts_logo_alt_text=SchemaField(
    course_theme_key('logo_alt_text'), 'Header logo alternate text', 'string',
    optional=True,
    description='Header logo alternate text')


    @classmethod
    def get_fields(cls):
        theme_fields = set()
        theme_fields.add(lambda c: cls.theme_opts_logo_alt_text)
        theme_fields.add(lambda c: cls.theme_opts_background_color)
        theme_fields.add(lambda c: cls.theme_opts_logo_url)
        return theme_fields


    @classmethod
    def register(cls):
        courses.DEFAULT_COURSE_YAML_DICT[THEME_SECTION] = dict()
        courses.DEFAULT_COURSE_YAML_DICT[THEME_SECTION]['background_color'] = 'a90909'
        courses.DEFAULT_COURSE_YAML_DICT[THEME_SECTION]['logo_url'] = ''
        courses.DEFAULT_COURSE_YAML_DICT[THEME_SECTION]['logo_alt_text'] = ''

        courses.DEFAULT_EXISTING_COURSE_YAML_DICT[THEME_SECTION] = { 
            'background_color': 'a90909' }
        courses.DEFAULT_EXISTING_COURSE_YAML_DICT[THEME_SECTION] = { 
            'logo_url': '' }
        courses.DEFAULT_EXISTING_COURSE_YAML_DICT[THEME_SECTION] = { 
            'logo_alt_text': '' }

        courses.Course.OPTIONS_SCHEMA_PROVIDERS[
        THEME_SECTION] += cls.get_fields()
        course_settings.CourseSettingsHandler.register_settings_section(
                                        THEME_SECTION, title='Course Theme ')    

    @classmethod
    def unregister(cls):
        for field in cls.get_fields():
            courses.Course.OPTIONS_SCHEMA_PROVIDERS[
                THEME_SECTION].remove(field)
