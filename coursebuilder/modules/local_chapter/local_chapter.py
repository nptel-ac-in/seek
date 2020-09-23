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

"""Local Chapter module."""

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
from modules.oeditor import oeditor
from modules.local_chapter import base
from modules.local_chapter import local_chapter_model
from controllers.utils import ReflectiveRequestHandler


class LocalChapterBaseAdminHandler(base.LocalChapterBase):

    @classmethod
    def get_local_chapters(self, handler):
        """Shows a list of all local chapters available on this site."""
        template_values = {}
        template_values['page_title'] = handler.format_title('Local Chapters')

        content = safe_dom.NodeList()
        content.append(
            safe_dom.Element(
                'a', id='add_local_chapter', className='gcb-button gcb-pull-right',
                role='button', href='%s?action=add_local_chapter' % handler.LINK_URL
            ).add_text('Add Local Chapter')
        ).append(
            safe_dom.Element(
                'a', id='bulk_add_local_chapter', className='gcb-button gcb-pull-right',
                role='button', href='%s?action=bulk_add_local_chapter' % handler.LINK_URL
            ).add_text('Bulk Add Local Chapter')
        ).append(
            safe_dom.Element('div', style='clear: both; padding-top: 2px;')
        ).append(
            safe_dom.Element('h3').add_text('All Local Chapters')
        )
        table = safe_dom.Element('table')
        content.append(table)
        table.add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('th').add_text('Chapter Code')
            ).add_child(
                safe_dom.Element('th').add_text('Chapter Name')
            ).add_child(
                safe_dom.Element('th').add_text('City')
            ).add_child(
                safe_dom.Element('th').add_text('State')
            )
        )
        count = 0
        for chapter in local_chapter_model.LocalChapterDAO.get_local_chapter_list():
            count += 1
            error = safe_dom.Text('')

            args = {'action': 'edit_local_chapter', 'key': chapter.code}
            link = href='%s?%s' % (handler.LINK_URL, urllib.urlencode(args))

            link = safe_dom.Element('a', href=link).add_text(chapter.code)

            table.add_child(
                safe_dom.Element('tr').add_child(
                    safe_dom.Element('td').add_child(link).add_child(error)
                ).add_child(
                    safe_dom.Element('td').add_text(chapter.name)
                ).add_child(
                    safe_dom.Element('td').add_text(chapter.city)
                ).add_child(
                    safe_dom.Element('td').add_text(chapter.state)
                ))

        table.add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('td', colspan='5', align='right').add_text(
                    'Total: %s item(s)' % count)))
        template_values['main_content'] = content

        handler.render_page(template_values)


    @classmethod
    def get_add_local_chapter(self, handler):
        """Handles 'get_add_local_chapter' action and renders new course entry editor."""

        if roles.Roles.is_super_admin():
            exit_url = '%s?tab=local_chapters' % handler.LINK_URL
        else:
            exit_url = self.request.referer
        rest_url = AddNewLocalChapterRESTHandler.URI

        template_values = {}
        template_values['page_title'] = handler.format_title('Add Local Chapter')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, AddNewLocalChapterRESTHandler.SCHEMA_JSON,
            AddNewLocalChapterRESTHandler.ANNOTATIONS_DICT,
            None, rest_url, exit_url,
            auto_return=True,
            save_button_caption='Add New Local Chapter')
        handler.render_page(template_values, in_tab='local_chapters')


    @classmethod
    def get_bulk_add_local_chapter(self,handler):
        """Handles 'get_bulk_add_local_chapter' action and renders new course entry editor."""
        if roles.Roles.is_super_admin():
            exit_url = '%s?tab=local_chapters' % handler.LINK_URL
        else:
            exit_url = self.request.referer
        rest_url = BulkAddNewLocalChapterRESTHandler.URI

        template_values = {}
        template_values['page_title'] = handler.format_title('Bulk Add Local Chapter')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, BulkAddNewLocalChapterRESTHandler.SCHEMA_JSON,
            BulkAddNewLocalChapterRESTHandler.ANNOTATIONS_DICT,
            None, rest_url, exit_url,
            auto_return=True,
            save_button_caption='Upload New Local Chapters')
        handler.render_page(template_values, in_tab='local_chapters')


    @classmethod
    def get_edit_local_chapter(self, handler):
        """Handles 'edit_loal_chapter' action and renders new course entry editor."""

        if roles.Roles.is_super_admin():
            exit_url = '%s?tab=local_chapters' % handler.LINK_URL
        else:
            exit_url = self.request.referer
        rest_url = LocalChapterRESTHandler.URI
        key = handler.request.get('key')

        delete_url = '%s?%s' % (
            rest_url,
            urllib.urlencode({
                'key': key,
                'xsrf_token': cgi.escape(
                        handler.create_xsrf_token('delete-local_chapter'))
            }))

        template_values = {}
        template_values['page_title'] = handler.format_title('Edit Local Chapter')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, LocalChapterRESTHandler.SCHEMA_JSON,
            LocalChapterRESTHandler.get_schema_annotations_dict(),
            key, rest_url, exit_url,
            auto_return=True, delete_url=delete_url,
            delete_method='delete',
            save_button_caption='Update Local Chapter')
        handler.render_page(template_values, in_tab='local_chapters')


