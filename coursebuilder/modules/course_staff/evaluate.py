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

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import datetime
import os
import logging

from common import crypto
from common import jinja_utils
from controllers.utils import BaseHandler
from controllers.utils import ReflectiveRequestHandler

import course_staff

class EvaluationHandler(BaseHandler, ReflectiveRequestHandler):
    """Handler for prog assignment."""

    default_action = 'summary'
    get_actions = [default_action]
    post_actions = []
    _custom_get_actions = {}
    _custom_post_actions = {}

    @classmethod
    def add_custom_get_action(cls, action, handler, overwrite=False):
        """Adds a custom get action"""
        if not action:
            logging.critical('Action not specified. Ignoring')
            return

        if not handler:
            logging.critical('For action %s Handler cannot be null', action)
            return

        if ((action in cls._custom_get_actions or action in cls.get_actions)
                and not overwrite):
            logging.critical('action: %s already exists. Ignoring.', action)

        cls._custom_get_actions[action] = handler

    @classmethod
    def remove_custom_get_action(cls, action):
        if action in cls._custom_get_actions:
            cls._custom_get_actions.pop(action)

    @classmethod
    def add_custom_post_action(cls, action, handler, overwrite=False):
        if not handler or not action:
            logging.critical('Action or handler can not be null.')
            return

        if ((action in cls._custom_post_actions or action in cls.post_actions)
                and not overwrite):
            logging.critical('action : %s already exists. Ignoring.', action)
            return

        cls._custom_post_actions[action] = handler

    @classmethod
    def remove_custom_post_action(cls, action):
        if action in cls._custom_post_actions:
            cls._custom_post_actions.pop(action)

    def custom_get_handler(self):
        """Renders Enabled Custom Manual Evaluator view."""
        action = self.request.get('action')
        user = self.personalize_page_and_get_user()
        if not user:
            self.error(404)
            self.redirect('/course')
            return
        evaluator = course_staff.CourseStaff.get(user.user_id())
        if not evaluator:
            self.error(404)
            self.redirect('/course')
            return

        # Render the template
        self.template_value['evaluator'] = evaluator
        self.template_value['navbar'] = {'course': True}
        self.template_value['base'] = self.get_template('base_course.html')
        self.template_value['course_navbar'] = self.get_template('course_navbar.html')
        self.template_value['CUSTOM_UNITS'] = course_staff.CourseStaff.CUSTOM_UNITS

        template_file = 'templates/custom_action_template.html'
        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__)])
        # self.render(template)
        self.template_value['base_evaluator'] = template

        # Store the user and evaluator for future use
        self.current_user = user
        self.evaluator = evaluator

        # Pass on control to the custom handler
        self._custom_get_actions[action](self)

    def custom_post_handler(self):
        """Edit Custom Custom Manual Evaluator view."""
        action = self.request.get('action')
        user = self.personalize_page_and_get_user()
        if not user:
            self.error(404)
            self.redirect('/course')
            return
        evaluator = course_staff.CourseStaff.get(user.user_id())
        if not evaluator:
            self.error(404)
            self.redirect('/course')
            return

        # Render the template
        self.template_value['evaluator'] = evaluator
        self.template_value['navbar'] = {'course': True}
        self.template_value['base'] = self.get_template('base_course.html')
        self.template_value['course_navbar'] = self.get_template('course_navbar.html')

        self.template_value['CUSTOM_UNITS'] = course_staff.CourseStaff.CUSTOM_UNITS

        template_file = 'templates/custom_action_template.html'
        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__)])
        self.template_value['base_evaluator'] = template

        # Store the user and evaluator for future use
        self.current_user = user
        self.evaluator = evaluator

        # Pass on control to the custom handler
        self._custom_post_actions[action](self)

    def get(self):
        """Adding support for custom get actions"""
        action = self.request.get('action')
        if action in self._custom_get_actions:
            return self.custom_get_handler()
        return super(EvaluationHandler, self).get()

    def post(self):
        """Adding support for custom post actions"""
        action = self.request.get('action')
        if action in self._custom_post_actions:
            # Each POST request must have a valid XSRF token.
            xsrf_token = self.request.get('xsrf_token')
            if not crypto.XsrfTokenManager.is_xsrf_token_valid(
                    xsrf_token, action):
                self.error(403)
                return
            return self.custom_post_handler()
        return super(EvaluationHandler, self).post()

    @classmethod
    def can_evaluate(cls, unit):
        workflow = unit.workflow
        if workflow.submit_only_once():
            return True
        submission_due_date = workflow.get_submission_due_date()
        if submission_due_date:
            time_now = datetime.datetime.now()
            if time_now > submission_due_date:
                return True
        return False

    def get_summary(self):
        user = self.personalize_page_and_get_user()
        if not user:
            self.error(404)
            self.redirect('/course')
            return
        evaluator = course_staff.CourseStaff.get(user.user_id())
        if not evaluator:
            self.error(404)
            self.redirect('/course')
            return

        self.template_value['evaluator'] = evaluator
        self.template_value['navbar'] = {'course': True}
        self.template_value['base'] = self.get_template('base_course.html')
        self.template_value['course_navbar'] = self.get_template('course_navbar.html')

        self.template_value['CUSTOM_UNITS'] = course_staff.CourseStaff.CUSTOM_UNITS


        template_file = 'summary.html'
        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__)])
        self.render(template)
