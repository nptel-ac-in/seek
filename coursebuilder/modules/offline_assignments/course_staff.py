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

"""Classes and methods to serving programming assignment."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import os
import csv
import StringIO

from models import models
from models import transforms
from common import jinja_utils

from modules.offline_assignments import base
from modules.offline_assignments import assignment
from modules.course_staff import course_staff

class OfflineAssignmentsCourseStaffBase(base.OfflineAssignmentBase):
    """Metadata for Course Staff related handlers for Offline Assignment"""
    LIST_ACTION = 'list_offline'
    EVALUATE_ACTION = 'evaluate_offline'
    POST_SCORE_ACTION = 'score_offline'

class OfflineAssignmentsCourseStaffHandler(OfflineAssignmentsCourseStaffBase):

    @classmethod
    def post_score_offline(cls, handler):
        user = handler.current_user
        evaluator = handler.evaluator

        errors = list()

        if not evaluator.can_grade:
            handler.error(404)
            errors.append('Failed')
            return

        assessment_id = handler.request.get('assessment_id')
        if not assessment_id:
            handler.error(404)
            errors.append('Failed')
            return

        course = handler.get_course()
        unit = course.find_unit_by_id(assessment_id)
        if not unit:
            handler.error(404)
            errors.append('Failed')
            return

        csv_text = handler.request.get('scores_csv').strip()
        if not csv_text:
            handler.error(400)
            errors.append('Failed')
            return

        if not errors:
            reader = csv.reader(StringIO.StringIO(csv_text))

            # Filter out empty rows
            reader = [r for r in reader if ''.join(r).strip()]

            assignment.OfflineAssignmentHandler.bulk_score_by_unit(
                course, unit, reader, errors)

        handler.template_value['errors'] = errors
        handler.template_value['unit'] = unit

        handler.template_value['CUSTOM_UNITS'] = course_staff.CourseStaff.CUSTOM_UNITS

        template_file = 'templates/course_staff/evaluation_result_offline.html'
        template = jinja_utils.get_template(
            template_file, [
                os.path.join(
                    os.getcwd(), 'modules/offline_assignments/templates'),
                os.path.dirname(__file__)])
        handler.render(template)

    @classmethod
    def get_list_offline(cls, handler):
        assignment_name = handler.request.get('name')
        course = handler.get_course()
        unit = course.find_unit_by_id(assignment_name)
        if not unit:
            handler.error(404)
            handler.redirect('/course')
            return

        if handler.can_evaluate(unit) or True:

            students = models.Student.all().fetch(None)
            filtered_students = []
            scores = []
            for student in students:
                if student.scores:
                    student_scores = transforms.loads(student.scores)
                    if student_scores:
                        score = student_scores.get(assignment_name)
                        if score is not None:
                            filtered_students.append(student)
                            scores.append(score)

            handler.template_value['students'] = filtered_students
            handler.template_value['scores'] = scores
            handler.template_value['unit'] = unit
            handler.template_value['back_url'] = ''

            handler.template_value['score_offline_assignment_url'] = (
                'course_staff?action=evaluate_offline')

            handler.template_value['CUSTOM_UNITS'] = course_staff.CourseStaff.CUSTOM_UNITS

            template_file = ('templates/course_staff/evaluations_offline.html')
            template = jinja_utils.get_template(
                template_file, [os.path.dirname(__file__)])
            handler.render(template)

    @classmethod
    def get_evaluate_offline(cls, handler):
        assessment_id = handler.request.get('assessment_id')
        if not assessment_id:
            handler.error(404)
            handler.redirect('/course_staff')
            return

        course = handler.get_course()
        unit = course.find_unit_by_id(assessment_id)
        if not unit:
            handler.error(404)
            handler.redirect('/course_staff')

        handler.template_value['form_uri'] = 'course_staff'
        handler.template_value['form_action'] = 'score_offline'
        handler.template_value['score_offline_xsrf_token'] = (
            handler.create_xsrf_token('score_offline'))
        handler.template_value['unit'] = unit

        handler.template_value['CUSTOM_UNITS'] = course_staff.CourseStaff.CUSTOM_UNITS

        template_file = 'templates/course_staff/evaluate_offline.html'
        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__)])
        handler.render(template)
