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

__author__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

from models.models import MemcacheManager
from models import transforms
from models.entities import BaseEntity
from models.models import NO_OBJECT

from google.appengine.ext import db


class ProgrammingAnswersEntity(BaseEntity):
    """Stores the response of student submission."""
    updated_on = db.DateTimeProperty(indexed=False, auto_now=True)

    # This is a string representation of a JSON dict.
    data = db.TextProperty(indexed=False)

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:submitted_programming_code:%s' % key

    @classmethod
    def _create_key(cls, student_id, unit_id):
        return '%s-%s' % (student_id, unit_id)

    @classmethod
    def create(cls, student, unit_id):
        return ProgrammingAnswersEntity(
            key_name=cls._create_key(student.user_id, unit_id))

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        user_id, unit_id = db_key.name().split('-', 1)
        return db.Key.from_path(
            cls.kind(), '%s-%s' % (transform_fn(user_id), unit_id))

    def put(self):
        """Do the normal put() and also add the object to memcache."""
        result = super(ProgrammingAnswersEntity, self).put()
        MemcacheManager.set(self._memcache_key(self.key().name()), self)
        return result

    def delete(self):
        """Do the normal delete() and also remove the object from memcache."""
        super(ProgrammingAnswersEntity, self).delete()
        MemcacheManager.delete(self._memcache_key(self.key().name()))

    @classmethod
    def get(cls, student, unit_id):
        """Loads programming answer entity."""
        key = cls._create_key(student.user_id, unit_id)
        value = MemcacheManager.get(cls._memcache_key(key))
        if NO_OBJECT == value:
            return None
        if not value:
            value = cls.get_by_key_name(key)
            if value:
                MemcacheManager.set(cls._memcache_key(key), value)
            else:
                MemcacheManager.set(cls._memcache_key(key), NO_OBJECT)
        return value


class ProgrammingSumissionEntity(ProgrammingAnswersEntity):
    """Stores the response of student submission."""
    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:programming_submission_code:%s' % key

    @classmethod
    def create(cls, student, unit_id):
        return ProgrammingSumissionEntity(
            key_name=cls._create_key(student.user_id, unit_id))


class SavedProgrammingCodeEntity(BaseEntity):
    """Stores last saved code for the student."""
    updated_on = db.DateTimeProperty(indexed=False, auto_now=True)

    # This is a string representation of a JSON dict.
    data = db.TextProperty(indexed=False)

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:saved_programming_code:%s' % key

    @classmethod
    def _create_key(cls, student_id, unit_id):
        return '%s-%s' % (student_id, unit_id)

    @classmethod
    def create(cls, student, unit_id):
        return SavedProgrammingCodeEntity(
            key_name=cls._create_key(student.user_id, unit_id))

    @classmethod
    def get_code(cls, student, unit_id):
        entity = cls.get(student, str(unit_id))
        return transforms.loads(entity.data) if entity else None

    @classmethod
    def save_code(cls, student, unit_id, lang, lang_dict):
        entity = cls.get(student, str(unit_id))
        if entity is None:
            entity = cls.create(student, str(unit_id))
        code_dict = transforms.loads(entity.data) if entity.data else dict()
        if not isinstance(code_dict, dict):
            code_dict = dict()
        code_dict[lang] = lang_dict
        entity.data = transforms.dumps(code_dict)
        entity.put()

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        user_id, unit_id = db_key.name().split('-', 1)
        return db.Key.from_path(
            cls.kind(), '%s-%s' % (transform_fn(user_id), unit_id))

    def put(self):
        """Do the normal put() and also add the object to memcache."""
        result = super(SavedProgrammingCodeEntity, self).put()
        MemcacheManager.set(self._memcache_key(self.key().name()), self)
        return result

    def delete(self):
        """Do the normal delete() and also remove the object from memcache."""
        super(SavedProgrammingCodeEntity, self).delete()
        MemcacheManager.delete(self._memcache_key(self.key().name()))

    @classmethod
    def get(cls, student, unit_id):
        """Loads programming answer entity."""
        key = cls._create_key(student.user_id, unit_id)
        value = MemcacheManager.get(cls._memcache_key(key))
        if NO_OBJECT == value:
            return None
        if not value:
            value = cls.get_by_key_name(key)
            if value:
                MemcacheManager.set(cls._memcache_key(key), value)
            else:
                MemcacheManager.set(cls._memcache_key(key), NO_OBJECT)
        return value


