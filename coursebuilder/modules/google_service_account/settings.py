# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Admin module for service account."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import urllib
import cgi
import logging

from common import safe_dom
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from controllers.utils import BaseRESTHandler
from controllers.utils import XsrfTokenManager
from models import roles
from models import transforms
from modules.oeditor import oeditor
from modules.google_service_account import base
from modules.google_service_account import google_service_account
from modules.google_service_account import service_account_models


class GoogleServiceAccountBaseAdminHandler(base.GoogleServiceAccountBase):

    TABLE_HEADING_LIST = [
        'credential_type',
        'client_email',
        'sub_user_email',
        'scope'
    ]

    @classmethod
    def get_google_service_account(cls, handler):
        """Displays list of service account settings."""

        if roles.Roles.is_super_admin():
            # ?tab= for v1.9, ?action= for v1.8
            exit_url = '%s?tab=google_service_account' % handler.LINK_URL
        else:
            exit_url = cls.request.referer
        rest_url = GoogleServiceAccountRESTHandler.URI

        template_values = {}
        template_values['page_title'] = handler.format_title(
            'Google Service Accounts')

        content = safe_dom.NodeList()
        edit_google_service_account_action = (
            base.GoogleServiceAccountBase.
            DASHBOARD_EDIT_SERVICE_ACCOUNT_ACTION)

        for name, key in (service_account_models.GoogleServiceAccountTypes.
                          to_dict().iteritems()):
            content.append(
                safe_dom.Element(
                    'a', id=edit_google_service_account_action,
                    className='gcb-button gcb-pull-right', role='button',
                    style='margin: 5px',
                    href='%s?action=%s&key=%s&credential_type=%s' % (
                        handler.LINK_URL, edit_google_service_account_action,
                        key, key)
                ).add_text('Add/Edit %s object' % name)
            )

        # Title - Default Settings
        content.append(
            safe_dom.Element('h3').add_text('Default Settings')
        )

        # Table - Default Settings
        table_div = safe_dom.Element(
            'div', style='width: 100%; overflow: scroll; margin-top: 10px;')
        table = safe_dom.Element('table')
        table_div.add_child(table)
        content.append(table_div)

        table_heading = safe_dom.Element('tr')
        for attr in cls.TABLE_HEADING_LIST:
            table_heading.add_child(
                safe_dom.Element('th').add_text(attr))

        # table_heading.add_child(
        #     safe_dom.Element('th').add_text('Edit Link'))

        table.add_child(table_heading)

        all_settings = (
            google_service_account.GoogleServiceManager.
            get_all_default_settings())

        # TODO(rthakker) Add support for namespaces from course list etc
        # later on
        for entity in all_settings:
            tr = safe_dom.Element('tr')
            table.add_child(tr)
            args = {
                'action': edit_google_service_account_action,
                'key': entity.id,
            }

            for attr in cls.TABLE_HEADING_LIST:
                tr.add_child(safe_dom.Element('td').add_text(
                    getattr(entity, attr)
                ))

            # href = '%s?%s' % (handler.LINK_URL, urllib.urlencode(args))
            # link = safe_dom.Element(
            #     'a', href=href, type='button', className='gcb-button'
            # ).add_text('Edit')
            # edit_td = safe_dom.Element('td')
            # edit_td.add_child(link)
            # tr.add_child(edit_td)


        content.append(
            safe_dom.Element('p').add_text('Total: %d' % len(all_settings))
        )
        template_values['main_content'] = content
        handler.render_page(template_values)

    @classmethod
    def get_edit_google_service_account(cls, handler):
        """
        Handles 'get_add_google_service_account_settings' action and renders
        new course entry editor.
        """

        if roles.Roles.is_super_admin():
            # ?tab= for v1.9, ?action= for v1.8
            exit_url = '%s?tab=google_service_account' % handler.LINK_URL
        else:
            exit_url = cls.request.referer
        key = handler.request.get('key')
        namespace = handler.request.get('namespace')
        credential_type = handler.request.get('credential_type')

        extra_args = {
            'namespace': namespace,
            'credential_type': credential_type,
            'xsrf_token': cgi.escape(
                handler.create_xsrf_token('edit-service_account'))
        }
        delete_url = rest_url = GoogleServiceAccountRESTHandler.URI

        template_values = {}
        template_values['page_title'] = handler.format_title(
            'Add Google Service Account')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            cls, GoogleServiceAccountRESTHandler.SCHEMA_JSON,
            GoogleServiceAccountRESTHandler.ANNOTATIONS_DICT,
            key, rest_url, exit_url,
            extra_args=extra_args,
            delete_url=delete_url, delete_method='delete',
            save_button_caption='Save')
        if not template_values['main_content']:
            logging.error('Main content could not be loaded')
        handler.render_page(template_values)

    @classmethod
    def create_service_account_registry(cls):
        """Create the registry for course properties."""

        reg = FieldRegistry(
            'Google Service Account',
            description='Google Service Accounts',
            extra_schema_dict_values={
                'className': 'inputEx-Group new-form-layout'})
        reg.add_property(SchemaField(
            'id', 'ID', 'string', editable=False))

        credential_type_tuple_list = (
            service_account_models.
            GoogleServiceAccountTypes.
            to_dict().
            iteritems())

        select_data = []
        for a, b in credential_type_tuple_list:
            select_data.append((b, a))

        # Making select_data read only for now since it will get auto populated
        # depending on which one of the three links to add/edit the user
        # clicks on. This will avoid overriding wrong data by mistake.
        reg.add_property(
            SchemaField(
                'credential_type', 'Credential Type', 'string',
                select_data=select_data, editable=False))
        reg.add_property(SchemaField(
            'client_email', 'Client Email', 'string', description='Email ID '
            'of the account with which to use this credential'))
        reg.add_property(SchemaField(
            'sub_user_email', 'Sub User Email', 'string', optional=True,
            description='Optional for service account'))
        reg.add_property(SchemaField(
            'scope', 'Scopes', 'list', description='List of scopes you want '
            'to use with this credential'))
        reg.add_property(SchemaField(
            'client_id', 'Client ID', 'string', optional=True,
            description='Required for Oauth2 Client ID'))
        reg.add_property(SchemaField(
            'api_key', 'API Key', 'string', optional=True,
            description='Required for type API KEY, optional for '
            'service account'))
        reg.add_property(SchemaField(
            'project_id', 'Project ID', 'string', optional=True,
            description='Optional for service account'))
        reg.add_property(SchemaField(
            'project_key_id', 'Project ID Key', 'string', optional=True,
            description='Optional for service account'))
        reg.add_property(SchemaField(
            'private_key', 'Private Key', 'text', optional=True,
            description='Required for service account'))
        reg.add_property(SchemaField(
            'auth_uri', 'auth_uri', 'string', optional=True,
            description='Optional for service account'))
        reg.add_property(SchemaField(
            'token_uri', 'token_uri', 'string', optional=True,
            description='Optional for service account'))
        reg.add_property(SchemaField(
            'auth_provider_x509_cert_url', 'auth_provider_x509_cert_url',
            'string', optional=True,
            description='Optional for service account'))
        reg.add_property(SchemaField(
            'client_x509_cert_url', 'client_x509_cert_url', 'string',
            optional=True, description='Optional for service account'))

        return reg

