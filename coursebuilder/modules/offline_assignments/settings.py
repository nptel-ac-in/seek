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

__authors__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

import logging
import csv
import StringIO

from common import safe_dom
from controllers.utils import BaseRESTHandler
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from models import roles
from models import transforms
from modules.oeditor import oeditor
from controllers.utils import XsrfTokenManager

from modules.offline_assignments import base
from modules.offline_assignments import assignment

class OfflineAssignmentBaseAdminHandler(base.OfflineAssignmentBase):

    @classmethod
    def get_offline_assignment(cls, handler):
        """Displays an editor for bulk score update"""

        if not roles.Roles.is_super_admin():
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': 'Unauthorized'
            })
            return

        # ?tab=for v1.9, ?action= for v1.8
        # exit_url = '%s?tab=admin_offline_assignment' % handler.LINK_URL
        exit_url = ''
        rest_url = OfflineAssignmentRESTHandler.URI

        template_value = dict()
        template_value['page_title'] = handler.format_title(
            cls.ADMIN_DESCRIPTION)

        template_value['main_content'] = oeditor.ObjectEditor.get_html_for(
            cls, OfflineAssignmentRESTHandler.SCHEMA_JSON,
            OfflineAssignmentRESTHandler.ANNOTATIONS_DICT,
            None, rest_url, exit_url, save_button_caption='Save')
        if not template_value['main_content']:
            logging.error('Main content could not be loaded')
        handler.render_page(template_value)

        content = safe_dom.NodeList()

def create_bulk_offline_assignments_list_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        base.OfflineAssignmentBase.ADMIN_DESCRIPTION,
         description=base.OfflineAssignmentBase.ADMIN_DESCRIPTION,
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})
    reg.add_property(SchemaField(
        'csv_text',
        'Bulk Scores (course_namespace, student_id, assignment_id, score)',
        'text'))
    return reg


class OfflineAssignmentRESTHandler(BaseRESTHandler):
    """Provides REST API to Offline Assignments"""

    URI = '/rest/modules/offline_assignments/bulk_offline_assignment'
    DESCRIPTION = base.OfflineAssignmentBase.ADMIN_DESCRIPTION
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_bulk_offline_assignments_list_registry().get_json_schema()
    ANNOTATIONS_DICT = create_bulk_offline_assignments_list_registry().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_bulk_offline_assignments_list_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self):
        """Assemble a dict with the unit data fields."""
        entity = {
            'csv_text':'course_namespace,student_id,assignment_id,score'}
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def get(self):
        """A GET REST method shared by all unit types."""

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 403, 'Access denied.', {})
            return

        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=self.to_dict(),
            xsrf_token=XsrfTokenManager.create_xsrf_token(
                'bulk_score_offline_assignment'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'bulk_score_offline_assignment', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 403, 'Access denied.')
            return

        payload = request.get('payload')

        updated_dict = transforms.json_to_dict(
            transforms.loads(payload), self.get_schema_dict())

        errors = []
        data = dict()
        csv_text = updated_dict['csv_text']
        reader = csv.reader(StringIO.StringIO(csv_text))

        # Filter out empty rows
        reader = [r for r in reader if ''.join(r).strip()]
        assignment.OfflineAssignmentHandler.bulk_score(reader, errors)

        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))
