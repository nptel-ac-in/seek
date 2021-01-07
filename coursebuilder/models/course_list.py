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
import math
from common import utils
from common import utc
from common.utils import Namespace
import models
import entities
import transforms
import vfs
import yaml

from google.appengine.api import memcache
from google.appengine.api import namespace_manager
from google.appengine.ext import ndb

from modules.courses.constants import  COURSE_AVAILABILITY_PRIVATE
from modules.courses.constants import  COURSE_AVAILABILITY_REGISTRATION_REQUIRED
from modules.courses.constants import  COURSE_AVAILABILITY_REGISTRATION_OPTIONAL
from modules.courses.constants import  COURSE_AVAILABILITY_REGISTRATION_CLOSED
from modules.courses.constants import  COURSE_AVAILABILITY_PUBLIC
from modules.courses.constants import  COURSE_AVAILABILITY_POLICIES

class CourseList(ndb.Model):
    """Personal information not specific to any course instance."""

    slug = ndb.StringProperty(indexed=True)
    filesystem_path = ndb.StringProperty(indexed=True)

    should_list = ndb.BooleanProperty(indexed=True, default=True) # depreciated
    show_in_explorer = ndb.BooleanProperty(indexed=True, default=True)
    visible = ndb.BooleanProperty(indexed=True, default=False)
    availability_ = ndb.StringProperty(indexed=True)
    can_register = ndb.BooleanProperty(indexed=True, default=False)
    registration = ndb.StringProperty(
        indexed=False,
        choices=['NOT_OPEN', 'OPENING_SHORTLY', 'OPEN', 'CLOSED'],
        default='OPENING_SHORTLY')
    whitelist = ndb.TextProperty(indexed=False, default=None)
    browsable = ndb.BooleanProperty(indexed=False, default=False)
    closed = ndb.BooleanProperty(indexed=True, default=False)
    featured = ndb.BooleanProperty(indexed=False, default=False)


    title = ndb.StringProperty(indexed=False)
    blurb = ndb.TextProperty(indexed=False)
    instructor_details = ndb.TextProperty(indexed=False)
    explorer_summary = ndb.TextProperty(indexed=False)
    explorer_instructor_name = ndb.TextProperty(indexed=False)
    locale = ndb.StringProperty(indexed=False)

    category = ndb.StringProperty(indexed=True)
    tags = ndb.StringProperty(indexed=True, repeated=True)
    estimated_workload = ndb.StringProperty(indexed=False)
    course_admin_email = ndb.TextProperty(indexed=True, repeated=True)
    last_announcement = ndb.DateTimeProperty(indexed=False, default=None)
    admin_email = ndb.TextProperty(indexed=False, default=None)
    permissions = ndb.TextProperty(indexed=False)

    start_date = ndb.StringProperty(indexed=False)
    end_date = ndb.StringProperty(indexed=False)
    spoc_mentor = ndb.BooleanProperty(indexed=False, default=False)


    @property
    def namespace(self):
        return self.key.string_id()

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        return db_key

    @property
    def now_available(self):
        return self.visible

    @now_available.setter
    def now_available(self, val):
        self.visible = self.now_available

    @property
    def availability(self):
        for name, setting in COURSE_AVAILABILITY_POLICIES.iteritems():
            if (self.can_register == setting['can_register']
                and self.now_available == setting['now_available']
                and self.browsable == setting['browsable']):
                return name


    @availability.setter
    def availability(self, val):
        settings = COURSE_AVAILABILITY_POLICIES[val]

        self.can_register = setting['can_register']
        self.now_available = setting['now_available']
        self.browsable = setting['browsable']

        if val == 'private':
            self.visible = False
        else:
            self.visible = True


