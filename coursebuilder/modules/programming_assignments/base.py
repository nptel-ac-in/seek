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


import collections
import urllib

from models import transforms
from models import vfs
from tools import verify

from google.appengine.ext import db


class ProgAssignment(object):
    UNIT_TYPE_ID = 'com.google.coursebuilder.programming_assignment'
    UNIT_URL = '/progassignment'
    PA_ID_KEY = 'PA'
    NAME = 'Programming Assignments'
    SETTINGS_SECTION = 'programming_assignments'
    DASHBOARD_NAV = 'programming_assignments'
    DASHBOARD_REEVALUATION_TAB = 'reevaluation'
    REEVAL_ACTION = 'reevaluate_programming_assignment'
    REEVAL_CONFIRMED_ACTION = 'reevaluate_programming_assignment_confirmed'
    DASHBOARD_DOWNLOAD_TAB = 'download'
    DASHBOARD_TEST_RUN_TAB = 'test_run'
    TEST_RUN_ACTION = 'programming_assignment_test_run'
    DOWNLOAD_ACTION = 'download_programming_assignment'

    PROG_LANG_C = 'c'
    PROG_LANG_CPP = 'cpp'
    PROG_LANG_JAVA = 'java'
    PROG_LANG_PY = 'py'
    PROG_LANG_PY3 = 'py3'
    PROG_LANG_VERILOG = 'verilog'
    PROG_LANG_PERL = 'pl'
    PROG_LANG_HASKELL = 'hs'


    ALLOWED_LANGUAGES = [PROG_LANG_C, PROG_LANG_CPP, PROG_LANG_JAVA,
                         PROG_LANG_PY, PROG_LANG_PY3, PROG_LANG_VERILOG,
                         PROG_LANG_PERL, PROG_LANG_HASKELL]
    LANGS_WHICH_REQUIRE_EXPLICIT_FILENAME = [PROG_LANG_JAVA]
    PROG_LANG_FILE_MAP = collections.OrderedDict([
        (PROG_LANG_C, 'C'),
        (PROG_LANG_CPP, 'C++'),
        (PROG_LANG_JAVA, 'Java'),
        (PROG_LANG_PY, 'Python2'),
        (PROG_LANG_PY3, 'Python3'),
        (PROG_LANG_VERILOG, 'Verilog'),
        (PROG_LANG_PERL, 'Perl'),
        (PROG_LANG_HASKELL, 'Haskell')])

    PROG_LANG_SYNTAX_MAP = {
        PROG_LANG_C: 'clike',
        PROG_LANG_CPP: 'clike',
        PROG_LANG_JAVA: 'clike',
        PROG_LANG_PY: 'python',
        PROG_LANG_PY3: 'python',
        PROG_LANG_VERILOG: 'verilog',
        PROG_LANG_PERL:'perl',
        PROG_LANG_HASKELL:'haskell'}

    PROG_LANG_SYNTAX_MODE = {
        PROG_LANG_C: 'text/x-csrc',
        PROG_LANG_CPP: 'text/x-c++src',
        PROG_LANG_JAVA: 'text/x-java',
        PROG_LANG_PY: 'text/x-python',
        PROG_LANG_PY3: 'text/x-python',
        PROG_LANG_VERILOG: 'text/x-verilog',
        PROG_LANG_PERL:'text/x-perl',
        PROG_LANG_HASKELL:'text/x-haskell'}

    ALLOWED_LANGAUGES_XML_TAG = 'allowed_languages'


    @classmethod
    def _get_content(cls, course, filename):
        """Returns programming assignment content."""
        content = course.get_file_content(filename)
        return transforms.loads(content) if content else dict()

    @classmethod
    def _set_content(cls, course, filename, content):
        course.set_file_content(
            filename, vfs.string_to_stream(unicode(transforms.dumps(content))))

    @classmethod
    def get_content_filename(cls, unit, create_new=False):
        assert unit
        assert unit.custom_unit_type == cls.UNIT_TYPE_ID
        if create_new:
            return 'prog_assignments/assignment-%s.data' % unit.unit_id
        if 'filename' in unit.properties:
            return unit.properties['filename']
        return 'assets/js/prog-assignment-%s.js' % unit.unit_id

    @classmethod
    def get_content(cls, course, unit):
        """Returns programming assignment content."""
        filename = cls.get_content_filename(unit)
        return cls._get_content(course, filename)

    @classmethod
    def set_content(cls, course, unit, content):
        filename = cls.get_content_filename(unit, create_new=True)
        unit.properties['filename'] = filename
        cls._set_content(course, filename, content)

    @classmethod
    def delete_content(cls, course, unit):
        filename = cls.get_content_filename(unit)
        return course.delete_file(filename)

    @classmethod
    def get_course_settings(cls, course):
        """Returns programming assignment content."""
        return course.app_context.get_environ().get(cls.SETTINGS_SECTION, {})

    @classmethod
    def get_public_url(cls, unit):
        args = {}
        args['name'] = unit.unit_id
        return '%s?%s' % (cls.UNIT_URL, urllib.urlencode(args))

    @classmethod
    def get_test_case_id_state_filename(cls):
        """Stores the next free id of for test cases."""
        return '/prog-assignment-state.txt'

    @classmethod
    def index_to_int(cls, index):
        s = 0
        pow = 1
        for letter in index[::-1]:
            d = int(letter,36) - 9
            s += pow * d
            pow *= 26
        return s

    @classmethod
    def _get_max_pa_id(cls, course, units):
        max_pa_id = 0
        for u in units:
            if u.type != verify.UNIT_TYPE_CUSTOM:
                continue
            if u.custom_unit_type != cls.UNIT_TYPE_ID:
                continue
            str_pa_id = u.properties.get(cls.PA_ID_KEY)
            if not str_pa_id:
               continue
            pa_id = cls.index_to_int(str_pa_id)
            if pa_id > max_pa_id:
                max_pa_id = pa_id
            pa_id = cls._get_max_pa_id(course, course.get_subunits(u.unit_id))
            if pa_id > max_pa_id:
                max_pa_id = pa_id
        return max_pa_id

    @classmethod
    def get_test_case_id_state(cls, course):
        filename = cls.get_test_case_id_state_filename()
        data_dict = cls._get_content(course, filename)
        if cls.PA_ID_KEY in data_dict:
            return data_dict
        data_dict[cls.PA_ID_KEY] = cls._get_max_pa_id(course, course.get_units())
        return data_dict

    @classmethod
    def set_test_case_id_state(cls, course, data):
        filename = cls.get_test_case_id_state_filename()
        cls._set_content(course, filename, data)

    @classmethod
    @db.transactional(xg=True)
    def get_next_test_suite_id(cls, course):
        data_dict = cls.get_test_case_id_state(course)
        pa_id = data_dict.get(cls.PA_ID_KEY, 0)
        pa_id += 2
        data_dict[cls.PA_ID_KEY] = pa_id
        cls.set_test_case_id_state(course, data_dict)
        return pa_id
