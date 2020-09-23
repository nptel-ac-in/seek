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

import course_explorer
import webapp2

import appengine_config
from common import jinja_utils
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
from modules.course_explorer import layout as page_layout
from modules.course_explorer import settings

from google.appengine.api import users

# We want to use views file in both /views and /modules/course_explorer/views.
TEMPLATE_DIRS = [
    os.path.join(appengine_config.BUNDLE_ROOT, 'views'),
    os.path.join(
        appengine_config.BUNDLE_ROOT, 'modules', 'course_explorer', 'views'),
]


# Int. Maximum number of bytes App Engine's db.StringProperty can store.
_STRING_PROPERTY_MAX_BYTES = 500


class IndexPageHandler(webapp2.RequestHandler):
    """Handles routing of root URL."""

    def get(self):
        """Handles GET requests."""
        if course_explorer.GCB_ENABLE_COURSE_EXPLORER_PAGE.value:
            self.redirect('/explorer')
            return

        index = sites.get_course_index()
        if index.get_all_courses():
            course = index.get_course_for_path('/')
            if not course:
                course = index.get_all_courses()[0]
            self.redirect(ApplicationHandler.canonicalize_url_for(
                course, '/course?use_last_location=true'))
        else:
            self.redirect('/admin/welcome')


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
        PageInitializerService.get().initialize(self.template_value)
        self.enrolled_courses_dict = {}
        self.courses_progress_dict = {}
        user = users.get_current_user()
        if not user:
            return

        profile = StudentProfileDAO.get_profile_by_user_id(user.user_id())
        if not profile:
            return

        self.template_value['register_xsrf_token'] = (
            XsrfTokenManager.create_xsrf_token('register-post'))

        self.enrolled_courses_dict = transforms.loads(profile.enrollment_info)
        if self.enrolled_courses_dict:
            self.template_value['has_enrolled_courses'] = True

        if profile.course_info:
            self.courses_progress_dict = transforms.loads(profile.course_info)

    def get_public_courses(self):
        """Get all the public courses."""
        public_courses = []
        for course in sites.get_all_courses():
            if ((course.now_available and Roles.is_user_allowlisted(course))
                or Roles.is_course_admin(course)):
                public_courses.append(course)
        return public_courses

    def get_listable_courses(self):
        """Get all the public courses."""
        listable_courses = []
        for course in self.get_public_courses():
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
        self.template_value['course_info'] = Courses.COURSE_TEMPLATE_DICT
        self.template_value['course_info']['course'] = {
            'locale': self.get_locale_for_user()}
        user = users.get_current_user()
        if not user:
            self.template_value['loginUrl'] = users.create_login_url('/')
        else:
            self.template_value['email'] = user.email()
            self.template_value['is_super_admin'] = Roles.is_super_admin()
            self.template_value['logoutUrl'] = users.create_logout_url('/')
        return user

    def is_valid_xsrf_token(self, action):
        """Asserts the current request has proper XSRF token or fails."""
        token = self.request.get('xsrf_token')
        return token and XsrfTokenManager.is_xsrf_token_valid(token, action)

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

    def get_show(self):
        """Handles GET requests."""
        if not course_explorer.GCB_ENABLE_COURSE_EXPLORER_PAGE.value:
            self.error(404)
            return

        user = self.initialize_page_and_get_user()
        if not user:
            self.redirect('/explorer')
            return

        profile = self.get_profile_for_user(user)

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
        if not course_explorer.GCB_ENABLE_COURSE_EXPLORER_PAGE.value:
            self.error(404)
            return

        user = self.initialize_page_and_get_user()
        if not user:
            self.redirect('/explorer')
            return

        profile = self.get_profile_for_user(user)
        if not profile:
            self.redirect('/explorer')
            return

        self.template_value['student'] = profile

        self.fill_profile_data(profile)
        self.fill_local_chapter_data()

        self.template_value['xsrf_token'] = (
            XsrfTokenManager.create_xsrf_token('save_profile'))

        self.template_value['navbar'] = {'profile': True}
        self.template_value['html_hooks'] = NullHtmlHooks()
        self.template_value['submit_button_name'] = 'Update Profile'
        self.template_value['force'] = self.request.get('force')
        self.render('edit_profile.html')

    def post_save_profile(self):
        """Handles post requests."""
        user = self.initialize_page_and_get_user()
        if not user:
            self.redirect('/explorer')
            return

        profile = self.get_profile_for_user(user)
        if not profile:
            self.redirect('/explorer')
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
        self.redirect('/explorer/profile')


def setSortStatus(c1):
    if c1.is_registered:
        c1.order = 3
    elif c1.is_completed:
        c1.order = 4
    elif c1.can_register:
        c1.order = 0
    elif c1.registration == 'OPENING_SOON':
        c1.order = 1
    elif c1.browsable:
        c1.order = 2
    elif c1.registration == 'CLOSED':
        c1.order = 5
    else:
        c1.order = 6


