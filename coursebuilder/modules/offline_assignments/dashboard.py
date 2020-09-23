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

"""Contain classes for the UI of bulk scoring."""

import os
import jinja2
import csv
import StringIO

from models import models
from models import transforms
from models import roles

from modules.offline_assignments import base
from modules.offline_assignments import assignment

__authors__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

class OfflineAssignmentDashboardHandler(base.OfflineAssignmentBase):
    """Dashboard Handler for Offline Assignment"""

    @classmethod
    def display_html(cls, handler):
        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Unauthorized'
            })
            return

        course = handler.get_course()
        if not course:
            return
        units = []
        for unit in course.get_units():
            if not unit.is_custom_unit():
                continue
            if cls.UNIT_TYPE_ID == unit.custom_unit_type:
                units.append(unit)

        template_value = {}
        template_value['offline_assignments'] = units
        template_value['offline_assignment_url'] = (
            handler.get_action_url(cls.OFFLINE_ASSIGNMENT_DETAILS_ACTION))

        return jinja2.utils.Markup(
            handler.get_template(
                'templates/list_offline_assignment.html',
                [os.path.dirname(__file__)]).render(template_value))

    @classmethod
    def get_assignment_scores(cls, handler):
        """GET endpoint to view scores of a particular assignment"""

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Unauthorized'
            })
            return

        key = handler.request.get('key', '')
        if not key.strip():
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Bad Request: no "key" parameter provided'
            }, in_action=cls.DASHBOARD_DEFAULT_ACTION, in_tab=cls.DASHBOARD_TAB)
            return

        course = handler.get_course()
        if not course:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Course not found'
            }, in_action=cls.DASHBOARD_DEFAULT_ACTION, in_tab=cls.DASHBOARD_TAB)
            return

        unit = course.find_unit_by_id(key)
        if not unit:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Offline Assignment not found'
            }, in_action=cls.DASHBOARD_DEFAULT_ACTION, in_tab=cls.DASHBOARD_TAB)
            return

        students = models.Student.all().fetch(None)
        filtered_students = []
        scores = []
        for student in students:
            if student.scores:
                student_scores = transforms.loads(student.scores)
                if student_scores:
                    score = student_scores.get(key)
                    if score is not None:
                        filtered_students.append(student)
                        scores.append(score)

        template_value = dict()
        template_value['students'] = filtered_students
        template_value['scores'] = scores
        template_value['unit'] = unit
        template_value['back_url'] = handler.get_action_url(
            cls.DASHBOARD_DEFAULT_ACTION)
        template_value['score_offline_assignment_url'] = (
            handler.get_action_url(cls.SCORE_OFFLINE_ASSIGNMENT_ACTION))

        template_file = 'offline_assignment_details.html'
        content = jinja2.utils.Markup(
            handler.get_template(
                template_file, [os.path.dirname(__file__) + '/templates']
            ).render(template_value))

        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_DEFAULT_ACTION,
            in_tab=cls.DASHBOARD_TAB)

    @classmethod
    def get_bulk_score(cls, handler):
        """GET endpoint to show editor for bulk scoring"""

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Unauthorized'
            })
            return

        assessment_id = handler.request.get('assessment_id')
        if not assessment_id and assessment_id.isdigit():
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Invalid unit ID'
            })
            return

        template_value = dict()

        course = handler.get_course()
        unit = course.find_unit_by_id(assessment_id)
        if not unit:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Assessment not found'
            })
            return

        template_value['assessment_id'] = assessment_id

        template_file = 'bulk_score_dashboard_view.html'

        template_value['back_url'] = handler.get_action_url(
            cls.DASHBOARD_DEFAULT_ACTION)
        template_value['form_action'] = cls.SCORE_OFFLINE_ASSIGNMENT_ACTION
        template_value['bulk_score_xsrf_token'] = (
            handler.create_xsrf_token(cls.SCORE_OFFLINE_ASSIGNMENT_ACTION))

        content = jinja2.utils.Markup(
            handler.get_template(
                template_file, [os.path.dirname(__file__) + '/templates']
            ).render(template_value))

        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_DEFAULT_ACTION,
            in_tab=cls.DASHBOARD_TAB)

    @classmethod
    def post_bulk_score(cls, handler):
        """POST endpoint to save bulk scores for a particular course"""

        csv_text = handler.request.get('scores_csv').strip()
        course = handler.get_course()
        unit_id = handler.request.get('assessment_id')
        unit = course.find_unit_by_id(unit_id)
        if not unit:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Assessment not found'
            })
            return

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Unauthorized'
            })
            return

        if not csv_text:
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Bad Request: no data provided'
            }, in_action=cls.DASHBOARD_DEFAULT_ACTION, in_tab=cls.DASHBOARD_TAB)
            return

        errors = []
        reader = csv.reader(StringIO.StringIO(csv_text))

        # Filter out empty rows
        reader = [r for r in reader if ''.join(r).strip()]

        assignment.OfflineAssignmentHandler.bulk_score_by_unit(
            course, unit, reader, errors)

        template_file = 'bulk_score_result.html'
        template_value = dict()
        template_value['errors'] = errors
        template_value['back_url'] = handler.get_action_url(
            cls.DASHBOARD_DEFAULT_ACTION)
        content = jinja2.utils.Markup(
            handler.get_template(
                template_file, [os.path.dirname(__file__) + '/templates']
            ).render(template_value))

        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_DEFAULT_ACTION,
            in_tab=cls.DASHBOARD_TAB)
