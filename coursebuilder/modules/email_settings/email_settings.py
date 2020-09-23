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

"""Handling external email settings."""

__author__ = 'Thejesh GN (tgn@google.com)'


import yaml
import StringIO
import cgi
import csv
import os
import urllib

from common import jinja_utils
from common import safe_dom
from common import tags
from common.schema_fields import FieldArray
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from controllers.utils import BaseRESTHandler
from controllers.utils import XsrfTokenManager
from models import courses
from models import roles
from models import transforms
from models import models
from modules.invitation import invitation
from modules.announcements import announcements
from modules.student_questions import student_questions
from modules.oeditor import oeditor
from modules.email_settings import base
from modules.email_settings import email_settings_model
from controllers.utils import ReflectiveRequestHandler

class EmailSettingsBaseAdminHandler(base.EmailSettingsBase):

    @classmethod
    def get_email_settings(self, handler):
        """Shows a list of all external email settings available on this site."""
        template_values = {}
        template_values['page_title'] = handler.format_title('Email Queue settings')

        content = safe_dom.NodeList()
        content.append(
            safe_dom.Element(
                'a', id='add_email_settings', className='gcb-button gcb-pull-right',
                role='button', href='%s?action=add_email_settings' % handler.LINK_URL
            ).add_text('Add Email Settings')
        ).append(
            safe_dom.Element('div', style='clear: both; padding-top: 2px;')
        ).append(
            safe_dom.Element('h3').add_text('All Email Settings')
        )
        table = safe_dom.Element('table')
        content.append(table)
        table.add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('th').add_text('Unique Name')
            ).add_child(
                safe_dom.Element('th').add_text('Provider')
            ).add_child(
                safe_dom.Element('th').add_text('From Email')
            ).add_child(
                safe_dom.Element('th').add_text('API Key')
            )
        )
        count = 0
        for settings_dao in email_settings_model.EmailSettingsDAO.get_email_settings_list():
            count += 1
            error = safe_dom.Text('')
            args = {'action': 'edit_email_settings', 'key': settings_dao.unique_name}
            link = href='%s?%s' % (handler.LINK_URL, urllib.urlencode(args))

            link = safe_dom.Element('a', href=link).add_text(settings_dao.unique_name)

            table.add_child(
                safe_dom.Element('tr').add_child(
                    safe_dom.Element('td').add_child(link)
                ).add_child(
                    safe_dom.Element('td').add_text(settings_dao.provider)
                ).add_child(
                    safe_dom.Element('td').add_text(settings_dao.from_email)
                ).add_child(
                    safe_dom.Element('td').add_text(settings_dao.api_key)
                ))

        table.add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('td', colspan='5', align='right').add_text(
                    'Total: %s item(s)' % count)))

        content.append(
            safe_dom.Element('div', style='clear: both; padding-top: 12px;')
        ).append(
            safe_dom.Element(
                'a', id='add_queue_settings', className='gcb-button gcb-pull-right',
                role='button', href='%s?action=add_queue_settings' % handler.LINK_URL
            ).add_text('Add Queue Settings')
        ).append(
            safe_dom.Element('div', style='clear: both; padding-top: 2px;')
        ).append(
            safe_dom.Element('h3').add_text('All Queue Settings')
        )


        queue_table = safe_dom.Element('table')
        content.append(queue_table)
        queue_table.add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('th').add_text('Queue')
            ).add_child(
                safe_dom.Element('th').add_text('Settings')
            )
        )
        count = 0
        for settings_dao in email_settings_model.QueueSettingsDAO.get_queue_settings_list():
            count += 1
            error = safe_dom.Text('')
            args = {'action': 'edit_queue_settings', 'key': settings_dao.queue_id}
            link = href='%s?%s' % (handler.LINK_URL, urllib.urlencode(args))

            link = safe_dom.Element('a', href=link).add_text(settings_dao.queue_id)

            queue_table.add_child(
                safe_dom.Element('tr').add_child(
                    safe_dom.Element('td').add_child(link)
                ).add_child(
                    safe_dom.Element('td').add_text(settings_dao.email_settings.unique_name)
                )
            )

        queue_table.add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('td', colspan='3', align='right').add_text(
                    'Total: %s item(s)' % count)))

        template_values['main_content'] = content

        handler.render_page(template_values)

    @classmethod
    def get_add_email_settings(self, handler):
        """Handles 'get_add_email_settings' action."""

        if roles.Roles.is_super_admin():
            exit_url = '%s?tab=email_settings' % handler.LINK_URL
        else:
            exit_url = self.request.referer
        rest_url = AddNewEmailSettingsRESTHandler.URI

        template_values = {}
        template_values['page_title'] = handler.format_title('Add New Email Settings')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, AddNewEmailSettingsRESTHandler.SCHEMA_JSON,
            AddNewEmailSettingsRESTHandler.get_schema_annotations_dict(),
            None, rest_url, exit_url,
            auto_return=True,
            save_button_caption='Add New Email Settings')
        handler.render_page(template_values, in_tab='email_settings')


    @classmethod
    def get_edit_email_settings(self, handler):
        """Handles 'edit_email_settingsr' action and renders new course entry editor."""

        if roles.Roles.is_super_admin():
            exit_url = '%s?tab=email_settings' % handler.LINK_URL
        else:
            exit_url = self.request.referer
        rest_url = EmailSettingsRESTHandler.URI
        key = handler.request.get('key')

        delete_url = '%s?%s' % (
            rest_url,
            urllib.urlencode({
                'key': key,
                'xsrf_token': cgi.escape(
                        handler.create_xsrf_token('delete_email_settings'))
            }))

        template_values = {}
        template_values['page_title'] = handler.format_title('Edit Email Settings')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, EmailSettingsRESTHandler.SCHEMA_JSON,
            EmailSettingsRESTHandler.get_schema_annotations_dict(),
            key, rest_url, exit_url,
            auto_return=True, delete_url=delete_url,
            delete_method='delete',
            save_button_caption='Update Email Settings')
        handler.render_page(template_values, in_tab='email_settings')


    @classmethod
    def get_add_queue_settings(self, handler):
        """Handles 'add_queue_settings' action."""

        if roles.Roles.is_super_admin():
            exit_url = '%s?tab=email_settings' % handler.LINK_URL
        else:
            exit_url = self.request.referer
        rest_url = AddNewQueueSettingsRESTHandler.URI

        template_values = {}
        template_values['page_title'] = handler.format_title('Add New Queue Settings')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, AddNewQueueSettingsRESTHandler.SCHEMA_JSON,
            AddNewQueueSettingsRESTHandler.get_schema_annotations_dict(),
            None, rest_url, exit_url,
            auto_return=True,
            save_button_caption='Add New Email Queue Settings')
        handler.render_page(template_values, in_tab='email_settings')


    @classmethod
    def get_edit_queue_settings(self, handler):
        """Handles 'edit_email_settingsr' action and renders new course entry editor."""

        if roles.Roles.is_super_admin():
            exit_url = '%s?tab=email_settings' % handler.LINK_URL
        else:
            exit_url = self.request.referer
        rest_url = QueueSettingsRESTHandler.URI
        key = handler.request.get('key')

        delete_url = '%s?%s' % (
            rest_url,
            urllib.urlencode({
                'key': key,
                'xsrf_token': cgi.escape(
                        handler.create_xsrf_token('delete_queue_settings'))
            }))

        template_values = {}
        template_values['page_title'] = handler.format_title('Edit Queue Settings')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, QueueSettingsRESTHandler.SCHEMA_JSON,
            QueueSettingsRESTHandler.get_schema_annotations_dict(),
            key, rest_url, exit_url,
            auto_return=True, delete_url=delete_url,
            delete_method='delete',
            save_button_caption='Update Queue Settings')
        handler.render_page(template_values, in_tab='email_settings')


