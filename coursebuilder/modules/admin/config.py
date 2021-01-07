# Copyright 2012 Google Inc. All Rights Reserved.
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

__author__ = 'Pavel Simakov (psimakov@google.com)'

import cgi
import logging
import re
import urllib
import csv

import appengine_config
from common import safe_dom
from common import crypto
from common import users
from common import utils as common_utils
from controllers import sites
from controllers import utils
from models import config
from models import courses
from models import entities
from models import models
from models import roles
from models import transforms
from models import course_list
from modules.oeditor import oeditor

from google.appengine.api import namespace_manager
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.ext.db import metadata

# This is a template because the value type is not yet known.
SCHEMA_JSON_TEMPLATE = """
    {
        "id": "Configuration Property",
        "type": "object",
        "description": "Configuration Property Override",
        "properties": {
            "label" : {"optional": true, "type": "string"},
            "name" : {"optional": true, "type": "string"},
            "value": {"optional": true, "type": "%s"}
        }
    }
    """

# This is a template because the doc_string is not yet known.
SCHEMA_ANNOTATIONS_TEMPLATE = [
    (['title'], 'Configuration Property Override'),
    (['properties', 'label', '_inputex'], {
        'label': 'Setting Name', '_type': 'uneditable'}),
    (['properties', 'name', '_inputex'], {
        'label': 'Internal Name', '_type': 'uneditable'}),
]


class ConfigPropertyRights(object):
    """Manages view/edit rights for configuration properties."""

    @classmethod
    def can_view(cls):
        return cls.can_edit()

    @classmethod
    def can_edit(cls):
        return roles.Roles.is_super_admin()

    @classmethod
    def can_delete(cls):
        return cls.can_edit()

    @classmethod
    def can_add(cls):
        return cls.can_edit()


