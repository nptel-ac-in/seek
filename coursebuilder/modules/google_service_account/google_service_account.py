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

"""Utility to enable oauth2 settings for NPTEL."""

__author__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

import logging
import re

import httplib2
import appengine_config
from oauth2client.client import SignedJwtAssertionCredentials
from apiclient.discovery import build

from google.appengine.api import memcache

from modules.google_service_account.service_account_models import (
    GoogleServiceAccountTypes, GoogleServiceAccountSettings,
    GoogleServiceAccountSettingsDTO)

# In real life we'd check in a blank file and set up the code to error with a
# message pointing people to https://code.google.com/apis/console.

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]+$")
DEFAULT_HTTP_TIMEOUT = 10

class GoogleServiceManager(object):
    """Manage all the credentials/services"""

    # Services are added to this object as and when required by the respective
    # Modules
    _SERVICES = {}
    _MEMCACHE_KEY = 'service_account_credentials'
    _DEFAULT_CACHE_TTL_SECS = 3600

    @classmethod
    def _default_id_from_credential_type(cls, credential_type):
        """
        Returns the ID for the default settings object from credential type
        """
        return credential_type

    @classmethod
    def get_by_id(cls, id, namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """Fetches an entry from the database using its ID"""
        entity = GoogleServiceAccountSettings.get_by_id(id, namespace=namespace)
        if entity:
            return GoogleServiceAccountSettingsDTO(entity)

    @classmethod
    def update_service_account_settings(
            cls, id, namespace=appengine_config.DEFAULT_NAMESPACE_NAME,
            credential_type=None, client_email=None,
            sub_user_email=None, scope=None, client_id=None, api_key=None,
            project_id=None, project_key_id=None, private_key=None,
            auth_uri=None, token_uri=None, auth_provider_x509_cert_url=None,
            client_x509_cert_url=None):
        """Updates a GoogleServiceAccountSettings object"""
        obj = GoogleServiceAccountSettings.get_or_create(id, namespace)

        if credential_type is not None:
            obj.credential_type = credential_type
        if client_email is not None:
            obj.client_email = client_email
        if sub_user_email is not None:
            obj.sub_user_email = sub_user_email
        if scope is not None:
            obj.scope = scope
        if client_id is not None:
            obj.client_id = client_id
        if api_key is not None:
            obj.api_key = api_key
        if project_id is not None:
            obj.project_id = project_id
        if project_key_id is not None:
            obj.project_key_id = project_key_id
        if private_key is not None:
            obj.private_key = private_key
        if auth_uri is not None:
            obj.auth_uri = auth_uri
        if token_uri is not None:
            obj.token_uri = token_uri
        if auth_provider_x509_cert_url is not None:
            obj.auth_provider_x509_cert_url = auth_provider_x509_cert_url
        if client_x509_cert_url is not None:
            obj.client_x509_cert_url = client_x509_cert_url

        # call initialize_credentials again if required
        if credential_type == GoogleServiceAccountTypes.SERVICE_ACCOUNT:
            if not cls.initialize_credentials(
                    service_account_settings=obj, namespace=namespace):
                return None

        # Save and return
        obj.put()
        return GoogleServiceAccountSettingsDTO(obj)

    @classmethod
    def get_default_settings_by_type(cls, credential_type,
            namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """Returns the default settings object for a credential type"""
        id = cls._default_id_from_credential_type(credential_type)
        entry = cls.get_by_id(id, namespace=namespace)
        return entry

    @classmethod
    def get_or_create_default_settings_by_type(cls, credential_type,
            namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """
        Returns the default settings object for a credential type.
        Creates a new object and returns it if none exist.
        """
        entry = cls.get_default_settings_by_type(credential_type, namespace)
        if not entry:
            id = cls._default_id_from_credential_type(credential_type)
            entry = cls.update_service_account_settings(
                id=id, namespace=namespace, credential_type=credential_type)
        return entry

    @classmethod
    def get_all_default_settings(
            cls, namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """Returns a list of the default settings objects for each type"""
        all_settings = []
        for credential_type in GoogleServiceAccountTypes.to_dict().values():
            entity = cls.get_default_settings_by_type(
                credential_type,
                namespace)
            if entity:
                all_settings.append(entity)
        return all_settings

    @classmethod
    def update_default_settings_by_type(
            cls, namespace=appengine_config.DEFAULT_NAMESPACE_NAME,
            credential_type=None, **kwargs):
        """
        Updates the default settings object identified by type.
        Each type will have exactly one default object.
        """
        id = cls._default_id_from_credential_type(credential_type)
        kwargs['id'] = id
        kwargs['credential_type'] = credential_type
        return cls.update_service_account_settings(
            namespace=namespace, **kwargs)

    @classmethod
    def _store_credentials_in_memcache(
            cls, credentials,
            namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """Stores the credential object in memcache"""
        memcache.set(
            cls._MEMCACHE_KEY, credentials, time=cls._DEFAULT_CACHE_TTL_SECS,
            namespace=namespace)

    @classmethod
    def _get_credentials_from_memcache(
            cls, namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """Gets the credentials from the memcache"""
        return memcache.get(cls._MEMCACHE_KEY, namespace=namespace)

    @classmethod
    def get_credentials(cls, namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        credentials = cls._get_credentials_from_memcache(namespace)
        if not credentials:
            # Try initializing again
            credentials = cls.initialize_credentials(namespace=namespace)
        return credentials

    @classmethod
    def initialize_credentials(cls, service_account_settings=None,
            namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """Builds a decorator for using oauth2 with webapp2.RequestHandlers."""
        # In real life we'd want to make one decorator per service because
        # we wouldn't want users to have to give so many permissions.

        # Initialize more credentials here if required
        try:
            if not service_account_settings:
                service_account_settings = cls.get_default_settings_by_type(
                        GoogleServiceAccountTypes.SERVICE_ACCOUNT,
                        namespace=namespace)

            if not service_account_settings:
                raise ValueError(
                    'Default service_account Settings not found')

            key = service_account_settings.private_key
            scope = service_account_settings.scope
            client_email = service_account_settings.client_email
            sub_user_email = service_account_settings.sub_user_email

            if key and scope and client_email:
                if sub_user_email:
                    credentials = SignedJwtAssertionCredentials(
                        client_email, key, scope=scope, sub=sub_user_email)
                else:
                    credentials = SignedJwtAssertionCredentials(
                        client_email, key, scope=scope)
                if credentials:
                    cls._store_credentials_in_memcache(
                        credentials, namespace=namespace)
                    # Reset all services
                    cls._SERVICES = {}
                    return credentials
                else:
                    raise ValueError('Could not create credentials')
            else:
                raise ValueError('Invalid default service_account settings')

        # Deliberately catch everything. pylint: disable-msg=broad-except
        except Exception as e:
            logging.error('Could not initialize Google service account '
                          'credentials.\nError: %s', e)
            return None

    @classmethod
    def _get_authorized_http_object(cls, http_obj=None,
            timeout=DEFAULT_HTTP_TIMEOUT,
            namespace=appengine_config.DEFAULT_NAMESPACE_NAME,
            *args, **kwargs):
        """Calls the authorize function of credentials"""
        if not http_obj:
            http_obj = httplib2.Http(timeout=timeout)
        credentials = cls.get_credentials()
        if not credentials:
            return None
        return credentials.authorize(
            http_obj, *args, **kwargs)

    @classmethod
    def _add_service(cls, name, version, service,
            namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """Adds a service to _SERVICES"""
        if namespace not in cls._SERVICES:
            cls._SERVICES[namespace] = {}
        if name not in cls._SERVICES[namespace]:
            cls._SERVICES[namespace][name] = {}
        cls._SERVICES[namespace][name][version] = {
            'name': name,
            'version': version,
            'service': service
        }
        return service

    @classmethod
    def _create_service(cls, name, version, http_obj=None,
            timeout=DEFAULT_HTTP_TIMEOUT,
            namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """Creates and adds a service"""

        if None in (name, version):
            return None

        if http_obj is None:
            http_obj = cls._get_authorized_http_object(
                timeout=timeout,
                namespace=namespace)
            if not http_obj:
                return None

        try:
            service = build(name, version, http=http_obj)
            cls._add_service(name, version, service, namespace)
            return service
        except Exception as e:
            logging.error('Unable to initialize %s service: %s',
                          name, e)
            return None

    @classmethod
    def get_service(cls, name=None, version=None, http_obj=None,
            timeout=DEFAULT_HTTP_TIMEOUT,
            namespace=appengine_config.DEFAULT_NAMESPACE_NAME):
        """
        Returns the service from _SERVICES

        Note: run this function every time you need to use a service to avoid
        using stale services.
        """
        if namespace in cls._SERVICES:
            if name in cls._SERVICES[namespace]:
                if version in cls._SERVICES[namespace][name]:
                    service = cls._SERVICES[namespace][name][version].get(
                        'service')
                    if service:
                        return service

        # If we reach here it means service doesn't exist. Create a new service
        return cls._create_service(
            name, version, http_obj, timeout, namespace)