def create_local_chapter_list_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Local Chapter',
         description='Local Chapters',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})
    reg.add_property(SchemaField(
        'code', 'Local Chapter Code', 'string'))
    reg.add_property(SchemaField(
        'name', 'Local Chapter Name', 'string'))
    reg.add_property(SchemaField(
        'city', 'City', 'string'))

    select_data = [('ANDAMAN AND NICOBAR ISLANDS','Andaman_and_Nicobar_Islands'),
    ( 'ANDHRA PRADESH', 'Andhra Pradesh'), ('ARUNACHAL PRADESH', 'Arunachal Pradesh'),
    ('ASSAM','Assam'), ('BIHAR','Bihar'), ('CHANDIGARH', 'Chandigarh'),
    ('CHHATTISGARH', 'Chhattisgarh'), ('DADRA AND NAGAR HAVELI', 'Dadra and Nagar Haveli'),
    ('DELHI', 'Delhi'), ('GOA','Goa'), ('GUJARAT','Gujarat'), ('HARYANA', 'Haryana'),
    ('HIMACHAL PRADESH', 'Himachal Pradesh'), ('JAMMU AND KASHMIR', 'Jammu and Kashmir'),
    ('JHARKHAND', 'Jharkhand'), ('KARNATAKA', 'Karnataka'),('KERALA', 'Kerala'),
    ('LAKSHADWEEP', 'Lakshadweep'),('MADHYA PRADESH', 'Madhya Pradesh'),
    ('MAHARASHTRA', 'Maharashtra'),('MANIPUR', 'Manipur'),('MEGHALAYA', 'Meghalaya'),
    ('MIZORAM', 'Mizoram'), ('NAGALAND', 'Nagaland'), ('ODISHA' , 'Odisha'),
    ('PONDICHERRY', 'Pondicherry'), ('PUNJAB', 'Punjab'), ('RAJASTHAN', 'Rajasthan'),
    ('SIKKIM','Sikkim'),('TAMIL NADU', 'Tamil Nadu'), ('TELANGANA', 'Telangana'),
    ('TRIPURA', 'Tripura'), ('UTTARAKHAND', 'Uttarakhand'),
    ('UTTAR PRADESH', 'Uttar Pradesh'), ('WEST BENGAL', 'West Bengal')]


    reg.add_property(SchemaField(
        'state', 'State', 'string', optional=False, select_data=select_data,
        extra_schema_dict_values={
            'className': 'inputEx-Field assessment-dropdown'}))

    return reg


