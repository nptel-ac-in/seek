# Copyright 2018 Google Inc. All Rights Reserved.
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

"""Contain classes to unlock."""

__author__ = 'Thejesh GN (tgn@google.com)'

import os
import json
import jinja2

from models import courses
from models import transforms
from modules.lockdown import base
from models import roles

from google.appengine.api import namespace_manager

class UnlockDashboardHandler(base.LockdownBase):
    """Handler for prog assignment."""


    @classmethod
    def display_html(cls, handler):
        template_value = {}
        is_super_admin = roles.Roles.is_super_admin()
        template_value['is_super_admin'] = is_super_admin
        if is_super_admin:
            course = handler.get_course()
            if not course:
                return
            units = []
            for unit in course.get_units():
                if not unit.is_assessment():
                    continue
                if unit.is_locked:
                    units.append(unit)

            template_value['locked_units'] = units
            template_value['submit_xsrf_token'] = handler.create_xsrf_token(
                cls.UNLOCK_ACTION)
            template_value['unlock_url'] = handler.get_action_url(
                cls.UNLOCK_ACTION)
        #return to template
        return jinja2.utils.Markup(
            handler.get_template(
                'templates/unlock_form.html',
                [os.path.dirname(__file__)]).render(template_value))

    @classmethod
    def unlock_assessment(cls, handler):
        template_value = {}
        is_super_admin = roles.Roles.is_super_admin()
        template_value['is_super_admin'] = is_super_admin        
        if is_super_admin:
            course = handler.get_course()
            unit_id = handler.request.get('unit_id')
            unit = course.find_unit_by_id(str(unit_id))
            unlock_status = False

            if unit and 'Cancel' != handler.request.get('submit'):
                if unit.is_locked:
                    if unit.availability == courses.AVAILABILITY_UNAVAILABLE:
                        unit.is_locked = False
                        unlock_status = True
                    else:
                        unlock_status = False
            
            template_value['unit'] = unit
            template_value['unlock_status'] = unlock_status

        #return
        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/unlock_confirmation.html',
                [os.path.dirname(__file__)]).render(template_value))
        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV)

