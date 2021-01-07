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

"""Role for Local Chapter Single Points of Contact (SPOC)."""

__author__ = 'Rishav Thakker (rthakker@google.com)'


from google.appengine.api import namespace_manager

import appengine_config
from common import users
from models import models
from models import roles
from common.utils import Namespace
from models import models
from models import permissions
from models import roles
from modules.spoc import base

custom_module = None


class SPOCRoleManager(object):
    """Contains functions for managing users in SPOC Role"""

    # Override if required. If set to None, the functions will not change the
    # existing namespace
    # TODO(rthakker) Perhaps it's better to use a function param instead of
    # class variable in this case since we may not always want to
    # inherit this class.
    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME

    @classmethod
    def add_spoc_emails_in_role(cls, spoc_emails):
        """Adds spoc email in role if required"""
        if not spoc_emails:
            return
        with Namespace(cls.TARGET_NAMESPACE):
            for role in models.RoleDAO.get_all():
                if role.name == base.SPOCBase.SPOC_ROLE_NAME:
                    emails_set = set([e.lower() for e in role.users])
                    add_emails_set = set([e.lower() for e in spoc_emails])
                    emails_set.update(add_emails_set)
                    if len(emails_set) > len(role.users):
                        # Some users have been added. Save.
                        role.dict['users'] = list(emails_set)
                        models.RoleDAO.save(role)
                    return

    @classmethod
    def remove_spoc_emails_from_role(cls, spoc_emails):
        """Removes spoc email from role"""
        if not spoc_emails:
            return
        with Namespace(cls.TARGET_NAMESPACE):
            for role in models.RoleDAO.get_all():
                if role.name == base.SPOCBase.SPOC_ROLE_NAME:
                    emails_set = set([e.lower() for e in role.users])
                    delete_emails_set = set([e.lower() for e in spoc_emails])
                    emails_set -= delete_emails_set
                    if len(emails_set) < len(role.users):
                        # Some users have been removed. Save.
                        role.dict['users'] = list(emails_set)
                        models.RoleDAO.save(role)
                    return

    @classmethod
    def is_global_spoc(cls, user):
        return user.email().lower() in base.GLOBAL_SPOC_EMAILS.value.lower()

    @classmethod
    def is_role_spoc(cls):
        with Namespace(cls.TARGET_NAMESPACE):
            user = users.get_current_user()
            if not user:
                return False
            if cls.is_global_spoc(user):
                return True
            for role in models.RoleDAO.get_all():
                if role.name == base.SPOCBase.SPOC_ROLE_NAME:
                    return (user.email().lower() in
                        [e.lower() for e in role.users])
        return False

    @classmethod
    def can_view(cls, action=None, app_context=None):
        return cls.is_role_spoc()

    @classmethod
    def can_edit(cls, action=None, app_context=None):
        return cls.can_view()


def create_spoc_role():
    """Creates the role for Local Chapter SPOC"""

    for role in models.RoleDAO.get_all():
        if (role.name == base.SPOCBase.SPOC_ROLE_NAME and
            role.permissions.get(custom_module.name, []) ==
            base.SPOCBase.SPOC_ROLE_PERMISSIONS):
            return

    role_dto = models.RoleDTO(None, {
        'name': base.SPOCBase.SPOC_ROLE_NAME,
        'permissions': {
            custom_module.name: base.SPOCBase.SPOC_ROLE_PERMISSIONS
        },
        'description': 'Ability to modify assessment due dates and scoring.',
        'users': list()})
    roles.RoleDAO.save(role_dto)

def on_module_enabled(spoc_custom_module, spoc_permissions):
    global custom_module # pylint: disable=global-statement
    custom_module = spoc_custom_module

    spoc_permissions.append(roles.Permission(
        base.SPOCBase.SPOC_PERMISSION,
        'Can view student details of local chapters.'))

    permissions.SchemaPermissionRegistry.add(
        base.SPOCBase.SCOPE_ADMIN,
        permissions.SimpleSchemaPermission(
            custom_module, base.SPOCBase.SPOC_PERMISSION
        )
    )

    create_spoc_role()
