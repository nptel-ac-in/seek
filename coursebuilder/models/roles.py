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

"""Manages mapping of users to roles and roles to privileges."""

__author__ = 'Pavel Simakov (psimakov@google.com)'

import collections
import config
import messages
import json

from google.appengine.api import namespace_manager

from common import utils
from common import caching
from common import users
from models import MemcacheManager
from models import RoleDAO
from course_list import CourseListDAO

GCB_ADMIN_LIST = config.ConfigProperty(
    'gcb_admin_user_emails', str, messages.SITE_SETTINGS_SITE_ADMIN_EMAILS, '',
    label='Site Admin Emails', multiline=True)

KEY_COURSE = 'course'
KEY_ADMIN_USER_EMAILS = 'admin_user_emails'

GCB_WHITELISTED_USERS = config.ConfigProperty(
    'gcb_user_whitelist', str, messages.SITE_SETTINGS_WHITELIST, '',
    label='Whitelist', multiline=True)

Permission = collections.namedtuple('Permission', ['name', 'description'])

class CourseAdminCache(caching.RequestScopedSingleton):
    """Class that manages optimized checking for course admin status."""

    def __init__(self):
        self._course_admin_dict = {}

    @classmethod
    def _key(cls, app_context):
        """Make key specific to current namespace and user."""
        user = users.get_current_user()
        if not user:
            return
        if not app_context:
            return
        return '%s:%s' % (
            users.get_current_user().email(), app_context.namespace)

    def _is_course_admin(self, app_context):
        key = self._key(app_context)
        if key in self._course_admin_dict:
            return self._course_admin_dict[key]

    def _set_course_admin_status(self, app_context, value):
        key = self._key(app_context)
        self._course_admin_dict[key] = value

    @classmethod
    def is_course_admin(cls, app_context):
        # pylint: disable=protected-access
        return cls.instance()._is_course_admin(app_context)

    @classmethod
    def set_course_admin_status(cls, app_context, value):
        cls.instance()._set_course_admin_status(app_context, value)


