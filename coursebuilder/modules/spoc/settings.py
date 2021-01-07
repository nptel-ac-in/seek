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

"""Admin handler for SPoC"""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import jinja2
import csv
import os
import mimetypes
import StringIO

from google.appengine.api import users
from google.appengine.ext import db
import appengine_config

from common import csv_unicode
from controllers import sites
from controllers import utils
from common import menus
from models import models
from models import transforms
from models import course_list
from modules.dashboard import dashboard
from modules.admin import admin
from modules.spoc import base
from modules.spoc import roles as spoc_roles
from modules.spoc import dashboard as spoc_dashboard

from modules.student_list import handlers as student_list_handlers
from modules.local_chapter import local_chapter_model
from modules.local_chapter import base as local_chapter_base

custom_module = None

class SPOCGlobalAdminHandler(base.SPOCBase, spoc_roles.SPOCRoleManager,
                             admin.GlobalAdminHandler,
                             student_list_handlers.InteractiveTableHandler):
    """Handler to present student details to the SPOC"""

    URL = '/spoc'
    LINK_URL = '/spoc'
    IN_ACTION = 'student_list'
    TEMPLATE_FILE = 'templates/profile_list.html'
    TEMPLATE_DIRS = [os.path.dirname(__file__)]

    NAME = 'SPoC Global Student List'
    SEARCH_STR_PARAM = 'email'
    DEFAULT_ORDER = 'email'
    DEFAULT_NUM_ENTRIES = 'all'
    LIST_ACTION = 'list'
    SAVE_ACTION = 'save_student_data'
    default_action = 'courses'
    DOWNLOAD_ACTION = 'download_student_list'
    get_actions = [default_action, LIST_ACTION, DOWNLOAD_ACTION]
    post_actions = [SAVE_ACTION]
    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME

    # Take a method from DashboardHandler. We don't want to inherit all the
    # methods and functions, need only this one.
    add_sub_nav_mapping = dashboard.DashboardHandler.__dict__[
        'add_sub_nav_mapping']

    @classmethod
    def run_query(cls, cursor=None, **kwargs):
        local_chapter_id = kwargs.get('local_chapter_id')
        org_type = kwargs.get('org_type')
        if cursor:
            query = db.Query(models.PersonalProfile, cursor=cursor)
        else:
            query = db.Query(models.PersonalProfile)
        q = query.filter(
            'local_chapter =', True
        )
        if org_type == local_chapter_base.LocalChapterBase.LOCAL_CHAPTER_ORG_INDUSTRY and local_chapter_id:
            q = q.filter('employer_id =', local_chapter_id)

        if org_type == local_chapter_base.LocalChapterBase.LOCAL_CHAPTER_ORG_COLLEGE and local_chapter_id:
            q = q.filter('college_id =', local_chapter_id)
        return q

    @classmethod
    def post_query_fn(cls, profiles, template_value):
        """
        This function filters out students who are not enrolled in any
        active (not closed) courses
        """

        open_course_namespaces = [
            course.namespace for course in
            sites.get_visible_courses(include_closed=False)]

        new_profiles = []

        for profile in profiles:
            enrollment_info = transforms.loads(profile.enrollment_info)
            # Check if student enrolled in any of the current courses
            old_keys = enrollment_info.keys()
            for ns in old_keys:
                if not (enrollment_info[ns] and ns in open_course_namespaces):
                    enrollment_info.pop(ns)
            enrolled_namespaces = enrollment_info.keys()
            if enrolled_namespaces:
                profile.enrollment_info = transforms.dumps(enrollment_info)
                new_profiles.append(profile)

        template_value['profiles'] = new_profiles
        return new_profiles

    @classmethod
    def install_courses_menu_item(cls):
        menu_item = menus.MenuItem(
            'courses', 'Courses', action='courses',
            can_view=cls.can_view,
            href="{}?action=courses".format(cls.LINK_URL))

        cls.actions_to_menu_items['courses'] = menu_item

    @classmethod
    def _update_scholarship_status(cls, scholarship_data_dict):
        if base.SPOC_UPDATE_SCHOLARSHIP.value:
            models.StudentProfileDAO.bulk_set_scholarship_status(
                scholarship_data_dict.keys(), scholarship_data_dict.values())

    @classmethod
    def calculate_student_registration_data(cls, local_chapter_id, org_type):
        """Calcualtes the number of students registered per course"""
        student_registration_data = {}
        student_profiles = cls.run_query(local_chapter_id=local_chapter_id, org_type=org_type).fetch(None)        
        student_profiles = cls.post_query_fn(student_profiles, {})
        student_registration_data['total_students'] = 0
        student_registration_data['total_registrations'] = 0
        for student in student_profiles:
            added_to_total = False
            for namespace in transforms.loads(student.enrollment_info):
                if not added_to_total:
                    student_registration_data['total_students'] += 1
                    added_to_total = True
                student_registration_data['total_registrations'] += 1
                if namespace in student_registration_data:
                    student_registration_data[namespace] += 1
                else:
                    student_registration_data[namespace] = 1
        return student_registration_data

    def get_courses(self):
        """Displays list of active courses for SPoC"""
        user = users.get_current_user()

        if not self.can_view():
            self.error(403)
            self.render_page({
                'page_title': custom_module.name,
                'main_content': 'Forbidden to access this page'
            })
            return

        if not user:
            self.error(401)
            self.redirect('/')

        email = user.email()
        local_chapter = (
            local_chapter_model.LocalChapterDAO.
            get_local_chapter_for_spoc_email(email))
        if not (local_chapter or self.is_global_spoc(user)):
            self.error(400)
            self.render_page({
                'page_title': custom_module.name,
                'main_content': 'Local Chapter not found'
            })
            return

        courses = sites.get_visible_courses(include_closed=False)

        template_value = {
            'courses': courses,
            'dashboard_action': spoc_dashboard.SPOCDashboardHandler.LIST_ACTION,
            'student_registration_data': self.calculate_student_registration_data(
                local_chapter.code if local_chapter else None, local_chapter.org_type if local_chapter else None,),
            'local_chapter': local_chapter,
        }
        content = jinja2.utils.Markup(
            self.get_template(
                'templates/courses.html',
                [os.path.dirname(__file__)]).render(template_value))
        self.render_page({
        'page_title': 'Active Courses for %s' % local_chapter.name,
            'main_content': content
        })

    def get_list(self):
        """Displays global list of students in SPoC's local chapter"""
        user = users.get_current_user()

        if not self.can_view():
            self.error(403)
            self.render_page({
                'page_title': custom_module.name,
                'main_content': 'Forbidden to access this page'
            })
            return

        if not user:
            self.error(401)
            self.redirect('/')

        email = user.email()
        local_chapter = (
            local_chapter_model.LocalChapterDAO.
            get_local_chapter_for_spoc_email(email))

        local_chapter_id = None
        org_type = None
        if local_chapter:
            local_chapter_id = local_chapter.code
            org_type = local_chapter.org_type
        elif self.is_global_spoc(user):
            local_chapter_id = None
            org_type = None
        else:
            self.error(400)
            self.render_page({
                'page_title': custom_module.name,
                'main_content': 'Local Chapter not found'
            })
            return

        template_value = {
            'namespace_to_name_dict': dict(
                (cl.namespace, cl.title) for cl in
                course_list.CourseListDAO.get_course_list()),
            'save_url': '/spoc?action=' + self.SAVE_ACTION,
            'save_xsrf_token': self.create_xsrf_token(self.SAVE_ACTION),
            'local_chapter': local_chapter,
            'allow_update_scholarship': base.SPOC_UPDATE_SCHOLARSHIP.value,
        }
        self.render_table(template_value, local_chapter_id=local_chapter_id,org_type=org_type)

    def get_download_student_list(self):
        """Returns a CSV of the student list for download"""

        user = users.get_current_user()

        if not self.can_view():
            self.error(403)
            self.render_page({
                'page_title': custom_module.name,
                'main_content': 'Forbidden to access this page'
            })
            return

        if not user:
            self.error(401)
            self.redirect('/')

        email = user.email()
        local_chapter = (
            local_chapter_model.LocalChapterDAO.
            get_local_chapter_for_spoc_email(email))
        local_chapter_id = None
        org_type = None
        if local_chapter:
            local_chapter_id = local_chapter.code
            org_type = local_chapter.org_type
        elif self.is_global_spoc(user):
            local_chapter_id = None
            org_type = None
        else:
            self.error(400)
            self.render_page({
                'page_title': custom_module.name,
                'main_content': 'Local Chapter not found'
            })
            return

        student_profiles = self.run_query(local_chapter_id=local_chapter_id, org_type=org_type).fetch(None)
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(output, delimiter=",", quotechar='"',
                                           quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
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
            'Roll Number',
            'Employer',
            'Age Group',
            'Graduation Year',
            'Profession',
            'Scholarship',
            'Qualification',
            'Degree',
            'Department',
            'Study Year',
            'Motivation',
            'Designation',
            'Exam Taker'
        ])

        open_course_namespaces = [
            course.namespace for course in
            sites.get_visible_courses(include_closed=False)]

        for student in student_profiles:
            enrollment_info = transforms.loads(student.enrollment_info)
            # Check if student enrolled in any of the current courses
            enrolled_namespaces = [
                ns for ns, is_enrolled in enrollment_info.iteritems()
                if (is_enrolled and ns in open_course_namespaces)]
            if not enrolled_namespaces:
                continue

            writer.writerow([
                student.user_id,
                student.email,
                student.nick_name,
                student.date_of_birth,
                student.mobile_number,
                '"%s"' % ','.join(enrolled_namespaces),
                student.country_of_residence,
                student.state_of_residence,
                student.city_of_residence,
                student.name_of_college,
                student.college_roll_no,
                student.employer_name,
                student.age_group,
                student.graduation_year,
                student.profession,
                student.scholarship,
                student.qualification,
                student.degree,
                student.department,
                student.study_year,
                student.motivation,
                student.designation,
                "Yes" if student.exam_taker else "No"

            ])

        filename = 'all_students.csv'
        (content_type, _) = mimetypes.guess_type(filename)
        self.response.headers['Content-Type'] = content_type
        self.response.headers['Content-Disposition'] = 'attachment; filename=' + filename
        self.response.write(output.getvalue())

    def post_save_student_data(self):
        """
        Saves student data (scholarship).
        Used as a POST endpoint.
        """

        if not self.can_edit():
            self.error(403)
            self.render_page({
                'page_title': custom_module.name,
                'main_content': 'Forbidden'
            })
            return

        scholarship_data_raw = self.request.get('scholarship-data')
        if not scholarship_data_raw:
            self.error(400)
            self.render_page({
                'page_title': 'Error: SPoC Global Student List',
                'main_content': 'Invalid Parameters'
            })
            return

        scholarship_data_dict = transforms.loads(scholarship_data_raw)
        self._update_scholarship_status(scholarship_data_dict)
        self.redirect('/spoc?action=' + self.LIST_ACTION)


def populate_menu():
    SPOCGlobalAdminHandler.install_courses_menu_item()

    SPOCGlobalAdminHandler.add_sub_nav_mapping(
        'analytics', 'spoc_global_student_list', 'All Local Chapter Members',
        action='list', can_view=SPOCGlobalAdminHandler.can_view,
        no_app_context=True)

global_routes = [
    (SPOCGlobalAdminHandler.URL, SPOCGlobalAdminHandler)
]