class ConfigPropertyEditor(object):
    """An editor for any configuration property."""

    # Map of configuration property type into inputex type.
    type_map = {str: 'string', int: 'integer', bool: 'boolean'}

    @classmethod
    def get_schema_annotations(cls, config_property):
        """Gets editor specific schema annotations."""
        doc_string = '%s Default: \'%s\'.' % (
            config_property.doc_string, config_property.default_value)
        item_dict = [] + SCHEMA_ANNOTATIONS_TEMPLATE
        item_dict.append((
            ['properties', 'value', '_inputex'], {
                'label': 'Value', '_type': '%s' % cls.get_value_type(
                    config_property),
                'description': doc_string}))
        return item_dict

    @classmethod
    def get_value_type(cls, config_property):
        """Gets an editor specific type for the property."""
        value_type = cls.type_map[config_property.value_type]
        if not value_type:
            raise Exception('Unknown type: %s', config_property.value_type)
        if config_property.value_type == str and config_property.multiline:
            return 'text'
        return value_type

    @classmethod
    def get_schema_json(cls, config_property):
        """Gets JSON schema for configuration property."""
        return SCHEMA_JSON_TEMPLATE % cls.get_value_type(config_property)

    def get_add_course(self):
        """Handles 'add_course' action and renders new course entry editor."""

        if roles.Roles.is_super_admin():
            exit_url = '{}?action=courses'.format(self.LINK_URL)
        else:
            exit_url = self.request.referer
        rest_url = CoursesItemRESTHandler.URI

        template_values = {}
        template_values['page_title'] = self.format_title('Add Course')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, CoursesItemRESTHandler.SCHEMA_JSON,
            CoursesItemRESTHandler.SCHEMA_ANNOTATIONS_DICT,
            None, rest_url, exit_url,
            auto_return=True,
            save_button_caption='Add New Course')

        self.render_page(template_values, in_action='courses')


    def get_run_courlist_migration(self):
        """Handles 'run_courlist_migration' property action."""
        template_values = {}
        template_values['page_title'] = self.format_title('Run Courlist Migration')
        content =  safe_dom.NodeList()

        content.append(safe_dom.Element(
            'link', rel='stylesheet',
            href='/modules/admin/resources/css/admin.css'))
        table = safe_dom.Element('table', className='gcb-config').add_child(
            safe_dom.Element('tr').add_child(
                safe_dom.Element('th').add_text('Entity')
            ).add_child(
                safe_dom.Element('th').add_text('Exists?')
            ).add_child(
                safe_dom.Element('th').add_text('Adding?')
            ))
        content.append(
            safe_dom.Element('h3').add_text('Courlist Migrations')
        ).append(table)


        item = config.Registry.registered["gcb_courses_config"]

        rules_text = item.value
        rules_text = rules_text.replace(',', '\n')
        contexts = sites.get_course_list_from_config(rules_text)
        for course in contexts:
            namespace = course.namespace
            exists =  course_list.CourseList.get_by_key_name(namespace)

            tr = safe_dom.Element('tr')
            table.add_child(tr)
            tr.add_child(
            safe_dom.Element(
                'td', style='white-space: nowrap;').add_text(namespace))

            if exists:
                tr.add_child(
                safe_dom.Element(
                'td', style='white-space: nowrap;').add_text("Yes"))
                tr.add_child(
                safe_dom.Element(
                'td', style='white-space: nowrap;').add_text("N.A"))
            else:
                tr.add_child(
                safe_dom.Element(
                'td', style='white-space: nowrap;').add_text("No"))
                path = course.slug
                title =  course.title
                errors = []
		course_list.CourseListDAO.add_new_course(namespace=namespace,
                    path=path, title=title, errors=errors)
                if len(errors) > 0:
                    tr.add_child(
                    safe_dom.Element(
                        'td', style='white-space: nowrap;').add_text("Failed"))
                else:
                    tr.add_child(
                    safe_dom.Element(
                        'td', style='white-space: nowrap;').add_text("Success"))
                    settings = course.get_environ()
                    if 'reg_form' not in settings:
                        settings['reg_form'] = dict()
                    if 'explorer' not in settings:
                        settings['explorer'] = dict()
                    reg_form = settings.get('reg_form')
                    c = settings.get('course')
                    explorer = settings['explorer']

                    if reg_form.get('opening_soon', False):
                        registration='OPENING_SHORTLY'
                    elif reg_form.get('can_register', False):
                        registration='OPEN'
                    else:
                        registration='CLOSED'
                    explorer['closed'] = c.get('closed', False)
                    reg_form['registration'] = registration
                    if 'welcome_email' in reg_form and reg_form['welcome_email'].strip():
                        c['send_welcome_notifications'] = True
                        c['welcome_notifications_sender'] = 'onlinecourses@nptel.iitm.ac.in'
                        c['welcome_notifications_subject'] = 'Welcome To ' + c['title']
                        c['welcome_notifications_body'] = reg_form['welcome_email']

		    course_list.CourseListConnector.save_settings(courses.Course(None, app_context=course), settings)

        template_values['main_content'] = content
        self.render_page(template_values, in_tab='migration')


    def get_config_edit(self):
        """Handles 'edit' property action."""

        key = self.request.get('name')
        if not key:
            self.redirect('%s?action=settings' % self.URL)

        item = config.Registry.registered[key]
        if not item:
            self.redirect('%s?action=settings' % self.URL)

        template_values = {}
        template_values['page_title'] = self.format_title('Edit Settings')

        exit_url = '%s?action=settings#%s' % (
            self.LINK_URL, cgi.escape(key))
        rest_url = '/rest/config/item'
        delete_url = '%s?%s' % (
            self.LINK_URL,
            urllib.urlencode({
                'action': 'config_reset',
                'name': key,
                'xsrf_token': cgi.escape
                    (self.create_xsrf_token('config_reset'))}))
        # Suppress delete button when setting is not currently overridden
        with common_utils.Namespace(appengine_config.DEFAULT_NAMESPACE_NAME):
            try:
                entity = config.ConfigPropertyEntity.get_by_key_name(key)
            except db.BadKeyError:
                entity = None
        if not entity or entity.is_draft:
            delete_url = None

        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, ConfigPropertyEditor.get_schema_json(item),
            ConfigPropertyEditor.get_schema_annotations(item),
            key, rest_url, exit_url, delete_url=delete_url)

        self.render_page(template_values, in_action='settings')

    def post_config_reset(self):
        """Handles 'reset' property action."""
        name = self.request.get('name')

        # Find item in registry.
        item = None
        if name and name in config.Registry.registered.keys():
            item = config.Registry.registered[name]
        if not item:
            self.redirect('%s?action=settings' % self.LINK_URL)

        with common_utils.Namespace(appengine_config.DEFAULT_NAMESPACE_NAME):
            # Delete if exists.
            try:
                entity = config.ConfigPropertyEntity.get_by_key_name(name)
                if entity:
                    old_value = entity.value
                    entity.delete()

                    models.EventEntity.record(
                        'delete-property', users.get_current_user(),
                        transforms.dumps({
                            'name': name, 'value': str(old_value)}))

            except db.BadKeyError:
                pass

        self.redirect('%s?action=settings' % self.URL)


