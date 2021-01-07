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

"""Classes supporting courses viewed by a student."""

__author__ = 'Rahul Singal (rahulsingal@google.com)'

import mimetypes
import os
import random
from collections import OrderedDict

from modules.explorer import settings
import webapp2

import appengine_config
from common import jinja_utils
from common import users
from controllers import sites
from controllers.utils import CBRequestHandler
from controllers.utils import BaseProfileHandler
from controllers.utils import ApplicationHandler
from controllers.utils import PageInitializerService
from controllers.utils import ReflectiveRequestHandler
from controllers.utils import XsrfTokenManager
from gae_mini_profiler import templatetags
from models import courses as Courses
from models import course_category
from models import transforms
from models.models import StudentProfileDAO
from models.roles import Roles
from controllers import utils
from models import courses as models_courses
from models import models
from models import roles
from models import transforms
from modules.spoc import roles as spoc_roles

# We want to use views file in both /views and /modules/course_explorer/views.
TEMPLATE_DIRS = [
    os.path.join(appengine_config.BUNDLE_ROOT, 'views'),
    os.path.join(
        appengine_config.BUNDLE_ROOT, 'modules', 'explorer', 'templates'),
]


# Int. Maximum number of bytes App Engine's db.StringProperty can store.
_STRING_PROPERTY_MAX_BYTES = 500

STUDENT_RENAME_GLOBAL_XSRF_TOKEN_ID = 'student_rename_token'


class BaseStudentHandler(CBRequestHandler):
    """Base Handler for a student's courses."""

    def __init__(self, *args, **kwargs):
        super(BaseStudentHandler, self).__init__(*args, **kwargs)
        self.template_value = {}
        self.initialize_student_state()

    def get_locale_for_user(self):
        """Chooses locale for a user."""
        return 'en_US'  # TODO(psimakov): choose proper locale from profile

    def initialize_student_state(self):
        """Initialize course information related to student."""
        utils.PageInitializerService.get().initialize(self.template_value)
        self.enrolled_courses_dict = {}
        self.courses_progress_dict = {}
        user = users.get_current_user()
        if not user:
            return

        profile = models.StudentProfileDAO.get_profile_by_user_id(
            user.user_id())
        if not profile:
            return

        self.template_value['register_xsrf_token'] = (
            utils.XsrfTokenManager.create_xsrf_token('register-post'))

        self.enrolled_courses_dict = transforms.loads(profile.enrollment_info)
        if self.enrolled_courses_dict:
            self.template_value['has_enrolled_courses'] = True

        if profile.course_info:
            self.courses_progress_dict = transforms.loads(profile.course_info)

    def get_public_courses(self, include_closed=True):
        """Get all the public courses."""
        public_courses = []
        for course in sites.get_all_courses(include_closed=include_closed):
            if ((course.now_available and roles.Roles.is_user_whitelisted(
                    course)) or roles.Roles.is_course_admin(course)):
                public_courses.append(course)
        return public_courses

    def get_listable_courses(self, include_closed=True):
        """Get all the public courses."""
        listable_courses = []
        for course in self.get_public_courses(include_closed=include_closed):
            if (course.should_list or self.is_enrolled(course)):
                listable_courses.append(self.get_course_info(course))
        return listable_courses

    def is_enrolled(self, course):
        """Returns true if student is enrolled else false."""
        return bool(
            self.enrolled_courses_dict.get(course.get_namespace_name()))

    def is_completed(self, course):
        """Returns true if student has completed course else false."""
        info = self.courses_progress_dict.get(course.get_namespace_name())
        if info and 'final_grade' in info:
            return True
        return False

    def can_register(self, course):
        return course.get_environ()['reg_form']['can_register']

    def get_course_info(self, course):
        """Returns course info required in views."""
        course_preview_url = course.slug
        if course.slug == '/':
            course_preview_url = '/course'
        course.course_preview_url = course_preview_url
        course.is_registered = self.is_enrolled(course)
        course.is_completed = self.is_completed(course)
        return course

    def get_enrolled_courses(self, courses):
        """Returns list of courses registered by student."""
        enrolled_courses = []
        for course in courses:
            if self.is_enrolled(course):
                enrolled_courses.append(self.get_course_info(course))
        return enrolled_courses

    def initialize_page_and_get_user(self):
        """Add basic fields to template and return user."""
        self.template_value['course_info'] = (
            models_courses.COURSE_TEMPLATE_DICT)
        self.template_value['course_info']['course'] = {
            'locale': self.get_locale_for_user()}
        self.template_value['page_locale'] = 'en'
        user = users.get_current_user()
        if not user:
            self.template_value['loginUrl'] = users.create_login_url('/')
        else:
            self.template_value['email'] = user.email()
            self.template_value[
                'is_super_admin'] = roles.Roles.is_super_admin()
            self.template_value['can_view_spoc_admin'] = (
                spoc_roles.SPOCRoleManager.can_view())
            self.template_value['logoutUrl'] = users.create_logout_url('/')
        return user

    def is_valid_xsrf_token(self, action):
        """Asserts the current request has proper XSRF token or fails."""
        token = self.request.get('xsrf_token')
        return token and utils.XsrfTokenManager.is_xsrf_token_valid(
            token, action)

    def render(self, template_file):
        self.template_value['profiler_includes'] = templatetags.profiler_includes()
        template = jinja_utils.get_template(template_file, TEMPLATE_DIRS,
                                            self.get_locale_for_user())
        self.response.write(template.render(self.template_value))


