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

"""Common classes and methods for managing persistent entities."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import appengine_config
from google.appengine.ext import ndb

class GoogleServiceAccountTypes(object):
    SERVICE_ACCOUNT = 'service_account'
    API_KEY = 'api_key'
    OAUTH2_CLIENT_ID = 'oauth2_client_id'

    @classmethod
    def to_dict(cls):
        all_types = {}
        for attr_name in dir(cls):
            # Filter out inbuilt attributes and functions such as this one
            if attr_name.startswith('__') or callable(getattr(cls, attr_name)):
                continue
            all_types[attr_name] = getattr(cls, attr_name)
        return all_types

class GoogleServiceAccountSettings(ndb.Model):
    """Stores settings and credentials for google drive access"""

    # Type
    credential_type = ndb.StringProperty(
        indexed=False, choices=set(
            GoogleServiceAccountTypes.to_dict().values()))
    # Common
    client_email = ndb.StringProperty(indexed=False)
    sub_user_email = ndb.StringProperty(indexed=False)
    scope = ndb.StringProperty(repeated=True)
    # OAUTH2_CLIENT_ID, SERVICE_ACCOUNT
    client_id = ndb.StringProperty(indexed=False)
    # API_KEY
    api_key = ndb.StringProperty(indexed=False)
    # SERVICE_ACCOUNT
    project_id = ndb.StringProperty(indexed=False)
    project_key_id = ndb.StringProperty(indexed=False)
    private_key = ndb.TextProperty(indexed=False)
    auth_uri = ndb.StringProperty(indexed=False)
    token_uri = ndb.StringProperty(indexed=False)
    auth_provider_x509_cert_url = ndb.StringProperty(indexed=False)
    client_x509_cert_url = ndb.StringProperty(indexed=False)

    @property
    def id(self):
        try:
            return self.key.id()
        except AttributeError:
            # Object probably not saved. Return None.
            return None

    @classmethod
    def get_or_create(cls, id, namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        entry = cls.get_by_id(id, namespace=namespace)
        if not entry:
            entry = cls(id=id, namespace=namespace)
        return entry

class GoogleServiceAccountSettingsDTO(object):
    """DTO for GoogleServiceAccountSettings"""

    def __init__(self, obj):
        if not obj:
            return None
        self.id = obj.id
        self.credential_type = obj.credential_type
        self.client_email = obj.client_email
        self.sub_user_email = obj.sub_user_email
        self.scope = obj.scope
        self.client_id = obj.client_id
        self.api_key = obj.api_key
        self.project_id = obj.project_id
        self.project_key_id = obj.project_key_id
        self.private_key = obj.private_key
        self.auth_uri = obj.auth_uri
        self.token_uri = obj.token_uri
        self.auth_provider_x509_cert_url = obj.auth_provider_x509_cert_url
        self.client_x509_cert_url = obj.client_x509_cert_url

    def to_dict(self):
        """Returns a dict of this object"""
        obj_dict = dict()
        try:
            for attr in self.attribute_names():
                obj_dict[attr] = getattr(self, attr)
        except AttributeError:
            return None
        return obj_dict

    def attribute_names(self):
        """
        Returns a list of the attribute names of a GoogleServiceAccountSettings
        database object.
        """
        attr_list = [
            attr for attr in dir(self)
            if not attr.startswith('__') and
            not callable(getattr(self, attr))
        ]
        return attr_list