class GoogleServiceAccountRESTHandler(BaseRESTHandler):
    """Provides REST API to Google Service Account."""

    URI = '/rest/modules/google_service_account/google_service_account'
    DESCRIPTION = 'Update Google Service Account'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-string', 'inputex-textarea']
    SCHEMA_JSON = (GoogleServiceAccountBaseAdminHandler.
                   create_service_account_registry().get_json_schema())
    ANNOTATIONS_DICT = (GoogleServiceAccountBaseAdminHandler.
                        create_service_account_registry().get_schema_dict())

    @classmethod
    def get_schema_annotations_dict(cls):
        return  cls.registration().get_schema_dict()

    @classmethod
    def registration(cls):
        return (GoogleServiceAccountBaseAdminHandler.
                create_service_account_registry())

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self, errors):
        """Assemble a dict with the unit data fields."""

        key = self.request.get('key')
        # TODO(rthakker) Add support for multiple courses
        namespace = ''
        # namespace = self.request.get('namespace', '')
        entry = None
        if key:
            entry = (
                google_service_account.GoogleServiceManager
                .get_by_id(key, namespace))
        if not entry:
            entry = service_account_models.GoogleServiceAccountSettingsDTO(
                service_account_models.GoogleServiceAccountSettings())
            credential_type = self.request.get('credential_type')
            if credential_type:
                entry.credential_type = credential_type
        return entry.to_dict()


    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated service account details."""
        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        # Un escape strings if required
        if '-----BEGIN PRIVATE KEY-----\\n' in updated_unit_dict['private_key']:
            updated_unit_dict['private_key'] = (
                updated_unit_dict['private_key'].decode('string_escape'))

        updated_entity = None
        if not updated_unit_dict.get('id'):
            # Default Settings
            updated_entity = (google_service_account.GoogleServiceManager.
             update_default_settings_by_type(**updated_unit_dict))
        else:
            updated_entity = (google_service_account.GoogleServiceManager.
             update_service_account_settings(**updated_unit_dict))
        if not updated_entity:
            errors.append('Failed to save, please verify the details provided.')

    def get(self):
        """A GET REST method"""
        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': ''})
            return
        errors = []
        payload_dict = self.to_dict(errors)
        if errors:
            transforms.send_json_response(self, 412, '\n'.join(errors))
            return
        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=payload_dict,
            xsrf_token=XsrfTokenManager.create_xsrf_token(
                'update-service_account'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'update-service_account', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        payload = request.get('payload')
        updated_dict = transforms.loads(payload)
        # updated_dict = transforms.json_to_dict(
        #     transforms.loads(payload), self.get_schema_dict())

        errors = []
        self.apply_updates(updated_dict, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))