class NullHtmlHooks(object):
    """Provide a non-null callback object for pages asking for hooks.

    In contexts where we have no single course to use to determine
    hook contents, we simply return blank content.
    """

    def insert(self, unused_name):
        return ''


class ProfileHandler(BaseStudentHandler, BaseProfileHandler, ReflectiveRequestHandler):
    """Global profile handler for a student."""

    default_action = 'show'
    get_actions = [ default_action, 'edit' ]
    post_actions = ['save_profile']

    def _storable_in_string_property(self, value):
        # db.StringProperty can hold 500B. len(1_unicode_char) == 1,
        # so len() is not a good proxy for unicode string size. Instead,
        # cast to utf-8-encoded str first.
        return len(value.encode('utf-8')) <= _STRING_PROPERTY_MAX_BYTES

    def get_show(self):
        """Handles GET requests."""
        if not settings.GCB_ENABLE_COURSE_EXPLORER_PAGE.value:
            self.error(404)
            return

        user = self.initialize_page_and_get_user()
        if not user:
            self.redirect('/')
            return

        profile = self.get_profile_for_user(user)
        if not profile:
            self.error(404)
            self.redirect('/')

        courses = self.get_public_courses()
        self.template_value['student'] = profile
        self.template_value['navbar'] = {'profile': True}
        self.template_value['courses'] = self.get_enrolled_courses(courses)
        self.template_value['html_hooks'] = NullHtmlHooks()
        self.template_value['student_preferences'] = {}

        self.fill_profile_data(profile)
        self.fill_local_chapter_data()

        self.template_value['make_reg_form_read_only'] = "yes"

        self.render('show_profile.html')

    def get_edit(self):
        if not settings.GCB_ENABLE_COURSE_EXPLORER_PAGE.value:
            self.error(404)
            return

        user = self.initialize_page_and_get_user()
        if not user:
            self.redirect('/')
            return

        profile = self.get_profile_for_user(user)
        if not profile:
            self.redirect('/')
            return

        self.template_value['student'] = profile

        self.fill_profile_data(profile)
        self.fill_local_chapter_data()

        self.template_value['xsrf_token'] = (
            utils.XsrfTokenManager.create_xsrf_token('save_profile'))

        self.template_value['navbar'] = {'profile': True}
        self.template_value['html_hooks'] = NullHtmlHooks()
        self.template_value['submit_button_name'] = 'Update Profile'
        self.template_value['force'] = self.request.get('force')
        self.render('edit_profile.html')

    def post_save_profile(self):
        """Handles post requests."""
        user = self.initialize_page_and_get_user()
        if not user:
            self.redirect('/')
            return

        profile = self.get_profile_for_user(user)
        if not profile:
            self.redirect('/')
            return

        accepted_terms = bool(self.request.get('terms'))
        accepted_honor = bool(self.request.get('honor_code'))
        if not accepted_honor or not accepted_terms:
            self.redirect('/profile?action=edit')
            return

        mobile_number = self.get_valid_mobile_number()
        if not mobile_number:
            self.redirect('/profile?action=edit')
            return

        self.update_profile_data(user, profile_only=True)
        self.redirect('/profile')



global_routes = [('/profile', ProfileHandler)]

namespaced_routes = []