class AddNewLocalChapterRESTHandler(BaseRESTHandler):
    """Provides REST API to Local Chapter."""

    URI = '/rest/modules/local_chapter/add_new_local_chapter'
    DESCRIPTION = 'Add Local Chapter'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_local_chapter_list_registry().get_json_schema()
    ANNOTATIONS_DICT = create_local_chapter_list_registry().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_local_chapter_list_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self):
        """Assemble a dict with the unit data fields."""
        entity = {
            'code':'',
            'name': '',
            'city': '',
            'state':''}
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        key = entity_dict['code']
        name = entity_dict['name']
        state = entity_dict['state']
        city = entity_dict['city']

        if local_chapter_model.LocalChapterDAO.get_local_chapter_by_key(key):
                errors.append(
                   'Local Chpater %s already exists.' % key)
        else:
            local_chapter_model.LocalChapterDAO.add_new_local_chapter(
		key, name, city, state, errors)

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
            xsrf_token=XsrfTokenManager.create_xsrf_token('add-new-local_chapter'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'add-new-local_chapter', {}):
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


def create_bulk_local_chapter_list_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Local Chapter',
         description='Bulk Local Chapters',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})
    reg.add_property(SchemaField(
        'bulk_addition', 'Bulk Local Chapters (code,name,city,state)', 'text'))
    return reg

class BulkAddNewLocalChapterRESTHandler(BaseRESTHandler):
    """Provides REST API to Bulk Add Local Chapter."""

    URI = '/rest/modules/local_chapter/bulk_add_local_chapter'
    DESCRIPTION = 'Bulk Add Local Chapter'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_bulk_local_chapter_list_registry().get_json_schema()
    ANNOTATIONS_DICT = create_bulk_local_chapter_list_registry().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_bulk_local_chapter_list_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self):
        """Assemble a dict with the unit data fields."""
        entity = {
            'bulk_addition':'code,name,city,state'}
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        key = updated_unit_dict['code']
        name = updated_unit_dict['name']
        state = updated_unit_dict['state']
        city = updated_unit_dict['city']

        if local_chapter_model.LocalChapterDAO.get_local_chapter_by_key(key):
                errors.append(
                   'Local Chpater %s already exists.' % key)
        else:
            local_chapter_model.LocalChapterDAO.add_new_local_chapter(
		key, name, city, state, errors)

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
            xsrf_token=XsrfTokenManager.create_xsrf_token('add-new-local_chapter'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'add-new-local_chapter', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        payload = request.get('payload')

        updated_dict = transforms.json_to_dict(
            transforms.loads(payload), self.get_schema_dict())
        errors = []

        bulk_addition = updated_dict['bulk_addition']
        reader = csv.reader(StringIO.StringIO(bulk_addition), delimiter=',')
        for row in reader:
            if len(row) != 4:
                errors.append('Invalid row %s' % row[0])
                continue
            updated_dict = {}
            updated_dict['code'] = row[0]
            updated_dict['name'] = row[1]
            updated_dict['city'] = row[2]
            updated_dict['state'] = row[3]
            self.apply_updates(updated_dict, errors)

        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))


class LocalChapterRESTHandler(BaseRESTHandler):
    """Provides REST API to Local Chapter."""

    URI = '/rest/modules/local_chapter/local_chapter_list'
    DESCRIPTION = 'Add Local Chapter'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_local_chapter_list_registry().get_json_schema()
    ANNOTATIONS_DICT = create_local_chapter_list_registry().get_schema_dict()

    @classmethod
    def get_schema_annotations_dict(cls):
        return  cls.registration().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_local_chapter_list_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self, key, errors):
        """Assemble a dict with the unit data fields."""
        l = local_chapter_model.LocalChapterDAO.get_local_chapter_by_key(key)
        if not l:
            errors.append('Local Chapter not found : %s' % key)
            return

        entity = {
            'code':l.code,
            'name': l.name,
            'city': l.city,
            'state':l.state}
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""
        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        key = entity_dict['code']
        name = entity_dict['name']
        city = entity_dict['city']
        state = entity_dict['state']

        if local_chapter_model.LocalChapterDAO.get_local_chapter_by_key(key):
            local_chapter_model.LocalChapterDAO.update_local_chapter(
		key, name, city, state, errors)
        else:
             errors.append('Local Chapter not found : %s' % key)

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
            xsrf_token=XsrfTokenManager.create_xsrf_token('update-local_chapter'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'update-local_chapter', {}):
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
                self.request, 'delete-local_chapter', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        errors = []
        local_chapter_model.LocalChapterDAO.delete_local_chapter(key, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Deleted.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))
