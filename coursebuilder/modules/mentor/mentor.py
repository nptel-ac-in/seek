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

"""Handlers that are not directly related to course content."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import csv
import os
import StringIO
import datetime

from common.utils import Namespace

from controllers import sites
from controllers.utils import BaseHandler
from controllers.utils import BaseRESTHandler
from controllers.utils import ReflectiveRequestHandler
from controllers.utils import XsrfTokenManager

from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from models import roles
from modules.oeditor import oeditor
from models import transforms
from models import course_list
from models.models import Student, StudentProfileDAO
from modules.mentor import base
from modules.mentor.mentor_model import Mentor
from modules.local_chapter import local_chapter_model

TEMPLATES_FOLDER_NAME = os.path.normpath('/modules/mentor/views/')

class MentorHandler(BaseHandler, ReflectiveRequestHandler, base.MentorBase):
    """Handler to set/remove mentor for a student."""

    default_action = 'select_mentor'
    get_actions = [default_action]
    post_actions = ['set_mentor', 'remove_mentor']

    def get_select_mentor(self):
        student = self.personalize_page_and_get_enrolled()
        if not student:
            self.redirect('/')
            return

        course = self.get_course()
        if not course:
            self.redirect('/')
            return

        if not self.can_use_mentor_feature(course):
            self.redirect('/')
            return

        mentor = Mentor.get_mentor_for_student(student.user_id)
        if mentor:
            self.template_value['mentor_email'] = mentor.email
        else:
            if student.profile.local_chapter:
                possible_mentor_list = Mentor.get_mentors_for_local_chapter(
                    student.profile.college_id, ignore_ids=[student.user_id])
            else:
                possible_mentor_list = (
                    Mentor.get_mentors_with_no_local_chapter(
                        ignore_ids=[student.user_id]))
            if len(possible_mentor_list) > 0:
                self.template_value['pmentors'] = possible_mentor_list

        self.template_value['navbar'] = {'mentor': True}
        self.template_value['set_mentor_xsrf_token'] = (
            XsrfTokenManager.create_xsrf_token('set_mentor'))
        self.template_value['remove_mentor_xsrf_token'] = (
            XsrfTokenManager.create_xsrf_token('remove_mentor'))

        path = sites.abspath(self.app_context.get_home_folder(),
                             TEMPLATES_FOLDER_NAME)
        self.render('mentor_select.html', additional_dirs = [path])


    def post_set_mentor(self):
        """Handles post requests."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            self.redirect('/')
            return
        course = self.get_course()
        if not course:
            self.redirect('/')
            return
        if not self.can_use_mentor_feature(course):
            self.redirect('/')
            return

        mentor_id = self.request.get('mentor_id')
        if mentor_id.strip():
            mentor = Mentor.set_mentor(mentor_id, student.user_id)
        self.redirect('/student/mentor')


    def post_remove_mentor(self):
        """Handles post requests."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            self.redirect('/')
            return
        course = self.get_course()
        if not course:
            self.redirect('/')
            return
        if not self.can_use_mentor_feature(course):
            self.redirect('/')
            return

        Mentor.set_mentor(None, student.user_id)
        self.redirect('/student/mentor')


class MenteeListHandler(BaseHandler, base.MentorBase):
    """Global profile handler for a student."""

    def mentee_score(self, mentee):
        scores_dict = dict()
        course = self.get_course()
        scores_list = course.get_all_scores(mentee)
        for unit in scores_list:
            if not unit['human_graded'] and unit['completed']:
                if unit['show_scores']:
                    scores_dict[unit['id']] = unit['score']
                else:
                    scores_dict[unit['id']] = 'submitted'
        return scores_dict

    def generate_mentee_data(self, mentor):
        profile_list, student_list = (
            StudentProfileDAO.bulk_get_student_and_profile_by_id(
                mentor.mentee))

        mlist = dict()
        for i, m in enumerate(student_list):
            if m is None:
                continue
            if not m.is_enrolled:
                continue
            mentee_details = self.mentee_score(m)
            mentee_details['email'] = m.email
            if profile_list[i] is not None and profile_list[i].nick_name:
                mentee_details['name'] = profile_list[i].nick_name
            else:
                mentee_details['name'] = ''
            mlist[m.user_id] = mentee_details
        return mlist

    def get_public_units(self, course):
        pu = []
        for unit in course.get_units():
            if unit.now_available:
                pu.append(unit)
        return pu

    def generate_assessments_list(self):
        course = self.get_course()
        unit_id_to_title_list = []
        for unit in self.get_public_units(course):
            if not unit.scored():
                continue
            show_scores = True
            submission_due_date = unit.workflow.get_submission_due_date()
            time_now = datetime.datetime.now()
            if submission_due_date is not None:
                if time_now < submission_due_date:
                    show_scores = False
            unit_id_to_title_list.append(
                (str(unit.unit_id), unit.title, show_scores))
        return unit_id_to_title_list


    def get(self):
        student = self.personalize_page_and_get_enrolled()
        if not student:
            self.redirect('/')
            return
        mentor = Mentor.get_by_id(student.user_id)
        if not mentor:
            self.redirect('/')
            return
        course = self.get_course()
        if not course:
            self.redirect('/')
            return
        if not self.can_use_mentor_feature(course):
            self.redirect('/')
            return

        user = self.get_user()
        assessment_list = self.generate_assessments_list()
        self.template_value['a_list'] = transforms.dumps(assessment_list)
        mlist = self.generate_mentee_data(mentor)
        if mlist is not None:
            self.template_value['mentee_list'] = transforms.dumps(mlist)

        self.template_value['navbar'] = {'mentee': True}
        path = sites.abspath(self.app_context.get_home_folder(),
                             TEMPLATES_FOLDER_NAME)
        self.render('mentee_list.html', additional_dirs = [path])



def create_bulk_mentor_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Mentors',
         description='Mentors',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})
    reg.add_property(SchemaField(
        'bulk_addition', 'Bulk Add Mentors (course_namespace, local_chapter_id,email)', 'text'))
    return reg


class BulkAddNewMentorRESTHandler(BaseRESTHandler):
    """Provides REST API to Bulk Add Mentors."""

    URI = '/rest/modules/mentor/bulk_add_mentors'
    DESCRIPTION = 'Bulk Add Mentors'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_bulk_mentor_registry().get_json_schema()
    ANNOTATIONS_DICT = create_bulk_mentor_registry().get_schema_dict()

    @classmethod
    def registration(cls):
        return create_bulk_mentor_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    def to_dict(self):
        """Assemble a dict with the unit data fields."""
        entity = {
            'bulk_addition':'course_namespace, local_chapter_id,email'}
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        course_namespace = updated_unit_dict['course_namespace']
        local_chapter_id = updated_unit_dict['local_chapter_id']
        email = updated_unit_dict['email']

        with Namespace(course_namespace):
            p = Student.get_by_email(email)
            if p is None:
                # Check if personal profile exists
                student_profile = StudentProfileDAO.get_profile_by_email(email)
                if student_profile:
                    # Auto register the user in this course
                    additional_fields = {
                        "form01": student_profile.nick_name
                    }
                    additional_fields = (
                        transforms
                        .dict_to_nested_lists_as_string(additional_fields))
                    p = Student(
                        key_name=email,
                        user_id=student_profile.user_id,
                        name=student_profile.nick_name,
                        additional_fields=additional_fields,
                        is_enrolled=True
                    )
                    p.put()
                else:
                    errors.append(
                       'Mentor %s doesnt exist.' % email)
                    return

            local_chapter = True
            if local_chapter_id:
                if local_chapter_model.LocalChapterDAO.get_local_chapter_by_key(
                    local_chapter_id) is None:
                    errors.append(
                        'Local Chapter %s doesnt exist.' % local_chapter_id)
                    return
            else:
                local_chapter_id = ''
                local_chapter = False

            mentor = Mentor.get_or_create(user_id=p.user_id)
            mentor.local_chapter = local_chapter
            mentor.college_id = local_chapter_id
            mentor.put()


    def get(self):
        """A GET REST method shared by all unit types."""
        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': ''})
            return

        message = ['Success.']
        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=self.to_dict(),
            xsrf_token=XsrfTokenManager.create_xsrf_token('bulk-add-mentors'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))

        if not self.assert_xsrf_token_or_fail(
                request, 'bulk-add-mentors', {}):
            return

        if not roles.Roles.is_super_admin():
            transforms.send_json_response(
                self, 401, 'Access denied.')
            return

        payload = request.get('payload')

        updated_dict = transforms.json_to_dict(
            transforms.loads(payload), self.get_schema_dict())
        errors = []

        bulk_addition = updated_dict['bulk_addition']
        reader = csv.reader(StringIO.StringIO(bulk_addition), delimiter=',')
        all_courses = course_list.CourseListDAO.get_course_list()
        course_namespaces = [cl.namespace for cl in all_courses]
        for row in reader:
            if len(row) != 3:
                errors.append('Invalid row %s' % row[0])
                continue

            course_namespace = row[0]
            local_chapter_id = row[1]
            email = row[2].strip()

            if course_namespace not in course_namespaces:
                errors.append('Course %s does not exist' % course_namespace)
                continue

            updated_dict = {
                'course_namespace': course_namespace,
                'local_chapter_id': local_chapter_id,
                'email': email
            }
            self.apply_updates(updated_dict, errors)

        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))



class MentorBaseAdminHandler(base.MentorBase):
    @classmethod
    def get_add_bulk_mentors(self,handler):
        """Handles 'get_add_bulk_mentors' action and renders new course entry editor."""
        if roles.Roles.is_super_admin():
            exit_url = '%s?tab=courses' % handler.LINK_URL
        else:
            exit_url = self.request.referer
        rest_url = BulkAddNewMentorRESTHandler.URI

        template_values = {}
        template_values['page_title'] = handler.format_title('Bulk Add Mentors')
        template_values['main_content'] = oeditor.ObjectEditor.get_html_for(
            self, BulkAddNewMentorRESTHandler.SCHEMA_JSON,
            BulkAddNewMentorRESTHandler.ANNOTATIONS_DICT,
            None, rest_url, exit_url,
            auto_return=True,
            save_button_caption='Upload Mentors')
        handler.render_page(template_values, in_tab='mentors')