class CoursesPropertyRights(object):
    """Manages view/edit rights for configuration properties."""

    @classmethod
    def can_add(cls):
        if roles.Roles.is_super_admin():
            return True
        for course_context in sites.get_all_courses():
            if roles.Roles.is_course_admin(course_context):
                return True
        return False


class CoursesItemRESTHandler(utils.BaseRESTHandler):
    """Provides REST API for course entries.

    Modules can register to be called back when a new course has been
    successfully created. Callbacks are registered like this:

        config.CoursesItemRESTHandler.NEW_COURSE_ADDED_HOOKS[
            'my_module'] = my_handler

    New course callbacks are called a single time, and in no particular order,
    via common.utils.run_hooks().

    New course callbacks must accept two parameters:
        - app_context
        - errors, a (possibly non-empty) list to which any errors occurring
            during the callback are appended
    """

    NEW_COURSE_ADDED_HOOKS = {}

    # Enable other modules to make changes to sample course import.
    # Each member must be a function of the form:
    #     callback(course, errors)
    COPY_SAMPLE_COURSE_HOOKS = []

    URI = '/rest/courses/item'
    XSRF_ACTION = 'add-course-put'


    def put(self):
        """Handles HTTP PUT verb."""
        request = transforms.loads(self.request.get('request'))
        if not self.assert_xsrf_token_or_fail(
                request, self.XSRF_ACTION, {}):
            return

        if not CoursesPropertyRights.can_add():
            self._send_json_error_response(401, 'Access denied.')
            return

        payload = request.get('payload')
        json_object = transforms.loads(payload)
        course_add_type = json_object.get('type')
        if course_add_type == 'add-course':
            name = json_object.get('name')
            title = json_object.get('title')
            admin_email = json_object.get('admin_email')
            template_course = json_object.get('template_course')
            status_code, errors = self._put_new_course_entry(name, title, admin_email,template_course)
            transforms.send_json_response(self, status_code, '\n'.join(errors))

        else:
            all_messages = []
            at_least_one_error = False
            add_multi_course_content = json_object.get('content')
            reader = csv.reader(add_multi_course_content.split('\n'), delimiter=',')
            for row in reader:
                if len(row) is not 3:
                    continue
                name = row[0]
                admin_email = row[1]
                title = row[2]
                template_course = None            
                status_code, errors = self._put_new_course_entry(name, title, admin_email)
                all_messages.extend(errors)
                if status_code is not 200:
                    at_least_one_error = True
                    

            if at_least_one_error:
                transforms.send_json_response(self, 412, '\n'.join(all_messages))
            else:
                transforms.send_json_response(self, 200, 'All added')

    def _put_new_course_entry(self,name, title, admin_email,template_course=None):
        # Add the new course entry.
        namespace = 'ns_' + name
        errors = []
        with common_utils.Namespace(namespace):
            if CourseDeleteHandler.get_any_undeleted_kind_name():
                errors.append(
                    'Unable to add new entry "%s": the corresponding '
                    'namespace "%s" is not empty.  If you removed a '
                    'course with that name in the last few minutes, the '
                    'background cleanup job may still be running.  '
                    'You can use the App Engine Dashboard to manually '
                    'remove all database entities from this namespace.' %
                    (name, namespace))

        # Add the new course entry.
        if not errors:
            entry = sites.add_new_course_entry(name, title, admin_email, errors)
            if not entry and not errors:
                errors.append('Error adding a new course entry.')
        if errors:
            return 412, errors

        # We can't expect our new configuration being immediately available due
        # to datastore queries consistency limitations. So we will instantiate
        # our new course here and not use the normal sites.get_all_courses().
        if sites.USE_COURSE_LIST:
            app_context = sites.get_app_context_for_namespace('ns_%s' % name)
        else:
            app_context = sites.get_all_courses(entry)[0]

        # Update course with a new title and admin email.
        new_course = courses.Course(None, app_context=app_context)
        if not new_course.init_new_course_settings(title, admin_email):
            errors.append("""Added new course entry, but failed to update title and/or 
                        admin email. The course.yaml file already exists and must be 
                        updated manually.""")
            return 412, errors

        if template_course:
            if template_course != 'sample':
                errors.append('Unknown template course: %s' % template_course)
                return 412, errors 
            errors = []
            src_app_context = sites.get_all_courses('course:/:/:')[0]
            new_course.import_from(src_app_context, errors)
            new_course.save()
            if not errors:
                common_utils.run_hooks(
                    self.COPY_SAMPLE_COURSE_HOOKS, app_context, errors)
            if errors:
                return 412, errors


        if not errors:
            common_utils.run_hooks(
                self.NEW_COURSE_ADDED_HOOKS.itervalues(), app_context, errors)

        if errors:
            # Any errors at this point are the result of one or more failed
            # _HOOKS callbacks. It is probably not possible to determine if
            # these are caused by bad server state or instead by bad user
            # input, so return a rather generic 500 HTTP status.
            if isinstance(errors, basestring):
                errors = [errors]
            return 500, errors
        else:
            errors.append('Added. ns_%s' % name)
            return 200, errors

