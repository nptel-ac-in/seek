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

"""Classes supporting configuration property editor and REST operations."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


import yaml
import StringIO
import cgi
import csv

from common import tags
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
from modules.course_explorer import layout
from modules.oeditor import oeditor


def create_explorer_page_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Explorer Page', description='Explorer Page',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})

    # Course level settings.
    course_opts = reg.add_sub_registry('top_half', 'Top Half')
    course_opts.add_property(SchemaField(
        'top_text', 'Top Text', 'html', optional=False,
        description=('Problem Statement and description of program, visible'
                     ' to student.'),
        extra_schema_dict_values={
            'supportCustomTags': tags.CAN_USE_DYNAMIC_TAGS.value,
            'className': 'inputEx-Field content'}))
    course_opts.add_property(SchemaField(
        'video_id', 'Right hand side video', 'string',
	optional=True))

    category_list_items = FieldRegistry('', '')
    category_list_items.add_property(SchemaField(
        'category', 'Category', 'string', optional=True,
        extra_schema_dict_values={}, select_data=[]))
    category_list_opts = FieldArray(
        'category_list', 'Category Order', item_type=category_list_items,
        extra_schema_dict_values={
            'sortable': True,
            'listAddLabel': 'Add Category',
            'listRemoveLabel': 'Delete Category'})
    cli = reg.add_sub_registry('category_list', 'Category List')
    cli.add_property(category_list_opts)
    return reg


class ExplorerPageRESTHandler(BaseRESTHandler):
    """Provides REST API to prog assignment."""

    URI = '/rest/modules/course_explorer/layout'
    DESCRIPTION = 'Explore Page Layout'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_explorer_page_registry().get_json_schema()
    KEY = 'layout'

    @classmethod
    def get_schema_annotations_dict(cls):
        category_list = []
        for c in course_category.CourseCategoryDAO.get_category_list():
            category_list.append(
		    (c.category, cgi.escape(c.description)))
        extra_select_options = dict()
        extra_select_options['category_list'] = dict()
        extra_select_options['category_list']['category_list'] = dict()
        extra_select_options['category_list']['category_list']['category'] = category_list
        return  cls.registration().get_schema_dict(extra_select_options=extra_select_options)

    @classmethod
    def registration(cls):
        return create_explorer_page_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self):
        """Assemble a dict with the unit data fields."""
        l = layout.ExplorerLayoutDAO.get_layout()
        entity = {
                'top_text': l.top_text,
                'video_id': l.right_video_id,
                'category_list': [{'category': item} for item in l.category_order],
                }
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)
        layout.ExplorerLayoutDAO.update_layout(
            top_text=entity_dict['top_text'],
            right_video_id=entity_dict['video_id'],
            category_order=[item['category'] for item in entity_dict['category_list']])

    def get(self):
        """A GET REST method shared by all unit types."""
        key = self.request.get('key')

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=self.to_dict(),
            xsrf_token=XsrfTokenManager.create_xsrf_token('update-layout'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'update-layout', {'key': self.KEY}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': self.KEY})
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
    """Provides REST API to prog assignment."""

    URI = '/rest/modules/course_explorer/category_list'
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
    """Provides REST API to prog assignment."""

    URI = '/rest/modules/course_explorer/add_new_category'
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



def create_course_category_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Course Category', description='Course Category',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})

    # Course level settings.
    reg.add_property(SchemaField(
	'id', 'Course id', 'string', editable=False))
    reg.add_property(SchemaField('title', 'Title', 'string', editable=False))

    reg.add_property(SchemaField(
        'category', 'Category', 'string', optional=True,
        extra_schema_dict_values={}, select_data=[('', '--')]))
    return reg


class CourseCategoryRESTHandler(BaseRESTHandler):
    """Provides REST API to prog assignment."""

    URI = '/rest/modules/course_explorer/course_category'
    DESCRIPTION = 'Explore Page Layout'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_course_category_registry().get_json_schema()

    @classmethod
    def get_schema_annotations_dict(cls):
        category_list = []
        for c in course_category.CourseCategoryDAO.get_category_list():
            category_list.append(
		    (c.category, cgi.escape(c.description)))
        extra_select_options = dict()
        extra_select_options['category'] = category_list
        return  cls.registration().get_schema_dict(extra_select_options=extra_select_options)

    @classmethod
    def registration(cls):
        return create_course_category_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self, key, errors):
        """Assemble a dict with the unit data fields."""
        c = course_list.CourseListDAO.get_course_for_namespace(key)
        if not c:
            errors.append('Course %s not found' % key)
            return
        entity = {
                'id': c.namespace,
                'title': c.title,
		'category': c.category, }
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)
        course_list.CourseListDAO.update_course_details(
             entity_dict['id'], category=entity_dict['category'])

    def get(self):
        """A GET REST method shared by all unit types."""
        key = self.request.get('key')

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        errors = []
        payload_dict=self.to_dict(key, errors)
        if errors:
            transforms.send_json_response(
                self, 404, 'Object Not found.', {'key': key})
            return
        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=payload_dict,
            xsrf_token=XsrfTokenManager.create_xsrf_token('update-course-category'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))
        key = self.request.get('key')

        if not self.assert_xsrf_token_or_fail(
                request, 'update-course-category', {'key': key}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': self.KEY})
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


def create_course_featured_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Course Featured', description='Course Featured',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})

    # Course level settings.
    reg.add_property(SchemaField('id', 'Course id', 'string', editable=False))
    reg.add_property(SchemaField('title', 'Title', 'string', editable=False))
    reg.add_property(SchemaField('featured', 'Featured', 'boolean', optional=True))
    return reg



class CourseFeaturedRESTHandler(BaseRESTHandler):
    """Provides REST API to handle featured course."""

    URI = '/rest/modules/course_explorer/course_featured'
    DESCRIPTION = 'Explore Page Layout'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number','inputex-boolean']
    SCHEMA_JSON = create_course_featured_registry().get_json_schema()

    @classmethod
    def get_schema_annotations_dict(cls):
        return  cls.registration().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_course_featured_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self, key, errors):
        """Assemble a dict with the unit data fields."""
        c = course_list.CourseListDAO.get_course_for_namespace(key)
        if not c:
            errors.append('Course %s not found' % key)
            return
        entity = {
                'id': c.namespace,
                'title': c.title,
                'featured': c.featured }
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        print str(entity)
        print str(json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)
        course_list.CourseListDAO.update_course_details(
             entity_dict['id'], featured=entity_dict['featured'])

    def get(self):
        """A GET REST method shared by all unit types."""
        key = self.request.get('key')

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        errors = []
        payload_dict=self.to_dict(key, errors)
        if errors:
            transforms.send_json_response(
                self, 404, 'Object Not found.', {'key': key})
            return
        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=payload_dict,
            xsrf_token=XsrfTokenManager.create_xsrf_token('update-course-featured'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))
        key = self.request.get('key')

        if not self.assert_xsrf_token_or_fail(
                request, 'update-course-featured', {'key': key}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': self.KEY})
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
