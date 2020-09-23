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

"""Common classes and methods for managing course staff."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

from models.entities import BaseEntity
from google.appengine.ext import db


class CourseStaff(BaseEntity):
    """Course Staff related details."""
    email = db.StringProperty(indexed=False)

    can_grade = db.BooleanProperty(indexed=True)
    can_override = db.BooleanProperty(indexed=False)

    num_graded = db.IntegerProperty(default=0, indexed=True)
    num_assigned = db.IntegerProperty(default=0, indexed=True)

    # Following is a string representation of a JSON dict.
    data = db.TextProperty(indexed=False)

    # Custom Unit Support
    CUSTOM_UNITS = {}

    @classmethod
    def add_custom_unit(cls, unit_type_id, list_action):
        """
        Adds custom assessment evaluation support.

        `unit_type_id` is the UNIT_TYPE_ID of the custom_unit.
        `list_action` is the GET action which will be called when someone clicks on
            this type of assessment in the course_staff view.

            This list action also needs to be added to the custom_get_actions with
            a handler function.

            Refer to modules.course_staff.evaluate.EvaluationHandler
        """
        cls.CUSTOM_UNITS[unit_type_id] = {
            'list_action': list_action
        }

    @property
    def user_id(self):
        return self.key().name()

    @classmethod
    def create_key(cls, user_id):
        return str(user_id)

    @classmethod
    def create(cls, profile):
        return CourseStaff(key_name=cls.create_key(profile.user_id))

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        return db.Key.from_path(cls.kind(), transform_fn(db_key.name()))

    @classmethod
    def get(cls, user_id):
        """Loads programming answer entity."""
        key = cls.create_key(user_id)
        return cls.get_by_key_name(key)