class Roles(object):
    """A class that provides information about user roles."""

    # Maps module names to callbacks which generate permissions.
    # See register_permissions for the structure of the callbacks.
    _REGISTERED_PERMISSIONS = collections.OrderedDict()

    memcache_key = 'roles.Roles.users_to_permissions_map'

    @classmethod
    def is_direct_super_admin(cls):
        """Checks if current user is a super admin, without delegation."""
        return users.get_current_user() and users.is_current_user_admin()

    @classmethod
    def is_super_admin(cls):
        """Checks if current user is a super admin, possibly via delegation."""
        if cls.is_direct_super_admin():
            return True
        return cls._user_email_in(users.get_current_user(),
                                  GCB_ADMIN_LIST.value)

    @classmethod
    def is_course_admin(cls, app_context=None, course_list_obj=None):
        """Checks if a user is a course admin, possibly via delegation."""

        if cls.is_super_admin():
            return True

        cached_is_course_admin = CourseAdminCache.is_course_admin(app_context)
        if cached_is_course_admin is not None:
            return cached_is_course_admin

        course_admin_email = None
        if app_context and app_context.course_admin_email is not None:
            user = users.get_current_user()
            is_course_admin = cls._user_email_in(
                user, app_context.course_admin_email)
            CourseAdminCache.set_course_admin_status(
                app_context, is_course_admin)
            return is_course_admin
        elif course_list_obj:
            user = users.get_current_user()
            if cls._user_email_in(user, course_list_obj.course_admin_email):
                return True
            return False
        else:
            raise ValueError("Must provide either app_context or course_list")

    @classmethod
    def is_user_whitelisted(cls, app_context=None, course_list_obj=None):
        user = users.get_current_user()
        global_whitelist = GCB_WHITELISTED_USERS.value.strip()

        if app_context:
            course_whitelist = app_context.whitelist.strip()
        elif course_list_obj:
            course_whitelist = course_list_obj.whitelist.strip()
        else:
            raise ValueError("Must provide either app_context or course_list")

        # Most-specific whitelist used if present.
        if course_whitelist:
            return cls._user_email_in(user, course_whitelist)

        # Global whitelist if no course whitelist
        elif global_whitelist:
            return cls._user_email_in(user, global_whitelist)

        # Lastly, no whitelist = no restrictions
        else:
            return True

    @classmethod
    def _user_email_in(cls, user, text):

        if not user:
            return False
        email = user.email().lower()
        if not email:
            return False
        match_to = set([email])
        if '@' in email:
            domain = email.split('@')[-1]
            if domain:
                match_to.add(domain)
                match_to.add('@' + domain)
        if isinstance(text, basestring):
            allowed = set([email.lower() for email in utils.text_to_list(
                text, utils.BACKWARD_COMPATIBLE_SPLITTER)])
        else:
            allowed = set(text)
        return bool(match_to & allowed)

    @classmethod
    def update_permissions_map(cls,app_context):
        """Puts a dictionary mapping users to permissions in memcache.

        A dictionary is constructed, using roles information from the datastore,
        mapping user emails to dictionaries that map module names to
        sets of permissions.

        Returns:
            The created dictionary.
        """
        permissions_map = {}
        for role in RoleDAO.get_all():
            for user in role.users:
                user_permissions = permissions_map.setdefault(user, {})
                for (module_name, permissions) in role.permissions.iteritems():
                    module_permissions = user_permissions.setdefault(
                        module_name, set())
                    module_permissions.update(permissions)

        MemcacheManager.set(cls.memcache_key, permissions_map)

        #Create a simple dict which can be serialized and save it to course list
        role_permissions_map = {}
        for role in RoleDAO.get_all():
            for user in role.users:
                user_permissions = role_permissions_map.setdefault(user, {})
                for (module_name, permissions) in role.permissions.iteritems():
                    module_permissions = user_permissions.setdefault(
                        module_name, [])
                    module_permissions.extend(permissions)
        namespace = app_context.namespace
        CourseListDAO.update_course_details(namespace,  permissions =  json.dumps(role_permissions_map))

        return permissions_map

    @classmethod
    def load_permissions_map(cls,app_context):
        """Loads the permissions map from Memcache or creates it if needed."""
        permissions_map = MemcacheManager.get(cls.memcache_key)
        if permissions_map is None:  # As opposed to {}, which is valid.
            permissions_map = cls.update_permissions_map(app_context)
        return permissions_map


    @classmethod
    def is_user_allowed(cls, app_context, module, permission):
        """Check whether the current user is assigned a certain permission.

        Args:
            app_context: sites.ApplicationContext of the relevant course
            module: module object that registered the permission.
            permission: string specifying the permission.

        Returns:
            boolean indicating whether the current user is allowed to perform
                the action associated with the permission.
        """
        if cls.is_course_admin(app_context):
            return True
        if not module or not permission or not users.get_current_user():
            return False
        permissions_map =  app_context.permissions()
        user_permissions = permissions_map.get(users.get_current_user().email(), {})
        return permission in user_permissions.get(module.name, [])

    @classmethod
    def in_any_role(cls, app_context=None, course_list_obj=None,
                    force_course_namespace=False):
        old_namespace = namespace_manager.get_namespace()
        if app_context:
            new_namespace = app_context.namespace
        elif course_list_obj:
            new_namespace = course_list_obj.namespace
        elif force_course_namespace:
            raise ValueError("Must provide either app_context or course_list")

        with utils.Namespace(
                new_namespace if force_course_namespace else old_namespace):
            user = users.get_current_user()
            if not user:
                return False
            if course_list_obj:
                permissions_map = json.loads(
                    course_list_obj.permissions if course_list_obj.permissions
                    else '{}')
            else:
                permissions_map = app_context.permissions()
            user_permissions = permissions_map.get(user.email(), {})
            return bool(user_permissions)

    @classmethod
    def register_permissions(cls, module, callback_function):
        """Registers a callback function that generates permissions.

        A callback should return an iteratable of permissions of the type
            Permission(permission_name, permission_description)

        Example:
            Module 'module-werewolf' registers permissions 'can_howl' and
            'can_hunt' by defining a function callback_werewolf returning:
            [
                Permission('can_howl', 'Can howl to the moon'),
                Permission('can_hunt', 'Can hunt for sheep')
            ]
            In order to register these permissions the module calls
                register_permissions(module, callback_werewolf) with the module
                whose module.name is 'module-werewolf'.

        Args:
            module: module object that registers the permissions.
            callback_function: a function accepting ApplicationContext as sole
                argument and returning a list of permissions.
        """
        assert module is not None
        assert module.name
        assert module not in cls._REGISTERED_PERMISSIONS
        cls._REGISTERED_PERMISSIONS[module] = callback_function

    @classmethod
    def unregister_permissions(cls, module):
        del cls._REGISTERED_PERMISSIONS[module]

    @classmethod
    def get_modules(cls):
        return cls._REGISTERED_PERMISSIONS.iterkeys()

    @classmethod
    def get_permissions(cls):
        return cls._REGISTERED_PERMISSIONS.iteritems()