class CourseListDTO(object):
    """DTO for CourseList."""

    def __init__(self, course=None):
        self.namespace = None
        self.slug = None
        self.filesystem_path = None
        self.should_list = None
        self.show_in_explorer = None
        self.visible = False
        self.can_register = False
        self.registration = False
        self.whitelist = ''
        self.browsable = False
        self.title = None
        self.blurb = None
        self.instructor_details = None
        self.explorer_summary = None
        self.explorer_instructor_name = None
        self.category = None
        self.closed = False
        self.tags = []
        self.estimated_workload = None
        self.course_admin_email = []
        self.featured = False
        self.permissions = '{}'
        self.locale = ''
        self.last_announcement = None
        self.start_date = None
        self.end_date = None
        self.spoc_mentor = False
        self.availability = None

        if course:
            self.namespace = course.namespace
            self.slug = course.slug
            self.filesystem_path = course.filesystem_path
            self.should_list = course.should_list
            self.show_in_explorer = course.show_in_explorer
            self.visible = course.visible
            self.can_register = course.can_register
            self.registration = course.registration
            self.whitelist = course.whitelist
            self.browsable = course.browsable
            self.title = course.title
            self.blurb = course.blurb
            self.instructor_details = course.instructor_details
            self.explorer_summary = course.explorer_summary
            self.explorer_instructor_name = course.explorer_instructor_name
            self.category = course.category
            self.closed = course.closed
            self.tags = course.tags
            self.estimated_workload = course.estimated_workload
            self.course_admin_email = course.course_admin_email
            self.featured = course.featured
            self.permissions = course.permissions
            self.locale = course.locale
            self.last_announcement = course.last_announcement
            self.start_date = course.start_date
            self.end_date = course.end_date
            self.spoc_mentor = course.spoc_mentor
            self.availability = course.availability

    @property
    def now_available(self):
        return self.visible

    def get_title(self):
        return self.title

    def get_slug(self):
        return self.slug

    def get_namespace_name(self):
        return self.namespace