class Model(object):
    """Mock of App Engine db.Model class; helps build keys-only .all() queries.

    CourseDeleteHandler, below, needs to delete all entries for all model
    types in the datastore.  In theory, we could call db.class_for_kind(),
    but it turns out that in practice, a) the entity type may be an old
    leftover and the code for that class is gone, b) the entity type is for
    a Course Builder module that is not currently enabled, or c) it's in
    some module that overrides the .kind() method to return some other name
    than the class name (I'm looking at _you_, MapReduce), and we just can't
    get the class.

    Lucky us, though - it turns out that queries that are only interested in
    fetching keys only need the db.Model to respond to .kind(), and so an
    instance of this class can be used in place of an actual class derived
    from db.Model when building such a query.
    """

    def __init__(self, kind):
        self._kind = kind

    def kind(self):
        return self._kind


class CourseUpdateHandler(utils.BaseHandler):

    URI = '/course/update'
    XSRF_ACTION = 'course_update'


    def post(self):
        user = users.get_current_user()
        namespace = namespace_manager.get_namespace();
        if not roles.Roles.is_course_admin(self.app_context):
            self.error(401)
            return
        if not self.assert_xsrf_token_or_fail(self.request, self.XSRF_ACTION):
            return
        if namespace == '':
            self.error(400)
            return

        if self.request.get('spoc_mentor') is not None and self.request.get('spoc_mentor') is not '':
            spoc_mentor = True if self.request.get('spoc_mentor') == "True" else False
            course_list.CourseListDAO.update_course_details(namespace,spoc_mentor=spoc_mentor);

        self.redirect('/modules/admin?action=courses', normalize=False)


