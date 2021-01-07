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

"""Manage local chapters."""

__author__ = 'Thejesh GN (tgn@google.com)'

from google.appengine.ext import ndb

import appengine_config

from common.utils import Namespace
from models import models
from modules.spoc import roles as spoc_roles
from modules.local_chapter import base

class LocalChapter(ndb.Model):
    """Local Chapters"""

    name = ndb.StringProperty(indexed=True)
    city = ndb.StringProperty(indexed=False)
    state = ndb.StringProperty(indexed=False)
    org_type = ndb.StringProperty(indexed=True, default="college")
    spoc_emails = ndb.StringProperty(indexed=True, repeated=True)

    @property
    def code(self):
        return self.key.id()



class LocalChapterDTO(object):
    """DTO for LocalChapter."""

    def __init__(self, local_chapter=None):
        self.code = None
        self.name = None
        self.city = None
        self.state = None
        self.org_type = "college"
        self.spoc_emails = list()
        if local_chapter:
            self.code = local_chapter.code
            self.name = local_chapter.name
            self.city = local_chapter.city
            self.state = local_chapter.state
            self.org_type = local_chapter.org_type
            self.spoc_emails = local_chapter.spoc_emails


class LocalChapterDAO(object):
    """All access and mutation methods for LocalChapter."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME
    list_memcache_key =  'local_chapter_list_all'


    @classmethod
    def _memcache_key_for_org(cls, org_type):
        """Makes a memcache key from org_type."""
        return 'local_chapter_list:%s' % org_type


    @classmethod
    def get_local_chapter_list_for_org(cls, org_type):
        org_memcache_key = cls._memcache_key_for_org(org_type)
        with Namespace(cls.TARGET_NAMESPACE):
            local_chapters_list = models.MemcacheManager.get(org_memcache_key, namespace=cls.TARGET_NAMESPACE)
            if local_chapters_list is not None:
                return local_chapters_list
            local_chapters = []

            #this is to handle default values for college
            query_iterator = None
            if org_type == base.LocalChapterBase.LOCAL_CHAPTER_ORG_COLLEGE:
                query_iterator = LocalChapter.query().filter(LocalChapter.org_type.IN([org_type.lower(),"", None])).iter()
            else:
                query_iterator = LocalChapter.query().filter(LocalChapter.org_type == org_type.lower()).iter()

            for chapter in query_iterator:
                local_chapters.append(LocalChapterDTO(chapter))
            local_chapters = sorted(local_chapters, key=lambda chapter: chapter.code)

            models.MemcacheManager.set(org_memcache_key, local_chapters, namespace=cls.TARGET_NAMESPACE)
            return local_chapters

    @classmethod
    def get_local_chapter_list(cls):
        with Namespace(cls.TARGET_NAMESPACE):
            local_chapters_list = models.MemcacheManager.get(cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)
            if local_chapters_list is not None:
                return local_chapters_list

            local_chapters = []
            for chapter in LocalChapter.query().iter():
                local_chapters.append(LocalChapterDTO(chapter))
            local_chapters = sorted(local_chapters, key=lambda chapter: chapter.code)

            models.MemcacheManager.set(cls.list_memcache_key, local_chapters, namespace=cls.TARGET_NAMESPACE)
            return local_chapters





    @classmethod
    def get_local_chapter_by_key(cls, key):
        with Namespace(cls.TARGET_NAMESPACE):
            c = LocalChapter.get_by_id(key)
            if c:
                return LocalChapterDTO(c)
            else:
                return None

    @classmethod
    def get_local_chapter_by_name(cls, name):
        with Namespace(cls.TARGET_NAMESPACE):
            c = LocalChapter.query(LocalChapter.name == name).get()
            if c:
                return LocalChapterDTO(c)
            else:
                return None


    @classmethod
    def get_local_chapter_for_spoc_email(cls, spoc_email):
        with Namespace(cls.TARGET_NAMESPACE):
            return LocalChapter.query(
                LocalChapter.spoc_emails == spoc_email.lower()).get()

    @classmethod
    def _update_local_chapter(cls, c, name, city, state, org_type, spoc_emails, errors):
        c.name = name
        c.city = city
        c.state = state
        c.org_type = org_type

        if c.spoc_emails is None:
            c.spoc_emails = list()
        if spoc_emails is None:
            spoc_emails = list()

        c.emails = [e.lower() for e in c.spoc_emails]
        spoc_emails = [e.lower() for e in spoc_emails]

        new_emails = set(spoc_emails)
        old_emails = set(c.spoc_emails)
        emails_to_be_added = new_emails - old_emails
        emails_to_be_removed = old_emails - new_emails

        # Refine the emails to be added, removing any existing SPOCs.
        for email in list(emails_to_be_added):
            local_chapter = cls.get_local_chapter_for_spoc_email(email)
            if local_chapter:
                errors.append('Email %s already present in another '
                              'Local chapter' % email)
                emails_to_be_added.remove(email)
                spoc_emails.remove(email)


        spoc_roles.SPOCRoleManager.add_spoc_emails_in_role(
            emails_to_be_added)
        spoc_roles.SPOCRoleManager.remove_spoc_emails_from_role(
            emails_to_be_removed)
        c.spoc_emails = spoc_emails
        key = c.put()

        #clear cache
        models.MemcacheManager.delete(
            cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)
        models.MemcacheManager.delete(
            cls._memcache_key_for_org(base.LocalChapterBase.LOCAL_CHAPTER_ORG_COLLEGE), namespace=cls.TARGET_NAMESPACE)
        models.MemcacheManager.delete(
            cls._memcache_key_for_org(base.LocalChapterBase.LOCAL_CHAPTER_ORG_INDUSTRY), namespace=cls.TARGET_NAMESPACE)

        return key

    @classmethod
    def add_new_local_chapter(cls, key, name, city, state, org_type, spoc_emails, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            if cls.get_local_chapter_by_key(key):
                errors.append(
                    'Unable to add new LocalChapter. Entry with the '
                    'same key \'%s\' already exists.' % key)
                return
            chapter = LocalChapter(id=key, name=name, city=city, state=state, org_type=org_type)
            return cls._update_local_chapter(chapter, name, city, state, org_type, spoc_emails, errors)

    @classmethod
    def update_local_chapter(cls, key, name, city, state, org_type, spoc_emails, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = LocalChapter.get_by_id(key)
            if not c:
                errors.append(
                   'Unable to find local chapter %s.' % key)
                return
            return cls._update_local_chapter(c, name, city, state, org_type, spoc_emails, errors)

    @classmethod
    def delete_local_chapter(cls, key, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = LocalChapter.get_by_id(key)
            if not c:
                errors.append(
                   'Unable to find Local Chapter %s.' % key)
                return
            spoc_roles.SPOCRoleManager.remove_spoc_emails_from_role(
                c.spoc_emails)
            c.key.delete()
            models.MemcacheManager.delete(
                cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)
            models.MemcacheManager.delete(
                cls._memcache_key_for_org(base.LocalChapterBase.LOCAL_CHAPTER_ORG_COLLEGE), namespace=cls.TARGET_NAMESPACE)
            models.MemcacheManager.delete(
                cls._memcache_key_for_org(base.LocalChapterBase.LOCAL_CHAPTER_ORG_INDUSTRY), namespace=cls.TARGET_NAMESPACE)
