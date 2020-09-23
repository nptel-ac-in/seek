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
import jinja2

from models import courses
from modules.scoring import base
from modules.scoring import rescorer
from tools import verify

from google.appengine.api import namespace_manager


class ScoringDashboardHandler(base.ScoringBase):
    """Handler for scoring."""

    @classmethod
    def display_html(cls, handler):
        course = handler.get_course()
        if not course:
            return
        units = []
        for unit in course.get_units():
            if verify.UNIT_TYPE_ASSESSMENT == unit.type:
                grader = unit.workflow.get_grader()
                if grader == courses.AUTO_GRADER:
                    units.append(unit)

        template_values = {}
        template_values['rescore_units'] = units
        template_values['submit_xsrf_token'] = handler.create_xsrf_token(
            cls.RESCORE_OBJ_ASSESSMENT_ACTION)
        template_values['rescore_url'] = handler.get_action_url(
            cls.RESCORE_OBJ_ASSESSMENT_ACTION)

        return jinja2.utils.Markup(
            handler.get_template(
                'templates/rescore_form.html',
                [os.path.dirname(__file__)]).render(template_values))

    @classmethod
    def confirm_rescore_page(cls, handler):
        course = handler.get_course()
        unit_id = handler.request.get('unit_id')
        ignore_order = handler.request.get('ignore_order')
        unit = course.find_unit_by_id(str(unit_id))
        template_values = {}
        if not unit:
            handler.redirect(handler.get_action_url(
                cls.DASHBOARD_NAV, extra_args={
                    'tab': cls.DASHBOARD_RESCORING_TAB}))
            return
        else:
            template_values['unit'] = unit
            template_values['ignore_order'] = ignore_order

        template_values['submit_xsrf_token'] = handler.create_xsrf_token(
            cls.RESCORE_OBJ_ASSESSMENT_CONFIRMED_ACTION)
        template_values['rescore_url'] = handler.get_action_url(
            cls.RESCORE_OBJ_ASSESSMENT_CONFIRMED_ACTION)

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/rescore_confirmation_form.html',
                [os.path.dirname(__file__)]).render(template_values))
        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_RESCORING_TAB)

    @classmethod
    def rescore_assignment(cls, handler):
        course = handler.get_course()
        unit_id = handler.request.get('unit_id')
        ignore_order = handler.request.get('ignore_order')
        unit = course.find_unit_by_id(str(unit_id))

        if not unit or 'Cancel' == handler.request.get('submit'):
            handler.redirect(
                handler.get_action_url(
                    cls.DASHBOARD_NAV,
                    extra_args={'tab': cls.DASHBOARD_RESCORING_TAB}))
            return

        job = rescorer.RescorerSubmission(course.app_context, unit.unit_id,
            ignore_order=True if ignore_order =="yes" else False)
        job.submit()

        template_values = {}
        template_values['unit'] = unit
        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/rescore_confirmation.html',
                [os.path.dirname(__file__)]).render(template_values))
        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_RESCORING_TAB)
