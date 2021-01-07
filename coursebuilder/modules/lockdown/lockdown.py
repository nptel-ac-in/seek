# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Module for locking down assessments to prevent unwanted edits."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

from google.appengine.ext import ndb

class Lockdown(ndb.Model):
    locked = ndb.BooleanProperty(default=False)

    @classmethod
    def convert_to_ndb_id(cls, _type, _id):
        return '%s_%s' % (_type, _id)

    @classmethod
    def get_or_create_by_id_and_type(cls, _type, _id):
        ndb_id = cls.convert_to_ndb_id(_type, _id)
        obj = cls.get_by_id(ndb_id)
        if not obj:
            obj = cls(id=ndb_id)
        return obj

    @classmethod
    def set_for_id_and_type(cls, _type, _id, value):
        # TODO(rthakker) implement this
        obj = cls.get_or_create_by_id_and_type(_type, _id)
        if obj.locked != value:
            obj.locked = value
            obj.put()
