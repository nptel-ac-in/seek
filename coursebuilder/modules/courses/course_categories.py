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

"""Classes supporting course category configuration property editor and REST operations."""

__author__ = 'Thejesh GN (tgn@google.com)'


import cgi
import urllib

from common import tags
from common import safe_dom
from common.schema_fields import FieldArray
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from controllers.utils import BaseRESTHandler
from controllers.utils import XsrfTokenManager
from models import courses
from models import course_category
from models import course_list
from models import roles
from models import transforms
from modules.dashboard import dashboard
from modules.oeditor import oeditor
from modules.admin import admin

def create_category_list_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Course Category',
         description='Categories in which courses are divided.',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})
    reg.add_property(SchemaField(
        'category', 'Category', 'string'))
    reg.add_property(SchemaField(
        'description', 'Visible Name', 'string'))
    reg.add_property(SchemaField(
        'visible', 'Visible', 'boolean'))
    return reg


class CategoryListRESTHandler(BaseRESTHandler):
    """Provides REST API to get category list."""

    URI = '/rest/modules/courses/category_list'

    def get(self):
        """A GET REST method shared by all unit types."""
        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return
      
        category_list = sorted(course_category.CourseCategoryDAO.get_category_list(),
          key=lambda category: category.category)
  
        errors = []
        data = {}
        for category in category_list:
            data[category.category] =  category.description
        payload_dict = {"categories":data}

        transforms.send_json_response(
            self, 200, 'okay',
            payload_dict=payload_dict)


class EditCategoryRESTHandler(BaseRESTHandler):
    """Provides REST API to category list."""

    URI = '/rest/modules/courses/edit_category'
    DESCRIPTION = 'Edit Course Category'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_category_list_registry().get_json_schema()
    ANNOTATIONS_DICT = create_category_list_registry().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_category_list_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self, key, errors):
        """Assemble a dict with the unit data fields."""
        l = course_category.CourseCategoryDAO.get_category_by_key(key)
        if not l:
            errors.append('Category not found : %s' % key)
            return

        entity = {
            'category': l.category,
            'description': l.description,
            'visible':l.visible}
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""
        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        key = entity_dict['category']
        description = entity_dict['description']
        visible = entity_dict['visible']

        if course_category.CourseCategoryDAO.get_category_by_key(key):
            course_category.CourseCategoryDAO.update_category(
        key, description, visible, errors)
        else:
             errors.append('Category not found : %s' % key)

    def get(self):
        """A GET REST method shared by all unit types."""
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
            xsrf_token=XsrfTokenManager.create_xsrf_token('update-category'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'update-category', {}):
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
        """A PUT REST method shared by all unit types."""
        key = self.request.get('key')

        if not self.assert_xsrf_token_or_fail(
                self.request, 'delete-category', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        errors = []
        course_category.CourseCategoryDAO.delete_category(key, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Deleted.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))


class AddNewCategoryRESTHandler(BaseRESTHandler):
    """Provides REST API to adding new course category."""

    URI = '/rest/modules/courses/add_new_category'
    DESCRIPTION = 'Add Course Category'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_category_list_registry().get_json_schema()
    ANNOTATIONS_DICT = create_category_list_registry().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_category_list_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self):
        """Assemble a dict with the unit data fields."""
        entity = {
            'category': 'NEW_CATEGORY',
            'description': 'Visible Name',
            'visible':False}
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        key = entity_dict['category']
        description = entity_dict['description']
        visible = entity_dict['visible']

        if course_category.CourseCategoryDAO.get_category_by_key(key):
                errors.append(
                   'Category %s already exists.' % key)
        else:
            course_category.CourseCategoryDAO.add_new_category(
        key, description, visible, errors)

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
            xsrf_token=XsrfTokenManager.create_xsrf_token('add-new-category'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'add-new-category', {}):
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