class CourseDeleteHandler(utils.BaseHandler):
    """Handles course deletion requests.

    Modules can register to be called back when deletion of a course has
    completed (during the last iteration of delete_course(), once no more
    entities associated with the course exist in the Datastore).  Callbacks
    are registered like this:

        config.CourseDeleteHandler.COURSE_DELETED_HOOKS[
            'my_module'] = my_handler

    Course deletion callbacks are called a single time, and in no particular
    order, via common.utils.run_hooks().

    Course deletion callbacks must accept a single parameter:
        - the namespace_name (a string)
    """

    COURSE_DELETED_HOOKS = {}

    URI = '/course/delete'
    XSRF_ACTION = 'course_delete'
    DELETE_BATCH_SIZE = 1000
    IGNORE_KINDS = re.compile(r'__.*__$|_ah_SESSION$|__unapplied_write')

    def post(self):
        user = users.get_current_user()
        if not roles.Roles.is_course_admin(self.app_context):
            self.error(401)
            return
        if not self.assert_xsrf_token_or_fail(self.request, self.XSRF_ACTION):
            return
        if namespace_manager.get_namespace() == '':
            self.error(400)
            return

        sites.remove_course(self.app_context)
        deferred.defer(self.delete_course)

        if self.request.get('is_selected_course') == 'True':
            # If we are deleting the course the UI is currently selected for,
            # redirect to the global handler.
            self.redirect('/modules/admin?action=courses', normalize=False)
        else:
            self.redirect(self.request.referer)

    @classmethod
    def get_any_undeleted_kind_name(cls):
        for kind in common_utils.iter_all(metadata.Kind.all()):
            kind_name = kind.kind_name
            if not cls.IGNORE_KINDS.match(kind_name):
                return kind_name
        return None

    @classmethod
    def delete_course(cls):
        """Called back repeatedly from deferred queue dispatcher."""
        try:
            kind_name = cls.get_any_undeleted_kind_name()
            if not kind_name:
                # No entity types remain to be deleted from the Datastore for
                # this course (i.e. namespace), so call (in no particular
                # order) callbacks waiting to be informed of course deletion.
                ns_name = namespace_manager.get_namespace()
                common_utils.run_hooks(
                    cls.COURSE_DELETED_HOOKS.itervalues(), ns_name)
                logging.info(
                    'CourseDeleteHandler found no entity types to delete for '
                    'namespace %s; deletion complete.', ns_name)
                return

            model = Model(kind_name)
            keys = list(db.Query(Model(kind_name), keys_only=True).run(
                batch_size=cls.DELETE_BATCH_SIZE))
            entities.delete(keys)
            logging.info(
                'CourseDeleteHandler deleted %d entities of type %s from '
                'namespace %s', len(keys), kind_name,
                namespace_manager.get_namespace())
            deferred.defer(cls.delete_course)
        except Exception:
            logging.critical(
                'Failed when attempting to delete course for namespace %s',
                namespace_manager.get_namespace())
            common_utils.log_exception_origin()
            raise


class ConfigPropertyItemRESTHandler(utils.BaseRESTHandler):
    """Provides REST API for a configuration property."""

    def get(self):
        """Handles REST GET verb and returns an object as JSON payload."""
        key = self.request.get('key')
        if not ConfigPropertyRights.can_view():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        item = None
        if key and key in config.Registry.registered.keys():
            item = config.Registry.registered[key]
        if not item:
            self.redirect('/admin?action=settings')

        try:
            entity = config.ConfigPropertyEntity.get_by_key_name(key)
        except db.BadKeyError:
            entity = None

        entity_dict = {'name': key, 'label': item.label}
        if entity and not entity.is_draft:
            entity_dict['value'] = transforms.string_to_value(
                entity.value, item.value_type)
        else:
            entity_dict['value'] = item.default_value
        json_payload = transforms.dict_to_json(entity_dict)
        transforms.send_json_response(
            self, 200, 'Success.',
            payload_dict=json_payload,
            xsrf_token=crypto.XsrfTokenManager.create_xsrf_token(
                'config-property-put'))

    def put(self):
        """Handles REST PUT verb with JSON payload."""
        request = transforms.loads(self.request.get('request'))
        key = request.get('key')

        if not self.assert_xsrf_token_or_fail(
                request, 'config-property-put', {'key': key}):
            return

        if not ConfigPropertyRights.can_edit():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        item = None
        if key and key in config.Registry.registered.keys():
            item = config.Registry.registered[key]
        if not item:
            self.redirect('/admin?action=settings')

        try:
            entity = config.ConfigPropertyEntity.get_by_key_name(key)
        except db.BadKeyError:
            transforms.send_json_response(
                self, 404, 'Object not found.', {'key': key})
            return
        if not entity:
            entity = config.ConfigPropertyEntity(key_name=key)
            old_value = None
        else:
            old_value = entity.value

        payload = request.get('payload')
        json_object = transforms.loads(payload)
        new_value = item.value_type(json_object['value'])

        # Validate the value.
        errors = []
        if item.validator:
            item.validator(new_value, errors)
        if errors:
            transforms.send_json_response(self, 412, '\n'.join(errors))
            return

        # Update entity.

        entity.value = str(new_value)
        entity.is_draft = False
        entity.put()
        if item.after_change:
            item.after_change(item, old_value)

        models.EventEntity.record(
            'put-property', users.get_current_user(), transforms.dumps({
                'name': key,
                'before': str(old_value), 'after': str(entity.value)}))

        transforms.send_json_response(self, 200, 'Saved.')
