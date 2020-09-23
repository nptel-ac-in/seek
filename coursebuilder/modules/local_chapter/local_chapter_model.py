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


import appengine_config

from common.utils import Namespace
from models import models

from google.appengine.ext import ndb


class LocalChapter(ndb.Model):
    """Local Chapters"""

    name = ndb.StringProperty(indexed=False)
    city = ndb.StringProperty(indexed=False)
    state = ndb.StringProperty(indexed=False)

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
        if local_chapter:
            self.code = local_chapter.code
            self.name = local_chapter.name
            self.city = local_chapter.city
            self.state = local_chapter.state


class LocalChapterDAO(object):
    """All access and mutation methods for LocalChapter."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME
    list_memcache_key =  'all_local_chapter_list'

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
    @ndb.transactional()
    def add_new_local_chapter(cls, key, name, city, state, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            if cls.get_local_chapter_by_key(key):
                errors.append(
                    'Unable to add new LocalChapter. Entry with the '
                    'same key \'%s\' already exists.' % key)
                return
            chapter = LocalChapter(id=key, name=name, city=city, state=state)
            chapter_key = chapter.put()
            models.MemcacheManager.delete(cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)
            return chapter_key

    @classmethod
    def update_local_chapter(cls, key, name, city, state, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = LocalChapter.get_by_id(key)
            if not c:
                errors.append(
                   'Unable to find local chapter %s.' % key)
                return
            if name is not None:
                c.name = name
                c.city = city
                c.state = state
            c.put()
            models.MemcacheManager.delete(cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)


    @classmethod
    def delete_local_chapter(cls, key, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = LocalChapter.get_by_id(key)
            if not c:
                errors.append(
                   'Unable to find Local Chapter %s.' % key)
                return
            c.key.delete()
            models.MemcacheManager.delete(cls.list_memcache_key, namespace=cls.TARGET_NAMESPACE)
