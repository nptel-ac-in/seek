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

"""Contain Dashboard Handler for SPOC."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import os
import csv
import jinja2
import mimetypes
import StringIO

from google.appengine.ext import db
from google.appengine.ext import ndb
from google.appengine.api import users

import appengine_config
from common import csv_unicode
from controllers import sites
from common import utils
from models import models
from models import transforms
from modules.mentor import mentor_model
from modules.student_list import handlers as student_list_handlers
from modules.local_chapter import local_chapter_model
from modules.local_chapter import base as local_chapter_base

from modules.spoc import roles as spoc_roles
from modules.spoc import base

custom_module = None

class SPOCDashboardHandler(base.SPOCBase, spoc_roles.SPOCRoleManager,
                           student_list_handlers.InteractiveTableHandler):
    """Dashboard Handler for SPoC."""

    NAME = 'List of Members for your Local Chapter'
    SEARCH_STR_PARAM = 'email'
    DEFAULT_ORDER = 'email'
    DEFAULT_NUM_ENTRIES = 'all'
    DASHBOARD_CATEGORY = 'analytics'
    LIST_ACTION = base.SPOCBase.DASHBOARD_LIST_ACTION
    DETAILS_ACTION = 'spoc_student_details'
    DOWNLOAD_ACTION = 'download_student_list'
    SAVE_ACTION = 'spoc_save'
    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME

    @classmethod
    def get_by_search_str(cls, email):
        return models.StudentProfileDAO.get_profile_by_email(email)

    @classmethod
    def run_query(cls, cursor=None, **kwargs):
        local_chapter_id = kwargs.get('local_chapter_id')
        org_type = kwargs.get('org_type')
        if cursor:
            query = db.Query(models.PersonalProfile, cursor=cursor)
        else:
            query = db.Query(models.PersonalProfile)

        if org_type == local_chapter_base.LocalChapterBase.LOCAL_CHAPTER_ORG_INDUSTRY:
            return query.filter(
                'local_chapter =', True
            ).filter('employer_id =', local_chapter_id)
        else:    
            return query.filter(
                'local_chapter =', True
            ).filter('college_id =', local_chapter_id)

    @classmethod
    def post_query_fn(cls, profiles, template_value):
        # Replace template_value['objects']
        # This is required to filter out students not in this course.
        student_ids = [profile.user_id for profile in profiles]
        students = models.StudentProfileDAO.bulk_get_student_by_id(student_ids)

        new_profiles = list()
        new_students = list()

        for i, student in enumerate(students):
            if student:
                new_students.append(student)
                new_profiles.append(profiles[i])

        template_value['students'] = new_students
        return new_profiles

    @classmethod
    def display_html(cls, handler):
        """Displays list of students in SPoC's local chapter"""
        user = users.get_current_user()
        if not user:
            return
        email = user.email()
        local_chapter = (
            local_chapter_model.LocalChapterDAO.
            get_local_chapter_for_spoc_email(email))
        if not local_chapter:
            handler.error(404)
            handler.render_page({
                'page_title': custom_module.name,
                'main_content': 'Local chapter not found'
            })
            return
        org_type = local_chapter.org_type
        local_chapter_id = local_chapter.code

        course = handler.get_course()
        if not course:
            handler.error(404)
            handler.render_page({
                'page_title': custom_module.name,
                'main_content': 'Course not found'
            })
            return

        if not cls.can_view():
            handler.error(403)
            handler.render_page({
                'page_title': custom_module.name,
                'main_content': 'Forbidden to access this page.'
            })
            return

        template_value = dict()

        if not cls.generate_table(handler, template_value,
                    local_chapter_id=local_chapter_id, org_type=org_type):
            handler.error(400)
            handler.render_page({
                'page_title': custom_module.name,
                'main_content': 'Invalid parameters'
            })
            return


        mentor_list = mentor_model.Mentor.get_mentors_for_local_chapter(
            local_chapter_id, ignore_ids=list())
        mentor_dict = dict((mentor.user_id, mentor) for mentor in mentor_list)
        template_value['mentor_dict'] = mentor_dict
        template_value['local_chapter'] = local_chapter
        template_value['course'] = course
        template_value['list_action'] = handler.get_action_url(cls.LIST_ACTION)
        template_value['save_url'] = handler.get_action_url(
            cls.SAVE_ACTION)
        template_value['save_xsrf_token'] = handler.create_xsrf_token(
            cls.SAVE_ACTION)

        template_value['org_type'] = org_type
        template_value['allow_update_mentor'] = course.app_context.spoc_mentor
        template_value['units'] = course.get_units()

        # parse the student scores
        student_scores_list = []
        for student in template_value['students']:
            scores = {}
            if student.scores:
                scores = transforms.loads(student.scores)
            student_scores_list.append(scores)

        template_value['student_scores_list'] = student_scores_list
        return jinja2.utils.Markup(
            handler.get_template(
                'templates/list.html',
                [os.path.dirname(__file__)]).render(template_value))

    @classmethod
    def _update_mentor_status(cls, mentor_data_dict, spoc_mentor, org_type):
        """Sets or unsets a student as as mentor. Used as a POST endpoint."""

        if not spoc_mentor:
            return

        mentors = mentor_model.Mentor.bulk_get_mentor_by_user_id(
            mentor_data_dict.keys())
        profiles = models.StudentProfileDAO.bulk_get_student_profile_by_id(
            mentor_data_dict.keys())
        mentors_to_add = list()
        mentor_keys_to_remove = list()

        for i, uid in enumerate(mentor_data_dict.keys()):
            is_mentor = mentor_data_dict[uid]
            profile = profiles[i]
            if is_mentor and ( profile.profession == 'faculty' or org_type =="industry" ):
                mentor = mentor_model.Mentor.get_or_create(
                    uid, copy_data_from_profile=True)
                mentors_to_add.append(mentor)
            else:
                mentor_keys_to_remove.append(
                    ndb.Key(mentor_model.Mentor, uid)
                )

        if mentors_to_add:
            ndb.put_multi(mentors_to_add)
        if mentor_keys_to_remove:
            ndb.delete_multi(mentor_keys_to_remove)

    @classmethod
    def save_student_data(cls, handler):
        """
        Saves student data (mentor status).
        Used as a POST endpoint
        """

        course = handler.get_course()
        if not course:
            handler.error(404)
            handler.render_page({
                'page_title': custom_module.name,
                'main_content': 'Course not found'
            })
            return
        if not cls.can_edit(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': custom_module.name,
                'main_content': 'Forbidden to access this page.'
            })
            return

        mentor_data_raw = handler.request.get('mentor-data')
        org_type = handler.request.get('org_type') 
        if not mentor_data_raw:
            handler.error(400)
            handler.render_page({
                'page_title': 'SPoC Dashboard',
                'main_content': 'Invalid Parameters'
            })
            return
        mentor_data_dict = transforms.loads(mentor_data_raw)
        cls._update_mentor_status(mentor_data_dict, course.app_context.spoc_mentor, org_type)
        handler.redirect(handler.get_action_url(cls.LIST_ACTION))

    @classmethod
    def download_student_list(cls, handler):
        """Returns a CSV of the student list for download"""

        user = users.get_current_user()

        if not cls.can_view():
            cls.handler.error(403)
            cls.handler.render_page({
                'page_title': custom_module.name,
                'main_content': 'Forbidden to access this page'
            })
            return

        if not user:
            cls.handler.error(401)
            cls.handler.redirect('/')

        email = user.email()
        local_chapter = (
            local_chapter_model.LocalChapterDAO.
            get_local_chapter_for_spoc_email(email))
        if not local_chapter:
            cls.handler.error(400)
            cls.handler.render_page({
                'page_title': custom_module.name,
                'main_content': 'Local Chapter not found'
            })
            return

        org_type = local_chapter.org_type
        local_chapter_id = local_chapter.code
        course = handler.get_course()
        units = course.get_units()

        with utils.Namespace(appengine_config.DEFAULT_NAMESPACE_NAME):
            profiles = cls.run_query(local_chapter_id=local_chapter_id, org_type=org_type).fetch(None)
        student_ids = [profile.user_id for profile in profiles]
        students = models.StudentProfileDAO.bulk_get_student_by_id(student_ids)

        new_profiles = list()
        new_students = list()

        for i, student in enumerate(students):
            if student and student.is_enrolled:
                new_students.append(student)
                new_profiles.append(profiles[i])

        mentor_list = mentor_model.Mentor.get_mentors_for_local_chapter(
            local_chapter_id, ignore_ids=list())
        mentor_dict = dict((mentor.user_id, mentor) for mentor in mentor_list)

        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(output, delimiter=",", quotechar='"',
                                           quoting=csv.QUOTE_MINIMAL)

        headers = [
            'User ID',
            'Email',
            'Name',
            'Date of Birth',
            'Mobile',
            'Enrolled Courses',
            'Country',
            'State',
            'City',
            'College',
            'Employer',
            'Roll Number',
            'Age Group',
            'Graduation Year',
            'Profession',
            'Scholarship',
            'Mentor'
        ]

        for unit in units:
            headers.append(unit.title+"("+ str(unit.unit_id)+")")
        

        writer.writerow(headers)

        open_course_namespaces = [
            course.namespace for course in
            sites.get_visible_courses(include_closed=False)]

        for i, student in enumerate(new_students):
            profile = new_profiles[i]
            enrollment_info = transforms.loads(profile.enrollment_info)
            # Check if student enrolled in any of the current courses
            enrolled_namespaces = [
                ns for ns, is_enrolled in enrollment_info.iteritems()
                if (is_enrolled and ns in open_course_namespaces)]

            row = [
            profile.user_id,
            profile.email,
            profile.nick_name,
            profile.date_of_birth,
            profile.mobile_number,
            '"%s"' % ','.join(enrolled_namespaces),
            profile.country_of_residence,
            profile.state_of_residence,
            profile.city_of_residence,
            profile.name_of_college,
            profile.employer_name,
            profile.college_roll_no,
            profile.age_group,
            profile.graduation_year,
            profile.profession,
            profile.scholarship,
            "yes" if profile.user_id in mentor_dict else "no"]

            
            for unit in units:
                scores = None
                score = None
                if student.scores:
                    scores = transforms.loads(student.scores)
                    if scores and scores.has_key( str(unit.unit_id)):
                        score =scores[str(unit.unit_id)]

                if not score:
                    score=0
                row.append(score)

            writer.writerow(row)
        filename = 'students_for_%s.csv' % handler.app_context.namespace
        (content_type, _) = mimetypes.guess_type(filename)
        handler.response.headers['Content-Type'] = content_type
        handler.response.headers['Content-Disposition'] = 'attachment; filename=' + filename
        handler.response.write(output.getvalue())
