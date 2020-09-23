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

"""Manage  Queue Email settings."""

__author__ = 'Thejesh GN (tgn@google.com)'


import appengine_config

from common.utils import Namespace
from models import models

from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

APP_ENGINE_EMAIL = 'APP_ENGINE_EMAIL'
SEND_GRID = 'SEND_GRID'

class EmailSettings(ndb.Model):
    provider = ndb.StringProperty(choices=[APP_ENGINE_EMAIL, SEND_GRID,],
        default=APP_ENGINE_EMAIL)
    from_email = ndb.StringProperty()
    api_key = ndb.StringProperty()

    @property
    def unique_name(self):
        return self.key.id()


class EmailSettingsDTO(object):
    """DTO for EmailSettings."""

    def __init__(self, email_settings=None):
        self.unique_name = None
        self.provider = None
        self.from_email = None
        self.api_key = None
        if email_settings:
            self.unique_name = email_settings.unique_name
            self.provider = email_settings.provider
            self.from_email = email_settings.from_email
            self.api_key = email_settings.api_key


class EmailSettingsDAO(object):
    """All access and mutation methods for EmailSettings."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME
    list_memcache_key =  'all_email_settings_list'

    @classmethod
    def get_email_settings_list(cls):
        with Namespace(cls.TARGET_NAMESPACE):
            email_settings_list = models.MemcacheManager.get(cls.list_memcache_key,
                                                namespace=cls.TARGET_NAMESPACE)
            if email_settings_list is not None:
                return email_settings_list

            email_settings = []
            for settings in EmailSettings.query().iter():
                email_settings.append(EmailSettingsDTO(settings))

            models.MemcacheManager.set(cls.list_memcache_key, email_settings,
                                                namespace=cls.TARGET_NAMESPACE)
            return email_settings



    @classmethod
    def get_email_settings_by_key(cls, key):
        with Namespace(cls.TARGET_NAMESPACE):
            c = EmailSettings.get_by_id(key)
            if c:
                return EmailSettingsDTO(c)
            else:
                return None

    @classmethod
    @ndb.transactional()
    def add_new_email_settings(cls, unique_name, provider, from_email,
                            api_key, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            if cls.get_email_settings_by_key(unique_name):
                errors.append(
                    'Unable to add new EmailSettings. Entry with the '
                    'same key \'%s\' already exists.' % queue)
                return
            settings = EmailSettings(id=unique_name, provider=provider,
                from_email=from_email, api_key=api_key)
            settings = settings.put()
            models.MemcacheManager.delete(cls.list_memcache_key,
                namespace=cls.TARGET_NAMESPACE)
            return unique_name

    @classmethod
    def update_email_settings(cls, unique_name, provider, from_email,
                                                            api_key, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = EmailSettings.get_by_id(unique_name)
            if not c:
                errors.append(
                   'Unable to find EmailSettings %s.' % queue)
                return
            if c is not None:
                c.provider = provider
                c.from_email = from_email
                c.api_key = api_key

            c.put()
            models.MemcacheManager.delete(cls.list_memcache_key,
                                                namespace=cls.TARGET_NAMESPACE)


    @classmethod
    def delete_email_settings(cls, key, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = EmailSettings.get_by_id(key)
            if not c:
                errors.append(
                   'Unable to find EmailSettings %s.' % queue)
                return
            c.key.delete()
            models.MemcacheManager.delete(cls.list_memcache_key,
                                                namespace=cls.TARGET_NAMESPACE)



class QueueSettings(ndb.Model):
    """Email Settings"""
    email_settings = ndb.KeyProperty(kind=EmailSettings)

    @property
    def queue_id(self):
        return self.key.id()


class QueueSettingsDTO(object):
    """DTO for QueueSettings."""

    def __init__(self, queue=None):
        self.queue_id = None
        self.email_settings = None
        if queue:
            self.queue_id = queue.queue_id
            self.email_settings = EmailSettingsDAO.get_email_settings_by_key(queue.email_settings.id())


class QueueSettingsDAO(object):
    """All access and mutation methods for EmailSettings."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME
    list_memcache_key =  'all_queue_settings_list'

    @classmethod
    def get_queue_settings_list(cls):
        with Namespace(cls.TARGET_NAMESPACE):
            queue_settings_list = models.MemcacheManager.get(cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)
            if queue_settings_list is not None:
                return queue_settings_list

            queue_settings = []
            for settings in QueueSettings.query().iter():
                queue_settings.append(QueueSettingsDTO(settings))

            models.MemcacheManager.set(cls.list_memcache_key, queue_settings, namespace=cls.TARGET_NAMESPACE)
            return queue_settings

    @classmethod
    def get_queue_settings_by_email_settings(cls, email_settings_key):
        with Namespace(cls.TARGET_NAMESPACE):
            email_settings = EmailSettings.get_by_id(email_settings_key)
            query = QueueSettings.query().filter(QueueSettings.email_settings==email_settings.key)
            c = query.get()
            if c:
                return QueueSettingsDTO(c)
            else:
                return None

    @classmethod
    def get_queue_settings_by_key(cls, key):
        with Namespace(cls.TARGET_NAMESPACE):
            c = QueueSettings.get_by_id(key)
            if c:
                return QueueSettingsDTO(c)
            else:
                return None

    @classmethod
    @ndb.transactional()
    def add_new_queue_settings(cls, queue_id, email_settings, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            if cls.get_queue_settings_by_key(queue_id):
                errors.append(
                    'Unable to add new QueueSettings. Entry with the '
                    'same key \'%s\' already exists.' % queue)
                return
            settings = QueueSettings(id=queue_id,email_settings=email_settings)
            settings = settings.put()
            models.MemcacheManager.delete(cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)

    @classmethod
    def update_queue_settings(cls, queue_id, email_settings, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = QueueSettings.get_by_id(queue_id)
            if not c:
                errors.append(
                   'Unable to find QueueSettings %s.' % queue)
                return
            if email_settings is not None:
                c.email_settings = email_settings

            c.put()
            models.MemcacheManager.delete(cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)


    @classmethod
    def delete_queue_settings(cls, queue_id, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = QueueSettings.get_by_id(queue_id)
            if not c:
                errors.append(
                   'Unable to find QueueSettings %s.' % queue)
                return
            c.key.delete()
            models.MemcacheManager.delete(cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)