def create_queue_settings_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Queue Settings',
         description='Queue Settings',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})
    select_data = [(models.WELCOME_NOTIFICATION_INTENT,'WELCOME_NOTIFICATION_INTENT'),
                    (invitation.INVITATION_INTENT,'INVITATION_INTENT'),
                    (announcements.ANNOUNCEMENTS_INTENT,'ANNOUNCEMENTS_INTENT'),
                    (student_questions.FORUM_QUESTION_INTENT,'FORUM_QUESTION_INTENT')]

    reg.add_property(SchemaField(
        'queue_id', 'Queue ID', 'string', optional=False, select_data=select_data,
        extra_schema_dict_values={
            'className': 'inputEx-Field assessment-dropdown'}))

    reg.add_property(SchemaField(
        'email_settings', 'Email Settings', 'string', optional=False, select_data=[],
        extra_schema_dict_values={
            'className': 'inputEx-Field assessment-dropdown'}))

    return reg




class AddNewQueueSettingsRESTHandler(BaseRESTHandler):
    """Provides REST API to Local Chapter."""
    URI = '/rest/modules/email_settings/add_new_queue_settings'
    DESCRIPTION = 'Add New EmailQueue Settings'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_queue_settings_registry().get_json_schema()
    #ANNOTATIONS_DICT = create_queue_settings_registry().get_schema_dict()


    @classmethod
    def get_schema_annotations_dict(cls):
        email_settings_data_for_select = [
            (settings_dao.unique_name, settings_dao.unique_name)
        for settings_dao in email_settings_model.EmailSettingsDAO.get_email_settings_list()]
        extra_select_options = dict()
        extra_select_options['email_settings'] = email_settings_data_for_select
        return  cls.registration().get_schema_dict(extra_select_options=extra_select_options)


    @classmethod
    def registration(cls):
        return create_queue_settings_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self):
        """Assemble a dict with the unit data fields."""
        entity = {
            'queue_id':'',
            'email_settings':'',
            }
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the Queue settings."""

        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        queue_id = entity_dict['queue_id']
        email_settings = entity_dict['email_settings']

        esettings = email_settings_model.EmailSettings.get_by_id(email_settings)
        if esettings:
            email_settings_model.QueueSettingsDAO.add_new_queue_settings(queue_id, esettings.key, errors=errors)
        else:
            errors.append(
                'Unable to find EmailSettings. Entry with the '
                'key \'%s\' doesnt exist.' % email_settings)
        return

    def get(self):
        """A GET REST method shared by all unit types."""
        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=self.to_dict(),
            xsrf_token=XsrfTokenManager.create_xsrf_token('add_new_email_settings'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'add_new_email_settings', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        payload = request.get('payload')
        updated_dict = transforms.json_to_dict(
            transforms.loads(payload), self.get_schema_dict())

        errors = []
        self.apply_updates(updated_dict, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))





def create_email_settings_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Email Settings',
         description='Email Settings',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})
    reg.add_property(SchemaField(
        'unique_name', 'Unique Name', 'string'))
    select_data = [('APP_ENGINE_EMAIL','App Engine Email'),('SEND_GRID','Send Grid')]
    reg.add_property(SchemaField(
        'provider', 'Provider', 'string', optional=False, select_data=select_data,
        extra_schema_dict_values={
            'className': 'inputEx-Field assessment-dropdown'}))
    reg.add_property(SchemaField(
        'from_email', 'From Email', 'string'))
    reg.add_property(SchemaField(
        'api_key', 'API Key', 'string',optional=True))

    return reg




class AddNewEmailSettingsRESTHandler(BaseRESTHandler):
    """Provides REST API to Local Chapter."""
    URI = '/rest/modules/email_settings/add_new_email_settings'
    DESCRIPTION = 'Add New Email Settings'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_email_settings_registry().get_json_schema()
    #ANNOTATIONS_DICT = create_email_settings_registry().get_schema_dict()

    @classmethod
    def get_schema_annotations_dict(cls):
        return  cls.registration().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_email_settings_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self):
        """Assemble a dict with the unit data fields."""
        entity = {
            'unique_name':'',
            'provider':'',
            'from_email': '',
            'api_key':''}
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        unique_name = entity_dict['unique_name']
        provider = entity_dict['provider']
        from_email = entity_dict['from_email']
        api_key = entity_dict['api_key']

        #TODO add validation
        email_settings_model.EmailSettingsDAO.add_new_email_settings(
        unique_name=unique_name,provider=provider, from_email=from_email
        ,api_key=api_key, errors=errors)

    def get(self):
        """A GET REST method shared by all unit types."""
        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=self.to_dict(),
            xsrf_token=XsrfTokenManager.create_xsrf_token('add_new_email_settings'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'add_new_email_settings', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        payload = request.get('payload')
        updated_dict = transforms.json_to_dict(
            transforms.loads(payload), self.get_schema_dict())

        errors = []
        self.apply_updates(updated_dict, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))




class EmailSettingsRESTHandler(BaseRESTHandler):
    """Provides REST API to Email Settings."""

    URI = '/rest/modules/email_settings/email_settings_list'
    DESCRIPTION = 'Add Email Settings'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_email_settings_registry().get_json_schema()
    #ANNOTATIONS_DICT = create_email_settings_registry().get_schema_dict()

    @classmethod
    def get_schema_annotations_dict(cls):
        return  cls.registration().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_email_settings_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self, key, errors):
        """Assemble a dict with the unit data fields."""
        l = email_settings_model.EmailSettingsDAO.get_email_settings_by_key(key)
        if not l:
            errors.append('Email Settings not found : %s' % key)
            return

        entity = {
            'unique_name':l.unique_name,
            'provider':l.provider,
            'from_email': l.from_email,
            'api_key': l.api_key
            }
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""
        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        unique_name = entity_dict['unique_name']
        provider = entity_dict['provider']
        from_email = entity_dict['from_email']
        api_key = entity_dict['api_key']

        if email_settings_model.EmailSettingsDAO.get_email_settings_by_key(unique_name):
            email_settings_model.EmailSettingsDAO.update_email_settings(
		          unique_name=unique_name, provider=provider, from_email=from_email,
                  api_key=api_key, errors=errors)
        else:
             errors.append('Email Settings not found : %s' % key)

    def get(self):
        """A GET REST method"""
        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        key = self.request.get('key')
        errors = []
        payload_dict = self.to_dict(key, errors)
        if errors:
            transforms.send_json_response(self, 412, '\n'.join(errors))
            return

        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=payload_dict,
            xsrf_token=XsrfTokenManager.create_xsrf_token('update_email_settings'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'update_email_settings', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        payload = request.get('payload')
        updated_dict = transforms.json_to_dict(
            transforms.loads(payload), self.get_schema_dict())

        errors = []
        self.apply_updates(updated_dict, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))

    def delete(self):
        """A PUT REST method."""
        key = self.request.get('key')

        if not self.assert_xsrf_token_or_fail(
                self.request, 'delete_email_settings', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        queue_settings = email_settings_model.QueueSettingsDAO.get_queue_settings_by_email_settings(key)

        if queue_settings:
            transforms.send_json_response(
                self, 412, 'Cant delete email settings as a queue settings is dependent on it.')
            return

        errors = []
        email_settings_model.EmailSettingsDAO.delete_email_settings(key, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Deleted.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))


class QueueSettingsRESTHandler(BaseRESTHandler):
    """Provides REST API to Queue Settings."""

    URI = '/rest/modules/email_settings/queue_settings'
    DESCRIPTION = 'Add Email Settings'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_queue_settings_registry().get_json_schema()
    #ANNOTATIONS_DICT = create_queue_settings_registry().get_schema_dict()

    @classmethod
    def get_schema_annotations_dict(cls):
        email_settings_data_for_select = [
            (settings_dao.unique_name, settings_dao.unique_name)
        for settings_dao in email_settings_model.EmailSettingsDAO.get_email_settings_list()]
        extra_select_options = dict()
        extra_select_options['email_settings'] = email_settings_data_for_select
        return  cls.registration().get_schema_dict(extra_select_options=extra_select_options)

    @classmethod
    def registration(cls):
        return create_queue_settings_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self, key, errors):
        """Assemble a dict with the unit data fields."""
        l = email_settings_model.QueueSettingsDAO.get_queue_settings_by_key(key)
        if not l:
            errors.append('Queue Settings not found : %s' % key)
            return

        entity = {
            'queue_id':l.queue_id,
            'email_settings':l.email_settings.unique_name
            }

        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        print str(entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""
        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        queue_id = entity_dict['queue_id']
        email_settings = entity_dict['email_settings']
        esettings = email_settings_model.EmailSettings.get_by_id(email_settings)
        if esettings:
            email_settings_model.QueueSettingsDAO.update_queue_settings(queue_id, esettings.key, errors=errors)
        else:
            errors.append(
                'Unable to find EmailSettings. Entry with the '
                'key \'%s\' doesnt exist.' % email_settings)
        return

    def get(self):
        """A GET REST method"""
        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        key = self.request.get('key')
        errors = []
        payload_dict = self.to_dict(key, errors)

        if errors:
            transforms.send_json_response(self, 412, '\n'.join(errors))
            return

        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=payload_dict,
            xsrf_token=XsrfTokenManager.create_xsrf_token('update_queue_settings'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'update_queue_settings', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        payload = request.get('payload')
        updated_dict = transforms.json_to_dict(
            transforms.loads(payload), self.get_schema_dict())

        errors = []
        self.apply_updates(updated_dict, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))

    def delete(self):
        """A PUT REST method."""
        key = self.request.get('key')

        if not self.assert_xsrf_token_or_fail(
                self.request, 'delete_queue_settings', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        errors = []
        email_settings_model.QueueSettingsDAO.delete_queue_settings(key, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Deleted.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))
