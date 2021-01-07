# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Core data model classes."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

from google.appengine.ext import ndb

from models.models import StudentProfileDAO

class Mentor(ndb.Model):
    """Model to hold mentor data"""
    # Email of the mentor
    email = ndb.StringProperty(indexed=False)

    # Local chapter related data
    ## Denotes whether the mentor is a part of a local chapter or not
    local_chapter = ndb.BooleanProperty(indexed=True)

    ## if local_chapter == True, denotes the college_id of the local chapter
    college_id = ndb.StringProperty(indexed=True, default=None)

    ## Mentees (students) under this mentor
    mentee = ndb.StringProperty(indexed=True, repeated=True)

    @property
    def user_id(self):
        return self.key.id()

    @classmethod
    def create(cls, user_id, copy_data_from_profile=False):
        mentor = Mentor(id=user_id)
        profile = cls._get_mentor_profile(user_id)
        mentor.email = profile.email
        if copy_data_from_profile:
            mentor.local_chapter = profile.local_chapter
            mentor.college_id = profile.college_id
        return mentor

    @classmethod
    def get_or_create(cls, user_id, copy_data_from_profile=False):
        value = cls.get_by_id(user_id)
        if value is not None:
            return value
        return cls.create(
            user_id, copy_data_from_profile=copy_data_from_profile)

    @classmethod
    def _get_mentor_profile(cls, mentor_id):
        return StudentProfileDAO.get_profile_by_user_id(mentor_id)

    @classmethod
    def get_mentors_for_local_chapter(cls, local_chapter_id, ignore_ids=None):
        mentor_list = Mentor.query(
            cls.local_chapter == True, cls.college_id == local_chapter_id).fetch(None)
        mentor_id_list = [
            mentor.user_id for mentor in mentor_list
            if mentor.user_id not in ignore_ids]
        mentor_profile_list = StudentProfileDAO.bulk_get_student_profile_by_id(
            mentor_id_list)
        return mentor_profile_list

    @classmethod
    def get_mentors_with_no_local_chapter(cls, ignore_ids=None):
        mentor_list = Mentor.query(cls.local_chapter == False).fetch(None)
        mentor_id_list = [
            mentor.user_id for mentor in mentor_list
            if mentor.user_id not in ignore_ids]
        mentor_profile_list = StudentProfileDAO.bulk_get_student_profile_by_id(
            mentor_id_list)
        return mentor_profile_list

    @classmethod
    def get_all_mentors(cls):
        return Mentor.query().fetch(None)

    @classmethod
    def _get_mentor_for_student(cls, student_id):
	for mentor in Mentor.query(cls.mentee == student_id).fetch(None):
            if mentor.mentee.count(student_id) >= 1:
                return mentor
        return None

    @classmethod
    def get_mentor_for_student(cls, student_id):
        mentor = cls._get_mentor_for_student(student_id)
	if mentor:
            return StudentProfileDAO.get_profile_by_user_id(mentor.user_id)
        return None

    @classmethod
    @ndb.transactional()
    def _remove_mentee(cls, mentor_id, student_id):
        mentor = cls.get_by_id(mentor_id)
        if not mentor:
            return
        if mentor.mentee.count(student_id) >= 1:
            mentor.mentee.remove(student_id)
            mentor.put()

    @classmethod
    @ndb.transactional()
    def _add_mentee(cls, mentor_id, student_id):
        mentor = cls.get_by_id(mentor_id)
        if mentor:
            mentor.mentee.append(student_id)
            mentor.mentee = sorted(set(mentor.mentee))
            mentor.put()

    @classmethod
    def set_mentor(cls, mentor_id, student_id):
        if mentor_id == student_id:
            return
        mentor = cls._get_mentor_for_student(student_id)
        if mentor:
            cls._remove_mentee(mentor.user_id, student_id)
        if mentor_id:
            cls._add_mentee(mentor_id, student_id)

    @classmethod
    def delete_mentor(cls, mentor_id):
        """Deletes a mentor object"""
        mentor = Mentor.get_by_id(mentor_id)
        if mentor:
            mentor.key.delete()

    @classmethod
    def bulk_get_mentor_by_user_id(cls, user_ids):
        key_list = [ndb.Key(Mentor, uid) for uid in user_ids]
        return ndb.get_multi(key_list)