class CourseCategoriesAdmin(object):

    @classmethod
    def get_course_categories(self, handler):
        """Shows a list of all courses available on this site."""
        template_values = {}
        template_values['page_title'] = handler.format_title('Course Categories')

        content = safe_dom.NodeList()
        content.append(
            safe_dom.Element(
                'a', id='add_course_category', className='gcb-button gcb-pull-right',
                role='button', href='%s?action=add_course_category' % handler.LINK_URL
            ).add_text('Add Course Category')
        ).append(
            safe_dom.Element('div', style='clear: both; padding-top: 2px;')
        ).append(
            safe_dom.Element('h3').add_text('All Course Categories')
        )
        table = safe_dom.Element('table')
        content.append(table)
        table.add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('th').add_text('Id')
            ).add_child(
                safe_dom.Element('th').add_text('Description')
            ).add_child(
                safe_dom.Element('th').add_text('Visible')
            )
        )
        count = 0
        for category in sorted(
            course_category.CourseCategoryDAO.get_category_list(),
            key=lambda category: category.category):
            count += 1
            error = safe_dom.Text('')

            args = {'action': 'edit_course_category', 'key': category.category}
            link = href='%s?%s' % (handler.LINK_URL, urllib.urlencode(args))

            link = safe_dom.Element('a', href=link).add_text(category.category)

            table.add_child(
                safe_dom.Element('tr').add_child(
                    safe_dom.Element('td').add_child(link).add_child(error)
                ).add_child(
                    safe_dom.Element('td').add_text(category.description)
                ).add_child(
                    safe_dom.Element('td').add_text(category.visible)
                ))

        table.add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('td', colspan='4', align='right').add_text(
                    'Total: %s item(s)' % count)))
        template_values['main_content'] = content

        handler.render_page(template_values)


    @classmethod
    def get_add_course_category(self,handler):
        """Handles 'add_course_category' action and renders new course entry editor."""

        if roles.Roles.is_super_admin():
            exit_url = '%s?action=course_categories' % handler.LINK_URL
        else:
            exit_url = handler.request.referer
        rest_url = AddNewCategoryRESTHandler.URI

        template_values = {}
        template_values['page_title'] = handler.format_title('Add Category')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            handler, AddNewCategoryRESTHandler.SCHEMA_JSON,
            AddNewCategoryRESTHandler.ANNOTATIONS_DICT,
            None, rest_url, exit_url,
            auto_return=True,
            save_button_caption='Add New Course Category')

        handler.render_page(template_values, in_action='course_categories')

    @classmethod
    def get_edit_course_category(self,handler):
        """Handles action and renders new course entry editor."""
        if not roles.Roles.is_super_admin():
            handler.error(404)
            return

        exit_url = '%s?action=course_categories' % handler.LINK_URL
        rest_url = EditCategoryRESTHandler.URI
        key = handler.request.get('key')
        delete_url = '%s?%s' % (rest_url,urllib.urlencode({
              'key': key,
              'xsrf_token': cgi.escape(handler.create_xsrf_token('delete-category'))
        }))

        template_values = {}
        template_values['page_title'] = handler.format_title('Edit Category')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(handler, 
            EditCategoryRESTHandler.SCHEMA_JSON,EditCategoryRESTHandler.ANNOTATIONS_DICT,
            handler.request.get('key'), rest_url, exit_url,auto_return=True, 
            delete_url=delete_url,delete_method='delete',save_button_caption='Update Category')

        handler.render_page(template_values, in_action='course_categories')

def get_global_handlers():
    return [
        ( EditCategoryRESTHandler.URI, EditCategoryRESTHandler),
         (AddNewCategoryRESTHandler.URI, AddNewCategoryRESTHandler),
          (CategoryListRESTHandler.URI, CategoryListRESTHandler)
    ]

def get_namespaced_handlers():
    return [
        ('/' + EditCategoryRESTHandler.URI, EditCategoryRESTHandler),
         ('/' + AddNewCategoryRESTHandler.URI, AddNewCategoryRESTHandler)
    ]

def on_module_enabled(courses_custom_module, module_permissions):
    global custom_module  # pylint: disable=global-statement
    custom_module = courses_custom_module
    admin.GlobalAdminHandler.add_custom_get_action("course_categories", CourseCategoriesAdmin.get_course_categories)
    admin.GlobalAdminHandler.add_custom_get_action("add_course_category",CourseCategoriesAdmin.get_add_course_category)
    admin.GlobalAdminHandler.add_custom_get_action("edit_course_category",CourseCategoriesAdmin.get_edit_course_category)
    admin.BaseAdminHandler.add_menu_item('analytics', 'course_categories', 'Course Categories',
                          action='course_categories',contents=CourseCategoriesAdmin.get_course_categories, 
                          sub_group_name='advanced')