class SearchCourseHandler(BaseStudentHandler):
    """Handles list of courses that can be viewed by a student."""

    def get(self):
        """Handles GET requests."""
        category_key = self.request.get('category')
        category_name = ''
        category_list = course_category.CourseCategoryDAO.get_category_list()
        category_defs = dict()
        category_menu_list = dict()
        for categ in category_list:
            category_defs[categ.category] = categ.description
            if categ.visible:
                category_menu_list[categ.category] = categ.description

        if category_key in category_defs:
            category_name = category_defs[category_key]
        elif category_key == 'all':
            category_name = 'All'
        else:
            self.error(404)
            return

        user = self.initialize_page_and_get_user()
        self.template_value['show_registration_page'] = True
        if user is not None:
             profile = self.get_profile_for_user(user)
             if profile is not None:
                 self.template_value['show_registration_page'] = False


        listable_courses = self.get_listable_courses()
        course_by_search_filter = []

        for course in listable_courses:
            if (course.category == category_key or category_key == 'all') \
                            and course.category in category_menu_list.keys():
                course.course_preview_url = course.course_preview_url
                course.is_registered = self.is_enrolled(course)
                course.is_completed = self.is_completed(course)
                setSortStatus(course)
                course_by_search_filter.append(course)

        #sort the category_menu_list
        category_menu_list_ordered = OrderedDict(sorted(category_menu_list.items(), key=lambda t: t[1]))


        self.template_value['category_key'] = category_key
        self.template_value['category_name'] = category_name
        self.template_value['category_menu_list'] = category_menu_list_ordered
        self.template_value['course_by_search_filter'] = course_by_search_filter
        self.template_value['html_hooks'] = NullHtmlHooks()
        self.template_value['navbar'] = {'course_explorer': True, 'search_course':True }
        self.render('search_course.html')


class AllCoursesHandler(BaseStudentHandler):
    """Handles list of courses that can be viewed by a student."""

    def get(self):
        """Handles GET requests."""

        # if not course_explorer.GCB_ENABLE_COURSE_EXPLORER_PAGE.value:
        #     self.error(404)
        #     return

        user = self.initialize_page_and_get_user()
        self.template_value['show_registration_page'] = True
        if user is not None:
             profile = self.get_profile_for_user(user)
             if profile is not None:
                 self.template_value['show_registration_page'] = False
        self.template_value['explorer'] = True

        listable_courses = self.get_listable_courses()
        allowlisted_courses = []
        featured_courses = []

        layout = page_layout.ExplorerLayoutDAO.get_layout()
        category_order = layout.category_order

        category_list = course_category.CourseCategoryDAO.get_category_list()
        category_defs = dict()
        category_menu_list = dict()
        for categ in category_list:
            category_defs[categ.category] = categ.description
            if categ.visible:
                category_menu_list[categ.category] = categ.description

        course_groups = dict()
        for co in category_order:
            if co in category_defs.keys():
                course_groups[co] = []


        featured_courses_can_register = []
        featured_courses_others = []
        for course in listable_courses:
            course.course_preview_url = course.course_preview_url
            course.is_registered = self.is_enrolled(course)
            course.is_completed = self.is_completed(course)
            if course.allowlist.strip():
                allowlisted_courses.append(course)
            elif course.category in course_groups.keys():
                course_groups[course.category].append(course)
                if course.featured:
                    setSortStatus(course)
                    featured_courses.append(course)
            else:
                continue

        #shuffle the fetaured courses
        random.shuffle(featured_courses)

        #sort the category_menu_list
        category_menu_list_ordered = OrderedDict(
             sorted(category_menu_list.items(), key=lambda t: t[1]))

        if allowlisted_courses:
            self.template_value['allowlisted_courses'] = allowlisted_courses
        self.template_value['layout'] = layout
        self.template_value['category_defs'] = category_defs
        self.template_value['category_menu_list'] = category_menu_list_ordered
        self.template_value['course_groups'] = course_groups
        self.template_value['featured_courses'] = featured_courses
        self.template_value['html_hooks'] = NullHtmlHooks()
        self.template_value['navbar'] = {'course_explorer': True}
        self.render('course_explorer.html')

class RegisteredCoursesHandler(BaseStudentHandler):
    """Handles registered courses view for a student."""

    def get(self):
        """Handles GET request."""

        if not course_explorer.GCB_ENABLE_COURSE_EXPLORER_PAGE.value:
            self.error(404)
            return

        user = self.initialize_page_and_get_user()
        courses = self.get_public_courses()
        self.template_value['show_registration_page'] = True
        if user is not None:
             profile = self.get_profile_for_user(user)
             if profile is not None:
                 self.template_value['show_registration_page'] = False

        layout = page_layout.ExplorerLayoutDAO.get_layout()
        category_order = layout.category_order

        category_list = course_category.CourseCategoryDAO.get_category_list()
        category_defs = dict()
        for categ in category_list:
            category_defs[categ.category] = categ.description

        course_groups = dict()
        for co in category_order:
            if co in category_defs.keys():
                course_groups[co] = []

        enrolled_courses = self.get_enrolled_courses(courses)
        allowlisted_courses = []
        for course in enrolled_courses:
            if course.allowlist.strip():
                allowlisted_courses.append(course)
            elif course.category in course_groups.keys():
                course_groups[course.category].append(course)
            else:
                continue

        if allowlisted_courses:
            self.template_value['allowlisted_courses'] = allowlisted_courses
        self.template_value['category_defs'] = category_defs
        self.template_value['course_groups'] = course_groups
        self.template_value['layout'] = layout
        self.template_value['navbar'] = {'mycourses': True}
        self.template_value['can_enroll_more_courses'] = (
            len(courses) - len(enrolled_courses) > 0)
        self.template_value['html_hooks'] = NullHtmlHooks()
        self.template_value['student_preferences'] = {}
        self.render('course_explorer.html')


class AssetsHandler(webapp2.RequestHandler):
    """Handles asset file for the home page."""

    def get_mime_type(self, filename, default='application/octet-stream'):
        guess = mimetypes.guess_type(filename)[0]
        if guess is None:
            return default
        return guess

    def get(self, path):
        #TODO THEJ - You may want to uncomment this
        """Handles GET requests."""
        # if not course_explorer.GCB_ENABLE_COURSE_EXPLORER_PAGE.value:
        #     self.error(404)
        #     return

        filename = '%s/assets/%s' % (appengine_config.BUNDLE_ROOT, path)
        with open(filename, 'r') as f:
            self.response.headers['Content-Type'] = self.get_mime_type(filename)
            self.response.write(f.read())