class CourseListDAO(object):
    """All access and mutation methods for CourseList."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME

    @classmethod
    def _memcache_key_for_path(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:course-list-path:%s' % key

    @classmethod
    def _memcache_key(cls, shard_number, include_closed=True):
        """Makes a memcache key from primary key."""
        if include_closed:
            return 'entity:course-list-keys-all-%s' % str(shard_number)
        return 'entity:course-list-keys-not-closed-%s' % str(shard_number)


    @classmethod
    def _convert_to_dto_list(cls, courses):
        course_list = []
        for course in courses:
            course_list.append(CourseListDTO(course))
        return course_list

    @classmethod
    def _memcache_delete_course_list(cls):
        memcache.delete(cls._memcache_key(1,include_closed=False),
                        namespace=cls.TARGET_NAMESPACE)
        memcache.delete(cls._memcache_key(2,include_closed=False),
                        namespace=cls.TARGET_NAMESPACE)

        memcache.delete(cls._memcache_key(1,include_closed=True),
                        namespace=cls.TARGET_NAMESPACE)
        memcache.delete(cls._memcache_key(2,include_closed=True),
                        namespace=cls.TARGET_NAMESPACE)



    @classmethod
    def get_course_list(cls, include_closed=True):
        memcache_key_1 = cls._memcache_key(1, include_closed=include_closed)
        memcache_key_2 = cls._memcache_key(2, include_closed=include_closed)
        with Namespace(cls.TARGET_NAMESPACE):
            course_list_1 = memcache.get(memcache_key_1, namespace=cls.TARGET_NAMESPACE)
            course_list_2 = memcache.get(memcache_key_2, namespace=cls.TARGET_NAMESPACE)
            if course_list_1 and course_list_2:
                return cls._convert_to_dto_list(course_list_1 + course_list_2)
            course_list = []
            with Namespace(cls.TARGET_NAMESPACE):
                if include_closed:
                    query = CourseList.query().order(-CourseList.slug).iter()
                else:
                    query = CourseList.query(CourseList.closed == False).order(
                        -CourseList.slug).iter()
                for course in query:
                    course_list.append(course)
            try:
                n = len(course_list)
                memcache.set(memcache_key_1,course_list[0:n/2],
                        models.DEFAULT_CACHE_TTL_SECS,namespace=cls.TARGET_NAMESPACE)
                memcache.set(memcache_key_2,course_list[n/2:n],
                    models.DEFAULT_CACHE_TTL_SECS,namespace=cls.TARGET_NAMESPACE)
            except ValueError as err:
                logging.error(err)
            return cls._convert_to_dto_list(course_list)

    @classmethod
    def get_course_for_path(cls, path):
        memcache_key_for_path = cls._memcache_key_for_path(path)
        value = memcache.get(memcache_key_for_path, namespace=cls.TARGET_NAMESPACE)
        if value:
            return CourseListDTO(value)
        with Namespace(cls.TARGET_NAMESPACE):
            courses = CourseList.query(CourseList.slug == path).fetch(limit=2)
            if len(courses) == 2:
              raise Exception(
                  'There is more than one course with path %s' % path)
            if not courses:
                return None
	    memcache.set(memcache_key_for_path, courses[0], models.DEFAULT_CACHE_TTL_SECS,
                         namespace=cls.TARGET_NAMESPACE)
            return CourseListDTO(courses[0])

    @classmethod
    def get_course_for_namespace(cls, namespace):
        with Namespace(cls.TARGET_NAMESPACE):
            c = CourseList.get_by_id(namespace)
            if c:
                return CourseListDTO(c)
            else:
                return None

	#TODO: Remove this once everything is migrated to similar method with course_admin_email
    @classmethod
    @ndb.transactional()
    def add_new_course(cls, namespace, path, title, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            if cls.get_course_for_namespace(namespace):
                errors.append(
                    'Unable to add new entry. Entry with the '
                    'same name \'%s\' already exists.' % namespace)
                return
            cli = CourseList(id=namespace)
            cli.slug = path
            cli.title = title
            cli.put()
            memcache_key_for_path = cls._memcache_key_for_path(path)
            memcache.delete(memcache_key_for_path, namespace=cls.TARGET_NAMESPACE)
            cls._memcache_delete_course_list()



    @classmethod
    @ndb.transactional()
    def delete_course(cls, namespace):
        with Namespace(cls.TARGET_NAMESPACE):
            c = CourseList.get_by_id(namespace)
            memcache_key_for_path = cls._memcache_key_for_path(c.slug)
            c.key.delete()
            memcache.delete(memcache_key_for_path, namespace=cls.TARGET_NAMESPACE)
            memcache.delete(cls._memcache_key(), namespace=cls.TARGET_NAMESPACE)

    @classmethod
    @ndb.transactional()
    def add_new_course(cls, namespace, path, title, course_admin_email, errors):
        with Namespace(cls.TARGET_NAMESPACE):
            if cls.get_course_for_namespace(namespace):
                errors.append(
                    'Unable to add new entry. Entry with the '
                    'same name \'%s\' already exists.' % namespace)
                return
            cli = CourseList(id=namespace)
            cli.slug = path
            cli.title = title
            cli.course_admin_email = course_admin_email
            cli.put()
            memcache_key_for_path = cls._memcache_key_for_path(path)
            memcache.delete(memcache_key_for_path, namespace=cls.TARGET_NAMESPACE)
            cls._memcache_delete_course_list()


    @classmethod
    def update_course_details(
        cls, namespace, slug=None, filesystem_path=None, should_list=None,
        show_in_explorer=None,
        visible=None, can_register=None, registration=None, whitelist=None,
        browsable=None, title=None, blurb=None, instructor_details=None,
        explorer_summary=None, explorer_instructor_name=None, category=None,
        closed=None, tags=None, estimated_workload=None,
        course_admin_email=None, featured=None, permissions=None, locale=None,
        last_announcement=None, start_date=None, end_date=None,
        spoc_mentor=None):

        with Namespace(cls.TARGET_NAMESPACE):
            c = CourseList.get_by_id(namespace)
            if not c:
                return

            if slug is not None:
                c.slug = slug
            if filesystem_path is not None:
                c.filesystem_path = filesystem_path
            if should_list is not None:
                c.should_list = should_list
            if show_in_explorer is not None:
                c.show_in_explorer = show_in_explorer
            if visible is not None:
                c.visible = visible
            if can_register is not None:
                c.can_register = can_register
            if registration is not None:
                c.registration = registration
            if whitelist is not None:
                c.whitelist = whitelist
            if browsable is not None:
                c.browsable = browsable
            if title is not None:
                c.title = title
            if blurb is not None:
                c.blurb = blurb
            if instructor_details is not None:
                c.instructor_details = instructor_details
            if explorer_summary is not None:
                c.explorer_summary = explorer_summary
            if explorer_instructor_name is not None:
                c.explorer_instructor_name = explorer_instructor_name
            if category is not None:
                c.category = category
            if closed is not None:
                c.closed = closed
            if tags is not None:
                c.tags = tags
            if estimated_workload is not None:
                c.estimated_workload = estimated_workload
            if course_admin_email is not None:
                c.course_admin_email = course_admin_email
            if featured is not None:
                c.featured = featured
            if permissions is not None:
                c.permissions = permissions
            if locale is not None:
                c.locale = locale
            if last_announcement is not None:
                c.last_announcement=last_announcement
            if start_date is not None:
                c.start_date=start_date
            if end_date is not None:
                c.end_date=end_date
            if spoc_mentor is not None:
                c.spoc_mentor = spoc_mentor

            memcache_key_for_path = cls._memcache_key_for_path(c.slug)
            memcache.delete(memcache_key_for_path, namespace=cls.TARGET_NAMESPACE)
            cls._memcache_delete_course_list()
            c.put()

    @classmethod
    def duration_in_weeks(cls, obj):
        try:
            if obj and obj.start_date and obj.end_date:
                d1 = utc.text_to_datetime(obj.start_date)
                d2 = utc.text_to_datetime(obj.end_date)
                delta = d2 - d1
                return '%02d Weeks' % math.ceil(delta.days/7.0)
        except ValueError:
            return ''


class CourseListDTOForExplorer(CourseListDTO):
    """DTO for a stripped down version of course list used in Explorer"""

    def __init__(self, course=None):
        self.namespace = None
        self.slug = None
        self.should_list = None
        self.show_in_explorer = None
        self.visible = False
        self.can_register = False
        self.whitelist = ''
        self.browsable = False
        self.title = None
        self.explorer_summary = None
        self.explorer_instructor_name = None
        self.category = None
        self.closed = False
        self.tags = []
        self.estimated_workload = None
        self.course_admin_email = []
        self.featured = False
        self.locale = ''
        self.start_date = None
        self.end_date = None
        self.availability = None
        self.permissions = '{}'

        if course:
            self.namespace = course.namespace
            self.slug = course.slug
            self.should_list = course.should_list
            self.show_in_explorer = course.show_in_explorer
            self.visible = course.visible
            self.can_register = course.can_register
            self.whitelist = course.whitelist
            self.browsable = course.browsable
            self.title = course.title
            self.explorer_summary = course.explorer_summary
            self.explorer_instructor_name = course.explorer_instructor_name
            self.category = course.category
            self.closed = course.closed
            self.tags = course.tags
            self.estimated_workload = course.estimated_workload
            self.course_admin_email = course.course_admin_email
            self.featured = course.featured
            self.locale = course.locale
            self.start_date = course.start_date
            self.end_date = course.end_date
            self.availability = course.availability
            self.permissions = course.permissions


class CourseListDAOForExplorer(CourseListDAO):

    @classmethod
    def _memcache_key(cls, include_closed=True):
        """Returns a memcache key"""
        if include_closed:
            return 'entity:explorer-course-list-keys-all'
        return 'entity:explorer-course-list-keys-not-closed'

    @classmethod
    def _memcache_delete_course_list(cls):
        memcache.delete(cls._memcache_key(include_closed=False))
        memcache.delete(cls._memcache_key(include_closed=True))

    @classmethod
    def _memcache_set_course_list(cls, course_list, include_closed=True):
        with Namespace(cls.TARGET_NAMESPACE):
            memcache.set(cls._memcache_key(include_closed), course_list,
                         models.DEFAULT_CACHE_TTL_SECS,
                         namespace=cls.TARGET_NAMESPACE)

    @classmethod
    def _get_course_list_from_datastore(cls, include_closed=True):
        with Namespace(cls.TARGET_NAMESPACE):
            if include_closed:
                query = CourseList.query().order(-CourseList.slug).iter()
            else:
                query = CourseList.query(CourseList.closed == False
                                         ).order(-CourseList.slug).iter()
            return [c for c in query]

    @classmethod
    def _convert_to_dto_list(cls, courses):
        return [CourseListDTOForExplorer(c) for c in courses if c]

    @classmethod
    def get_course_list(cls, include_closed=True):
        memcache_key = cls._memcache_key(include_closed=include_closed)

        with Namespace(cls.TARGET_NAMESPACE):
            explorer_course_list = memcache.get(memcache_key, namespace=cls.TARGET_NAMESPACE)
            if explorer_course_list:
                return explorer_course_list

            # This means course list is not saved in cache
            explorer_course_list = cls._convert_to_dto_list(
                cls._get_course_list_from_datastore(include_closed))
            cls._memcache_set_course_list(explorer_course_list,
                                          include_closed=include_closed)
            return explorer_course_list



class CourseListConnector(object):
    """Tool to connect course list to course settings"""

    @classmethod
    def validate_settings_content(self, content):
        yaml.safe_load(content)

    @classmethod
    def save_settings(cls, course, course_settings):
        # TGN: I dont think we use registration field anywhere.
        # Can register shouldnt be dependent on it
        # We have to check it
        # if 'reg_form' in course_settings:
        #      if 'registration' in course_settings['reg_form']:
        #          course_settings['reg_form']['can_register'] = (
        #              course_settings['reg_form']['registration'] == 'OPEN')


        course_item = course_settings['course']
        reg_item = dict()
        if 'reg_form' in course_settings:
            reg_item = course_settings['reg_form']

        course_whitelist = course_item.pop('whitelist', None)
        reg_whitelist = reg_item.get('whitelist', None)
        if not reg_whitelist and course_whitelist:
            reg_item['whitelist'] = course_whitelist

        content = yaml.safe_dump(course_settings)
        try:
            cls.validate_settings_content(content)
        except yaml.YAMLError as e:  # pylint: disable=W0703
            logging.error('Failed to validate course settings: %s.', str(e))
            return False

        logging.debug("Content of of the course settings");
        logging.debug(content);
        content_stream = vfs.string_to_stream(unicode(content))
        # Store settings.
        course.set_file_content('/course.yaml', content_stream)

        explorer_item = dict()
        if 'explorer' in course_settings:
            explorer_item = course_settings['explorer']

        whitelist=reg_item.get('whitelist', None)
        if not whitelist:
            # Backword compatibility
            whitelist=course_item.get('whitelist', None)

        # Backward compatibility, depreciated fields.
        blurb = explorer_item.get("blurb")
        if not blurb:
            blurb = course_item.get("blurb")

        should_list = explorer_item.get("should_list")
        if not should_list:
            should_list = course_item.get("should_list")


        course_admin_email_str = course_item.get('admin_user_emails')
        if course_admin_email_str:
            course_admin_email = utils.text_to_list(
                course_admin_email_str, utils.BACKWARD_COMPATIBLE_SPLITTER)
        else:
            course_admin_email = []

        logging.debug("trying to save reg_form="+str(reg_item));

        category = course_item.get('category_name', '').strip()
        if category:
            CourseListDAO.update_course_details(
                course.app_context.get_namespace_name(),
                title=course_item.get('title'),
                browsable=course_item.get('browsable'),
                visible=course_item.get('now_available'),
                whitelist=reg_item.get('whitelist', None),
                category=course_item.get('category_name'),
                can_register=reg_item.get('can_register'),
                registration=reg_item.get('registration'),
                blurb=blurb,
                instructor_details=course_item.get('instructor_details'),
                explorer_summary=course_item.get('explorer_summary'),
                explorer_instructor_name=course_item.get(
                    'explorer_instructor_name'),
                should_list=should_list,
                show_in_explorer=course_item.get('show_in_explorer'),
                closed=course_item.get('closed', False),
                course_admin_email=course_admin_email,
                locale=course_item.get('locale'),
                featured=course_item.get('featured'),
                start_date=course_item.get('start_date'),
                end_date=course_item.get('end_date'),
                tags=course_item.get('tags'),
                spoc_mentor=course_item.get('spoc_mentor')
                )
        else:
            CourseListDAO.update_course_details(
                course.app_context.get_namespace_name(),
                title=course_item.get('title'),
                browsable=course_item.get('browsable'),
                visible=course_item.get('now_available'),
                whitelist=reg_item.get('whitelist', None),
                # category=course_item.get('category_name'),
                can_register=reg_item.get('can_register'),
                registration=reg_item.get('registration'),
                blurb=blurb,
                instructor_details=course_item.get('instructor_details'),
                explorer_summary=course_item.get('explorer_summary'),
                explorer_instructor_name=course_item.get(
                    'explorer_instructor_name'),
                should_list=should_list,
                show_in_explorer=course_item.get('show_in_explorer'),
                closed=course_item.get('closed', False),
                course_admin_email=course_admin_email,
                locale=course_item.get('locale'),
                featured=course_item.get('featured'),
                start_date=course_item.get('start_date'),
                end_date=course_item.get('end_date'),
                tags=course_item.get('tags'),
                spoc_mentor=course_item.get('spoc_mentor')
                )
        course.invalidate_cached_course_settings()
        return True
