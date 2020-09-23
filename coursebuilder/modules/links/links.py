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

"""Handlers for opening links."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import os

from common import jinja_utils
from controllers import utils
from models import custom_modules


class LinkHandler(utils.BaseHandler):
    """Handler for forum page."""

    def get(self):
        """Handles GET requests."""
        student = self.personalize_page_and_get_enrolled(
            supports_transient_student=True)
        if not student:
            return
        u = self.request.get('unit')
        target = None
        title = None
        unit = None
        if u:
            unit = self.get_course().find_unit_by_id(u)
            if unit and unit.type == 'O' :
                target = unit.href
                title = unit.title
                self.template_value['unit'] = unit
                self.template_value['unit_id'] = unit.parent_unit
        if not unit:
            target = self.request.get('target')

        if not target:
            self.redirect('/')
            return

        self.template_value['target'] = target
        if title:
            self.template_value['title'] = title

        self.template_value['navbar'] = {}
        self.template_value['base'] = self.get_template('base_course.html')
        template = jinja_utils.get_template(
            'link.html', [os.path.dirname(__file__)])
        self.render(template)


custom_module = None


def register_module():
    """Registers this module in the registry."""
    
    courses_routes = [('/link', LinkHandler),]

    global custom_module
    custom_module = custom_modules.Module(
	'Links', 'Page for links tab', [], courses_routes)
    return custom_module
