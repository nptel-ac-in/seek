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

"""Manage all the list of courses."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


import appengine_config

import logging
from common.utils import Namespace
import models
import entities
import transforms
import vfs
import yaml

from google.appengine.api import memcache
from google.appengine.api import namespace_manager
from google.appengine.ext import db


class CourseList(entities.BaseEntity):
    """Personal information not specific to any course instance."""

    slug = db.StringProperty(indexed=True)
    filesystem_path = db.StringProperty(indexed=True)

    should_list = db.BooleanProperty(indexed=True, default=True)
    visible = db.BooleanProperty(indexed=True, default=False)
    can_register = db.BooleanProperty(indexed=True, default=False)
    registration = db.StringProperty(
        indexed=False,
        choices=['NOT_OPEN', 'OPENING_SHORTLY', 'OPEN', 'CLOSED'],
        default='OPENING_SHORTLY')
    allowlist = db.TextProperty(indexed=False, default=None)
    browsable = db.BooleanProperty(indexed=False, default=True)
    closed = db.BooleanProperty(indexed=False, default=False)
    featured = db.BooleanProperty(indexed=False, default=False)


    title = db.StringProperty(indexed=False)
    blurb = db.TextProperty(indexed=False)

    category = db.StringProperty(indexed=True)
    tags = db.StringListProperty(indexed=True, default=[])
    course_admin_email = db.TextProperty(indexed=False, default=None)
    last_announcement = db.DateTimeProperty(indexed=False, default=None)

    @property
    def namespace(self):
        return self.key().name()

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        return db_key


class CourseListDTO(object):
    """DTO for CourseList."""

    def __init__(self, course=None):
        self.namespace = None
        self.slug = None
        self.filesystem_path = None
        self.should_list = None
        self.visible = False
        self.can_register = False
        self.registration = False
        self.allowlist = ''
        self.browsable = True
        self.title = None
        self.blurb = None
        self.category = None
        self.closed = False
        self.tags = []
        self.course_admin_email = ''
        self.featured = False
        self.last_announcement = None
        if course:
            self.namespace = course.namespace
            self.slug = course.slug
            self.filesystem_path = course.filesystem_path
            self.should_list = course.should_list
            self.visible = course.visible
            self.can_register = course.can_register
            self.registration = course.registration
            self.allowlist = course.allowlist
            self.browsable = course.browsable
            self.title = course.title
            self.blurb = course.blurb
            self.category = course.category
            self.closed = course.closed
            self.tags = course.tags
            self.course_admin_email = course.course_admin_email
            self.featured = course.featured
            self.last_announcement = course.last_announcement


class CourseListDAO(object):
    """All access and mutation methods for CourseList."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:course-list:%s' % key

    @classmethod
    def get_course_list(cls):
        with Namespace(cls.TARGET_NAMESPACE):
            return CourseList.all().order('-%s' % CourseList.slug.name).run(batch_size=1000)

    @classmethod
    def get_course_for_path(cls, path):
        memcache_key = cls._memcache_key(path)
        value = memcache.get(memcache_key, namespace=cls.TARGET_NAMESPACE)
        if value:
            return CourseListDTO(value)
        with Namespace(cls.TARGET_NAMESPACE):
            courses = CourseList.all().filter(CourseList.slug.name, path).fetch(limit=2)
            if len(courses) == 2:
              raise Exception(
                  'There is more than one course with path %s' % path)
            if not courses:
                return None
            value = courses[0]
	    memcache.set(memcache_key, value, models.DEFAULT_CACHE_TTL_SECS,
                         namespace=cls.TARGET_NAMESPACE)
            return CourseListDTO(value)

    @classmethod
    def get_course_for_namespace(cls, namespace):
        with Namespace(cls.TARGET_NAMESPACE):
            c = CourseList.get_by_key_name(namespace)
            if c:
                return CourseListDTO(c)
            else:
                return None

    @classmethod
    @db.transactional()
    def add_new_course(cls, namespace, path, title, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            if cls.get_course_for_namespace(namespace):
                errors.append(
                    'Unable to add new entry. Entry with the '
                    'same name \'%s\' already exists.' % namespace)
                return
            cli = CourseList(key_name=namespace)
            cli.slug = path
            cli.title = title
            cli.put()
            memcache_key = cls._memcache_key(path)
	    memcache.delete(memcache_key, namespace=cls.TARGET_NAMESPACE)


    @classmethod
    def update_course_details(
        cls, namespace, slug=None, filesystem_path=None, should_list=None,
        visible=None, can_register=None, registration=None, allowlist=None,
	browsable=None, title=None, blurb=None, category=None, closed=None,
        tags=None, course_admin_email=None, featured = None,last_announcement=None):
        with Namespace(cls.TARGET_NAMESPACE):
            c = CourseList.get_by_key_name(namespace)
            if not c:
                return
            memcache_key = cls._memcache_key(c.slug)
	    memcache.delete(memcache_key, namespace=cls.TARGET_NAMESPACE)

            if slug is not None:
                c.slug = slug
            if filesystem_path is not None:
                c.filesystem_path = filesystem_path
            if should_list is not None:
                c.should_list = should_list
            if visible is not None:
                c.visible = visible
            if can_register is not None:
                c.can_register = can_register
            if registration is not None:
                c.registration = registration
            if allowlist is not None:
                c.allowlist = allowlist
            if browsable is not None:
                c.browsable = browsable
            if title is not None:
                c.title = title
            if blurb is not None:
                c.blurb = blurb
            if category is not None:
                c.category = category
            if closed is not None:
                c.closed = closed
            if tags is not None:
                c.tags = tags
            if course_admin_email is not None:
                c.course_admin_email = course_admin_email
            if featured is not None:
                c.featured = featured
            if last_announcement is not None:
                c.last_announcement=last_announcement
            c.put()


class CourseListConnector(object):
    """Tool to connect course list to course settings"""
    DEFAULT_MAPPING = {
        'course': {
            'title': CourseList.title.name,
            'browsable': CourseList.browsable.name,
            'now_available': CourseList.visible.name},
        'reg_form': {
            'can_register': CourseList.can_register.name,
            'allowlist': CourseList.allowlist.name,
         }
    }

    @classmethod
    def validate_settings_content(self, content):
        yaml.safe_load(content)

    @classmethod
    def save_settings(cls, course, course_settings):
        if 'reg_form' in course_settings:
             if 'registration' in course_settings['reg_form']:
                 course_settings['reg_form']['can_register'] = (
                     course_settings['reg_form']['registration'] == 'OPEN')

        content = yaml.safe_dump(course_settings)
        try:
            cls.validate_settings_content(content)
        except yaml.YAMLError as e:  # pylint: disable=W0703
            logging.error('Failed to validate course settings: %s.', str(e))
            return False
 
        content_stream = vfs.string_to_stream(unicode(content))
        # Store settings.
        course.set_file_content('/course.yaml', content_stream)

        course_item = course_settings['course']
        reg_item = dict()
        if 'reg_form' in course_settings:
            reg_item = course_settings['reg_form']
        explorer_item = dict()
        if 'explorer' in course_settings:
            explorer_item = course_settings['explorer']

        CourseListDAO.update_course_details(
            namespace_manager.get_namespace(),
            title=course_item.get('title'),
            browsable=course_item.get('browsable'),
            visible=course_item.get('now_available'),
            allowlist=course_item.get('allowlist'),
            can_register=reg_item.get('can_register'),
            registration=reg_item.get('registration'),
            blurb=explorer_item.get('blurb'),
            should_list=explorer_item.get('list_in_explorer'),
            closed=explorer_item.get('closed', False),
            course_admin_email=course_item.get('admin_user_emails')
            )
        course.invalidate_cached_course_settings()
        return True