class ProgrammingTestCasesEntity(BaseEntity):
    """Stores stats about each test case for a assignment."""
    updated_on = db.DateTimeProperty(indexed=False, auto_now=True)

    # Each of the following is a string representation of a JSON dict.
    private_test_case_data = db.TextProperty(indexed=False)
    public_test_case_data = db.TextProperty(indexed=False)

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:programming_test_cases:%s' % key

    @classmethod
    def _create_key(cls, student_id, unit_id):
        return '%s-%s' % (student_id, unit_id)

    @classmethod
    def create(cls, student, unit_id):
        return ProgrammingTestCasesEntity(
            key_name=cls._create_key(student.user_id, unit_id))

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        user_id, unit_id = db_key.name().split('-', 1)
        return db.Key.from_path(
            cls.kind(), '%s-%s' % (transform_fn(user_id), unit_id))

    def put(self):
        """Do the normal put() and also add the object to memcache."""
        result = super(ProgrammingTestCasesEntity, self).put()
        MemcacheManager.set(self._memcache_key(self.key().name()), self)
        return result

    def delete(self):
        """Do the normal delete() and also remove the object from memcache."""
        super(ProgrammingTestCasesEntity, self).delete()
        MemcacheManager.delete(self._memcache_key(self.key().name()))

    @classmethod
    def get(cls, student, unit_id):
        """Loads programming answer entity."""
        key = cls._create_key(student.user_id, unit_id)
        value = MemcacheManager.get(cls._memcache_key(key))
        if NO_OBJECT == value:
            return None
        if not value:
            value = cls.get_by_key_name(key)
            if value:
                MemcacheManager.set(cls._memcache_key(key), value)
            else:
                MemcacheManager.set(cls._memcache_key(key), NO_OBJECT)
        return value

class ProgrammingAssignmentTestRunEntity(BaseEntity):
    """Stores stats about the latest test run for a programming assignment"""
    updated_on = db.DateTimeProperty(indexed=False, auto_now=True)
    data = db.TextProperty(indexed=False)

    @property
    def pa_id(self):
        return self.key().name()

    @classmethod
    def _memcache_key(cls, key):
        """Makes a memcache key from primary key."""
        return 'entity:programming_test_run:%s' % key

    @classmethod
    def _create_key(cls, pa_id):
        return '%s' % pa_id

    @classmethod
    def create(cls, pa_id):
        return ProgrammingAssignmentTestRunEntity(
            key_name=cls._create_key(pa_id))

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        user_id, unit_id = db_key.name().split('-', 1)
        return db.Key.from_path(
            cls.kind(), '%s-%s' % (transform_fn(user_id), unit_id))

    def put(self):
        """Do the normal put() and also add the object to memcache."""
        result = super(ProgrammingAssignmentTestRunEntity, self).put()
        MemcacheManager.set(self._memcache_key(self.key().name()), self)
        return result

    def delete(self):
        """Do the normal delete() and also remove the object from memcache."""
        super(ProgrammingAssignmentTestRunEntity, self).delete()
        MemcacheManager.delete(self._memcache_key(self.key().name()))

    @classmethod
    def get_by_pa_id(cls, pa_id):
        """Loads programming answer entity."""
        key = cls._create_key(pa_id)
        value = MemcacheManager.get(cls._memcache_key(key))
        if NO_OBJECT == value:
            return None
        if not value:
            value = cls.get_by_key_name(key)
            if value:
                MemcacheManager.set(cls._memcache_key(key), value)
            else:
                MemcacheManager.set(cls._memcache_key(key), NO_OBJECT)
        return value

    @classmethod
    def get_or_create(cls, pa_id):
        pa_id = str(pa_id)
        value = cls.get_by_pa_id(pa_id)
        if not value:
            value = cls.create(pa_id)
        return value

    @classmethod
    def save_evaluation_result(cls, pa_id, data):
        """Creates or updates the test run entity for pa_id"""
        entity = cls.get_or_create(pa_id)
        entity.data = data
        entity.put()
        return entity
