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

"""Contain classes to run deferred tasks."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import os
import json
import jinja2

from models import transforms

from modules.programming_assignments import base
from modules.programming_assignments import reevaluator
from modules.programming_assignments import prog_models
from modules.programming_assignments import test_run
from modules.scoring import base as scoring_base

from google.appengine.api import namespace_manager

class ProgAssignmentDashboardHandler(base.ProgAssignment):
    """Handler for prog assignment."""

    @classmethod
    def display_html(cls, handler):
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
        template_value['reeval_units'] = units
        template_value['submit_xsrf_token'] = handler.create_xsrf_token(
            cls.REEVAL_ACTION)
        template_value['reevaluate_url'] = handler.get_action_url(
            cls.REEVAL_ACTION)

        return jinja2.utils.Markup(
            handler.get_template(
                'templates/reevaluate_form.html',
                [os.path.dirname(__file__)]).render(template_value))

    @classmethod
    def confirm_reevaluation_page(cls, handler):
        course = handler.get_course()
        unit_id = handler.request.get('unit_id')
        unit = course.find_unit_by_id(str(unit_id))
        template_value = {}
        if not unit:
            handler.redirect(handler.get_action_url(
                cls.DASHBOARD_NAV, extra_args={
                    'tab': cls.DASHBOARD_REEVALUATION_TAB}))
            return
        else:
            template_value['unit'] = unit

        template_value['submit_xsrf_token'] = handler.create_xsrf_token(
            cls.REEVAL_CONFIRMED_ACTION)
        template_value['reevaluate_url'] = handler.get_action_url(
            cls.REEVAL_CONFIRMED_ACTION)

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/reevaluate_confirmation_form.html',
                [os.path.dirname(__file__)]).render(template_value))
        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=scoring_base.ScoringBase.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_REEVALUATION_TAB)

    @classmethod
    def reevalaute_assignment(cls, handler):
        course = handler.get_course()
        unit_id = handler.request.get('unit_id')
        unit = course.find_unit_by_id(str(unit_id))

        if not unit or 'Cancel' == handler.request.get('submit'):
            handler.redirect(
                handler.get_action_url(
                    scoring_base.DASHBOARD_NAV,
                    extra_args={'tab': cls.DASHBOARD_REEVALUATION_TAB}))
            return

        job = reevaluator.ReevaluateSubmission(course.app_context, unit.unit_id)
        job.submit()

        template_value = {}
        template_value['unit'] = unit
        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/reevaluate_confirmation.html',
                [os.path.dirname(__file__)]).render(template_value))
        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=scoring_base.ScoringBase.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_REEVALUATION_TAB)


class ProgAssignmentDownloadDashboardHandler(base.ProgAssignment):
    """Handler for prog assignment downloads."""

    @classmethod
    def display_html(cls, handler):
        course = handler.get_course()
        tab = handler.request.get('tab')

        if not course:
            return
        has_programming_assignments = False
        for unit in course.get_units():
            if not unit.is_custom_unit():
                continue
            if cls.UNIT_TYPE_ID == unit.custom_unit_type:
                has_programming_assignments = True

        template_value = {}
        template_value['download_units'] = has_programming_assignments
        template_value['submit_xsrf_token'] = handler.create_xsrf_token(
            cls.DOWNLOAD_ACTION)
        template_value['download_url'] = handler.get_action_url(
            cls.DOWNLOAD_ACTION)
        return jinja2.utils.Markup(
            handler.get_template(
                'templates/pog_assignment_download_form.html',
                [os.path.dirname(__file__)]).render(template_value))

    @classmethod
    def download_assignment(cls, handler):
        course = handler.get_course()

        if 'Cancel' == handler.request.get('submit'):
            handler.redirect(
                handler.get_action_url(
                    cls.DASHBOARD_NAV,
                    extra_args={'tab': cls.DASHBOARD_DOWNLOAD_TAB}))
            return

        handler.response.headers['Content-Disposition'] = (
            'attachment; filename="course.txt"')
        output = {'course_name': str(namespace_manager.get_namespace())}
        output['units'] = []
        for unit in course.get_units():
            if cls.UNIT_TYPE_ID == unit.custom_unit_type:
                content = cls.get_content(course, unit)
                if not content:
                    continue
                content['title'] = str(unit.title)
                content['pa_id'] = str(unit.properties.get(cls.PA_ID_KEY))
                output['units'].append(content)
        handler.response.out.write(output)

class ProgAssignmentTestRunHandler(base.ProgAssignment):
    """Handler for prog assignment test runs"""

    @classmethod
    def display_html(cls, handler):
        """Landing page for viewing programming assignment test runs"""

        course = handler.get_course()
        units = course.get_units()
        programming_assignments = [
            unit for unit in units
            if unit.custom_unit_type == base.ProgAssignment.UNIT_TYPE_ID
        ]

        template_value = {
            'programming_assignments': programming_assignments
        }

        return jinja2.utils.Markup(
            handler.get_template(
                'templates/prog_assignment_test_run_form.html',
                [os.path.dirname(__file__)]).render(template_value))

    @classmethod
    def get_show_results(cls, handler):
        """
        GET endpoint to show the details of the latest run of a programming
        assignment
        """
        course = handler.get_course()
        pa_id = handler.request.get('pa_id')
        try:
            pa_id = int(pa_id)
        except ValueError:
            # TODO(rthakker) return bad request
            handler.render_page({
                'page_title': 'qwe',
                'main_content': 'Bad Request'
            }, in_action='mentor', in_tab='download')
            return

        programming_assignment = course.find_unit_by_id(pa_id)
        if not programming_assignment:
            # TODO(rthakker) return 404
            handler.render_page({
                'page_title': 'qwe',
                'main_content': '404'
            }, in_action='mentor', in_tab='download')
            return

        template_value = {
            'programming_assignment': programming_assignment
        }
        template_value['pa_test_run_details'] = {}
        student = course.get_or_create_bot_student()

        # Load the latest evaluation results
        pa_test_run_details = (
            prog_models.ProgrammingAssignmentTestRunEntity
            .get_by_pa_id(pa_id))

        if pa_test_run_details:
            pa_test_run_details = transforms.loads(pa_test_run_details.data)

        if not pa_test_run_details:
            # TODO(rthakker) return 404
            template_file = 'prog_assignment_test_run_details.html'
            content = jinja2.utils.Markup(
                handler.get_template(
                    template_file, [os.path.dirname(__file__) + '/templates']
                ).render(template_value))
            handler.render_page({
                'page_title': 'qwe',
                'main_content': content
            }, in_action='mentor', in_tab='download')
            return

        content_dict = base.ProgAssignment.get_content(
            course, programming_assignment)

        for lang, lang_dict in pa_test_run_details.iteritems():
            public_assignment_dict = (
                test_run.ProgrammingAssignmentTestRun
                .get_assignment_template_value(
                    lang_dict['public'], content_dict))

            private_assignment_dict = (
                test_run.ProgrammingAssignmentTestRun
                .get_assignment_template_value(
                    lang_dict['private'], content_dict))
            template_value['pa_test_run_details'][lang] = {
                'public': public_assignment_dict,
                'private': private_assignment_dict
            }

        template_file = 'prog_assignment_test_run_details.html'
        content = jinja2.utils.Markup(
            handler.get_template(
                template_file, [os.path.dirname(__file__) + '/templates']
            ).render(template_value))

        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_TEST_RUN_TAB)
