# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Tests the child orde."""

__author__ = 'Thejesh GN (tgn@google.com)'

from common import crypto
from models import courses
from tests.functional import actions

COURSE_NAME = 'unit_test'
COURSE_TITLE = 'Unit Test'
NAMESPACE = 'ns_%s' % COURSE_NAME
ADMIN_EMAIL = 'admin@foo.com'
STUDENT_EMAIL = 'foo@foo.com'
BASE_URL = '/' + COURSE_NAME
UNIT_URL_PREFIX = BASE_URL + '/unit?unit='


class UnitChildrenOrderTest(actions.TestBase):

    def setUp(self):
        super(UnitChildrenOrderTest, self).setUp()

        app_context = actions.simple_add_course(COURSE_NAME, ADMIN_EMAIL,
                                                COURSE_TITLE)
        self.course = courses.Course(None, app_context=app_context)

        self.unit = self.course.add_unit()
        self.unit.title = 'Unit 1'
        self.unit.availability = courses.AVAILABILITY_AVAILABLE

        self.top_assessment = self.course.add_assessment(self.unit)
        self.top_assessment.title = 'First Assessment'
        self.top_assessment.html_content = 'content of first assessment'
        self.top_assessment.availability = courses.AVAILABILITY_AVAILABLE
        self.unit.pre_assessment = self.top_assessment.unit_id

        self.lesson_one = self.course.add_lesson(self.unit)
        self.lesson_one.title = 'Lesson One'
        self.lesson_one.objectives = 'body of lesson one'
        self.lesson_one.availability = courses.AVAILABILITY_AVAILABLE

        self.lesson_two = self.course.add_lesson(self.unit)
        self.lesson_two.title = 'Lesson Two'
        self.lesson_two.objectives = 'body of lesson two'
        self.lesson_two.availability = courses.AVAILABILITY_AVAILABLE

        self.bottom_assessment = self.course.add_assessment(self.unit)
        self.bottom_assessment.title = 'Last Assessment'
        self.bottom_assessment.html_content = 'content of last assessment'
        self.bottom_assessment.availability = courses.AVAILABILITY_AVAILABLE
        self.unit.post_assessment = self.bottom_assessment.unit_id

        self.course.save()

        actions.login(STUDENT_EMAIL)
        actions.register(self, STUDENT_EMAIL, COURSE_NAME)


    def test_default_order(self):
        expected_children_order =  [{'id': 1, 'children': [{'section': 'sub_unit', 'id': 2, 'children': []},
                                    {'section': 'lesson', 'id': 3, 'children': []},
                                    {'section': 'lesson', 'id': 4, 'children': []},
                                    {'section': 'sub_unit', 'id': 5, 'children': []}]}]
        self.assertEqual(expected_children_order, self.course.get_children_order())

    def test_two_units(self):
        unit2 = self.course.add_unit()
        unit2.title = 'Unit 2'
        unit2.availability = courses.AVAILABILITY_AVAILABLE
        self.course.save()

        expected_children_order =  [{'id': 1, 'children': [{'section': 'sub_unit', 'id': 2, 'children': []},
                                                            {'section': 'lesson', 'id': 3, 'children': []},
                                                            {'section': 'lesson', 'id': 4, 'children': []},
                                                            {'section': 'sub_unit', 'id': 5, 'children': []}]},
                                   {'id': 6, 'children': []}]
        self.assertEqual(expected_children_order, self.course.get_children_order())


    def test_add_assessment_to_second_unit(self):
        unit2 = self.course.add_unit()
        unit2.title = 'Unit 2'
        unit2.availability = courses.AVAILABILITY_AVAILABLE
        assessment = self.course.add_assessment(unit2)
        assessment.title = ' Assessment'
        assessment.availability = courses.AVAILABILITY_AVAILABLE
        self.course.save()
        expected_children_order =  [{'id': 1, 'children': [{'section': 'sub_unit', 'id': 2, 'children': []},
                                        {'section': 'lesson', 'id': 3, 'children': []},
                                        {'section': 'lesson', 'id': 4, 'children': []},
                                        {'section': 'sub_unit', 'id': 5, 'children': []}]},
                                {'id': 6, 'children': [{'section': 'sub_unit', 'id': 7, 'children': []}]}]
        self.assertEqual(expected_children_order, self.course.get_children_order())
