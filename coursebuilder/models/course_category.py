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

"""Manage course categories."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


import appengine_config

from common.utils import Namespace
import models
import entities

from google.appengine.ext import db


class CourseCategory(entities.BaseEntity):
    """Course categories."""

    description = db.StringProperty(indexed=False)
    visible = db.BooleanProperty(indexed=True, default=False)

    @property
    def category(self):
        return self.key().name()


class CourseCategoryDTO(object):
    """DTO for CourseCategory."""

    def __init__(self, category=None):
        self.category = None
        self.description = None
        if category:
            self.category = category.category
            self.description = category.description
            self.visible = category.visible


class CourseCategoryDAO(object):
    """All access and mutation methods for CourseCategory."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME
    category_list_memcache_key = 'course-category-list-all'
    category_list_visible_memcache_key = 'course-category-list-visible-only'

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:course-category:%s' % key


    @classmethod
    def _convert_to_dto_list(cls, categories):
        category_list = []
        for category in categories:
            category_list.append(CourseCategoryDTO(category))
        return category_list


    @classmethod
    def get_category_list(cls, visible_only=False):
        with Namespace(cls.TARGET_NAMESPACE):
            if visible_only:
                category_list = models.MemcacheManager.get(cls.category_list_visible_memcache_key, 
                                namespace=cls.TARGET_NAMESPACE)                
            else:
                category_list = models.MemcacheManager.get(cls.category_list_memcache_key, 
                                namespace=cls.TARGET_NAMESPACE)
            if category_list:
                return cls._convert_to_dto_list(category_list)
                
            category_list = [] 
            query = db.Query(CourseCategory)
            if visible_only:
                query.filter('visible =', True)                
 
 
            for category in query:
                category_list.append(category)
            
            if visible_only:
                models.MemcacheManager.set(cls.category_list_visible_memcache_key, category_list, 
                    namespace=cls.TARGET_NAMESPACE)
            else:
                models.MemcacheManager.set(cls.category_list_memcache_key, category_list, 
                    namespace=cls.TARGET_NAMESPACE)    

            return cls._convert_to_dto_list(category_list)

    @classmethod
    def get_category_by_key(cls, key):
        with Namespace(cls.TARGET_NAMESPACE):
            c = models.MemcacheManager.get(
                cls._memcache_key(key), namespace=cls.TARGET_NAMESPACE)
            if c:
                return CourseCategoryDTO(c)

            c = CourseCategory.get_by_key_name(key)
            if c:
                models.MemcacheManager.set(
		    cls._memcache_key(key), c, namespace=cls.TARGET_NAMESPACE)
                return CourseCategoryDTO(c)
            else:
                return None

    @classmethod
    @db.transactional()
    def add_new_category(cls, key, description, visible, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            if cls.get_category_by_key(key):
                errors.append(
                    'Unable to add new category. Entry with the '
                    'same key \'%s\' already exists.' % key)
                return
            cli = CourseCategory(key_name=key)
            cli.description = description
            cli.visible = visible
            cli.put()
            models.MemcacheManager.set(
	        cls._memcache_key(key), cli, namespace=cls.TARGET_NAMESPACE)
            models.MemcacheManager.delete(cls.category_list_memcache_key, namespace=cls.TARGET_NAMESPACE)
            models.MemcacheManager.delete(cls.category_list_visible_memcache_key , namespace=cls.TARGET_NAMESPACE)


    @classmethod
    def update_category(cls, key, description, visible, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = CourseCategory.get_by_key_name(key)
            if not c:
                errors.append(
                   'Unable to find category %s.' % key)
                return

            if description is not None:
                c.description = description
                c.visible = visible
            c.put()
            models.MemcacheManager.set(
	        cls._memcache_key(key), c, namespace=cls.TARGET_NAMESPACE)
            models.MemcacheManager.delete(cls.category_list_memcache_key, namespace=cls.TARGET_NAMESPACE)
            models.MemcacheManager.delete(cls.category_list_visible_memcache_key , namespace=cls.TARGET_NAMESPACE)


    @classmethod
    def delete_category(cls, key, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            c = CourseCategory.get_by_key_name(key)
            if not c:
                errors.append(
                   'Unable to find category %s.' % key)
                return

            c.delete()
            models.MemcacheManager.delete(
	        cls._memcache_key(key),  namespace=cls.TARGET_NAMESPACE)
            models.MemcacheManager.delete(cls.category_list_memcache_key, namespace=cls.TARGET_NAMESPACE)
            models.MemcacheManager.delete(cls.category_list_visible_memcache_key , namespace=cls.TARGET_NAMESPACE)

