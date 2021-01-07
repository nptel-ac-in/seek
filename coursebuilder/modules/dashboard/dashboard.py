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

"""Classes and methods to create and manage Courses."""

__author__ = 'Pavel Simakov (psimakov@google.com)'

import collections
import datetime
import logging
import os
import urllib
import uuid

import appengine_config
from gae_mini_profiler import templatetags

#from modules.courses.admin_preferences_editor import AdminPreferencesEditor
#from modules.courses.admin_preferences_editor import AdminPreferencesRESTHandler
#from modules.courses.settings import CourseSettingsDisplayHelper
#from modules.courses.settings import CourseSettingsHandler
#from modules.courses.settings import CourseSettingsRESTHandler
#from modules.courses.settings import HtmlHookHandler
#from modules.courses.settings import HtmlHookRESTHandler
from filer import AssetItemRESTHandler
from filer import FileManagerAndEditor
from filer import FilesItemRESTHandler
from filer import TextAssetRESTHandler
from label_editor import LabelManagerAndEditor, TrackManagerAndEditor
from label_editor import LabelRestHandler, TrackRestHandler
import messages
from question_editor import GeneralQuestionRESTHandler
from question_editor import GiftQuestionRESTHandler
from question_editor import McQuestionRESTHandler
from question_editor import QuestionManagerAndEditor
from question_editor import SaQuestionRESTHandler
from question_group_editor import QuestionGroupManagerAndEditor
from question_group_editor import QuestionGroupRESTHandler
from role_editor import RoleManagerAndEditor
from role_editor import RoleRESTHandler

import utils as dashboard_utils

from common import crypto
from common import jinja_utils
from common import safe_dom
from common import tags
from common import users
from common.utils import Namespace
from controllers import sites
from controllers.utils import ApplicationHandler
from controllers.utils import CourseHandler
from controllers.utils import ReflectiveRequestHandler
from models import config
from models import custom_modules
from models import roles
from models import services
from models.models import RoleDAO
from common import menus

from google.appengine.api import app_identity

custom_module = None

TEMPLATE_DIR = os.path.join(
    appengine_config.BUNDLE_ROOT, 'modules', 'dashboard', 'templates')


class DashboardHandler(
    CourseHandler, FileManagerAndEditor,
    LabelManagerAndEditor, TrackManagerAndEditor, QuestionGroupManagerAndEditor,
    QuestionManagerAndEditor, ReflectiveRequestHandler, RoleManagerAndEditor):
    """Handles all pages and actions required for managing a course."""

    # This dictionary allows the dashboard module to optionally nominate a
    # specific sub-tab within each major tab group as the default sub-tab to
    # open when first navigating to that major tab.  The default may be
    # explicitly specified here so that sub-tab registrations from other
    # modules do not inadvertently take over the first position due to order
    # of module registration.
    default_subtab_action = collections.defaultdict(lambda: None)
    get_actions = [
        'edit_settings', 'edit_unit_lesson',
        'manage_asset', 'manage_text_asset',
        'add_mc_question', 'add_sa_question',
        'edit_question', 'add_question_group', 'edit_question_group',
        'question_preview', 'question_group_preview',
        'add_label', 'edit_label', 'add_track', 'edit_track',
        'add_role', 'edit_role',
        'import_gift_questions']
    # Requests to these handlers automatically go through an XSRF token check
    # that is implemented in ReflectiveRequestHandler.
    post_actions = [
        'create_or_edit_settings',
        'add_to_question_group',
        'clone_question']
    child_routes = [
            (AssetItemRESTHandler.URI, AssetItemRESTHandler),
            (FilesItemRESTHandler.URI, FilesItemRESTHandler),
            (LabelRestHandler.URI, LabelRestHandler),
            (TrackRestHandler.URI, TrackRestHandler),
            (McQuestionRESTHandler.URI, McQuestionRESTHandler),
            (GiftQuestionRESTHandler.URI, GiftQuestionRESTHandler),
            (SaQuestionRESTHandler.URI, SaQuestionRESTHandler),
            (GeneralQuestionRESTHandler.URI, GeneralQuestionRESTHandler),
            (TextAssetRESTHandler.URI, TextAssetRESTHandler),
            (QuestionGroupRESTHandler.URI, QuestionGroupRESTHandler),
            (RoleRESTHandler.URI, RoleRESTHandler)]

    # List of functions which are used to generate content displayed at the top
    # of every dashboard page. Use this with caution, as it is extremely
    # invasive of the UX. Each function receives the handler as arg and returns
    # an object to be inserted into a Jinja template (e.g. a string, a safe_dom
    # Node or NodeList, or a jinja2.Markup).
    PAGE_HEADER_HOOKS = []

    # A list of hrefs for extra CSS files to be included in dashboard pages.
    # Files listed here by URL will be available on every Dashboard page.
    EXTRA_CSS_HREF_LIST = []

    # A list of hrefs for extra JS files to be included in dashboard pages.
    # Files listed here by URL will be available on every Dashboard page.
    EXTRA_JS_HREF_LIST = []

    # A list of template locations to be included in dashboard pages
    ADDITIONAL_DIRS = []

    # Link URL
    LINK_URL = 'dashboard'

    # Dictionary that maps external permissions to their descriptions
    _external_permissions = {}
    # Dictionary that maps actions to permissions
    _get_action_to_permission = {}
    _post_action_to_permission = {}

    default_action = None
    GetAction = collections.namedtuple('GetAction', ['handler', 'in_action'])
    _custom_get_actions = {}  # Map of name to GetAction
    _custom_post_actions = {}  # Map of name to handler callback.

    # Create top level menu groups which other modules can register against.
    # I would do this in "register", but other modules register first.
    actions_to_menu_items = {}
    root_menu_group = menus.MenuGroup('dashboard', 'Dashboard')

    @classmethod
    def add_nav_mapping(cls, name, title, **kwargs):
        """Create a top level nav item."""
        menu_item = cls.root_menu_group.get_child(name)
        if menu_item is None:
            is_link = kwargs.get('href')
            menu_cls = menus.MenuItem if is_link else menus.MenuGroup
            menu_item = menu_cls(
                name, title, group=cls.root_menu_group, **kwargs)
            if not is_link:
                # create the basic buckets
                pinned = menus.MenuGroup(
                    'pinned', None, placement=1000, group=menu_item)
                default = menus.MenuGroup(
                    'default', None, placement=2000, group=menu_item)
                advanced = menus.MenuGroup(
                    'advanced', None,
                    placement=menus.MenuGroup.DEFAULT_PLACEMENT * 2,
                    group=menu_item)
        return menu_item

    @classmethod
    def get_nav_title(cls, action):
        item = cls.actions_to_menu_items.get(action)
        if item:
            return item.group.group.title + " > " + item.title
        else:
            return None

    @classmethod
    def add_sub_nav_mapping(
            cls, group_name, item_name, title, action=None, contents=None,
            can_view=None, href=None, no_app_context=False,
            sub_group_name=None, **kwargs):
        """Create a second level nav item.

        Args:
            group_name: Name of an existing top level nav item to use as the
                parent
            item_name: A unique key for this item
            title: Human-readable label
            action: A unique operation ID for
            contents: A handler which will be added as a custom get-action on
                DashboardHandler
            can_view: Pass a boolean function here if your handler has
                additional permissions logic in it that the dashboard does not
                check for you.  You must additionally check it in your handler.
            sub_group_name: The sub groups 'pinned', 'default', and 'advanced'
                exist in that order and 'default' is used by default.  You can
                pass some other string to create a new group at the end.
            other arguments: see common/menus.py
        """

        group = cls.root_menu_group.get_child(group_name)
        if group is None:
            logging.critical('The group %s does not exist', group_name)
            return

        if sub_group_name is None:
            sub_group_name = 'default'

        sub_group = group.get_child(sub_group_name)
        if not sub_group:
            sub_group = menus.MenuGroup(
                sub_group_name, None, group=group)

        item = sub_group.get_child(item_name)
        if item:
            logging.critical(
                'There is already a sub-menu item named "%s" registered in '
                'group %s subgroup %s.', item_name, group_name, sub_group_name)
            return

        if contents:
            action = action or group_name + '_' + item_name

        if action and not href:
            href = "{0}?action={1}".format(cls.LINK_URL, action)

        def combined_can_view(app_context):
            if action:
                # Current design disallows actions at the global level.
                # This might change in the future.
                if not app_context and not no_app_context:
                    return False

                # Check permissions in the dashboard
                if cls.can_view(action, app_context=app_context):
                    return True

            # Additional custom visibility check
            if can_view and can_view(app_context):
                return True

            return False

        item = menus.MenuItem(
            item_name, title, action=action, group=sub_group,
            can_view=combined_can_view, href=href, **kwargs)
        cls.actions_to_menu_items[action] = item

        if contents:
            cls.add_custom_get_action(action, handler=contents)

    @classmethod
    def add_custom_get_action(cls, action, handler=None, in_action=None,
                              overwrite=False):
        if not action:
            logging.critical('Action not specified. Ignoring.')
            return False

        if not handler:
            logging.critical(
                'For action : %s handler can not be null.', action)
            return False

        if ((action in cls._custom_get_actions or action in cls.get_actions)
            and not overwrite):
            logging.critical(
                'action : %s already exists. Ignoring the custom get action.',
                action)
            return False

        cls._custom_get_actions[action] = cls.GetAction(handler, in_action)
        return True

    @classmethod
    def remove_custom_get_action(cls, action):
        if action in cls._custom_get_actions:
            cls._custom_get_actions.pop(action)

    @classmethod
    def add_custom_post_action(cls, action, handler, overwrite=False):
        if not handler or not action:
            logging.critical('Action or handler can not be null.')
            return False

        if ((action in cls._custom_post_actions or action in cls.post_actions)
            and not overwrite):
            logging.critical(
                'action : %s already exists. Ignoring the custom post action.',
                action)
            return False

        cls._custom_post_actions[action] = handler
        return True

    @classmethod
    def remove_custom_post_action(cls, action):
        if action in cls._custom_post_actions:
            cls._custom_post_actions.pop(action)

    @classmethod
    def get_child_routes(cls):
        """Add child handlers for REST."""
        return cls.child_routes

    @classmethod
    def can_view(cls, action, app_context=None):
        """Checks if current user has viewing rights."""
        if not app_context:
            app_context = sites.get_app_context_for_current_request()
        if not app_context:
            return False
        if action in cls._get_action_to_permission:
            return cls._get_action_to_permission[action](app_context)
        return roles.Roles.is_course_admin(app_context)

    @classmethod
    def can_edit(cls, action):
        """Checks if current user has editing rights."""
        app_context = sites.get_app_context_for_current_request()
        if action in cls._post_action_to_permission:
            return cls._post_action_to_permission[action](app_context)
        return roles.Roles.is_course_admin(app_context)

    def default_action_for_current_permissions(self):
        """Set the default or first active navigation tab as default action."""
        item = self.root_menu_group.first_visible_item(self.app_context)
        if item:
            return item.action

    def get(self):
        """Enforces rights to all GET operations."""
        action = self.request.get('action')
        if not action:
            self.default_action = self.default_action_for_current_permissions()
            action = self.default_action
        self.action = action

        if not self.can_view(action, app_context=self.app_context):
            self.redirect(self.app_context.get_slug())
            return

        if action in self._custom_get_actions:
            result = self._custom_get_actions[action].handler(self)
            if result is None:
                return

            # The following code handles pages for actions that do not write out
            # their responses.

            template_values = {
                'page_title': self.format_title(self.get_nav_title(action)),
            }
            if isinstance(result, dict):
                template_values.update(result)
            else:
                template_values['main_content'] = result

            self.render_page(template_values)
            return


        # Force reload of properties. It is expensive, but admin deserves it!
        config.Registry.get_overrides(force_update=True)
        return super(DashboardHandler, self).get()

    def post(self):
        """Enforces rights to all POST operations."""
        action = self.request.get('action')
        self.action = action
        if not self.can_edit(action):
            self.redirect(self.app_context.get_slug())
            return
        if action in self._custom_post_actions:
            # Each POST request must have valid XSRF token.
            xsrf_token = self.request.get('xsrf_token')
            if not crypto.XsrfTokenManager.is_xsrf_token_valid(
                xsrf_token, action):
                self.error(403)
                return
            self._custom_post_actions[action](self)
            return

        return super(DashboardHandler, self).post()

    def get_template(self, template_name, dirs=None):
        """Sets up an environment and Gets jinja template."""
        return jinja_utils.get_template(
            template_name, (dirs or []) + [TEMPLATE_DIR], handler=self)

    def get_alerts(self):
        alerts = []
        if not self.app_context.is_editable_fs():
            alerts.append('Read-only course.')
        if not self.app_context.now_available:
            alerts.append('The course is not publicly available.')
        return '\n'.join(alerts)

    def _get_current_menu_action(self):
        registered_action = self._custom_get_actions.get(self.action)
        if registered_action:
            registered_in_action = registered_action.in_action
            if registered_in_action:
                return registered_in_action

        return self.action

    def render_page(self, template_values, in_action=None):
        """Renders a page using provided template values."""
        template_values['header_title'] = template_values['page_title']
        template_values['page_headers'] = [
            hook(self) for hook in self.PAGE_HEADER_HOOKS]
        template_values['course_title'] = self.app_context.get_title()

        current_action = in_action or self._get_current_menu_action()

        template_values['current_menu_item'] = self.actions_to_menu_items.get(
            current_action)
        template_values['courses_menu_item'] = self.actions_to_menu_items.get(
            'courses')
        template_values['root_menu_group'] = self.root_menu_group

        include_closed_raw = self.request.get('include_closed', "no")
        include_closed = include_closed_raw == "yes"
        if include_closed:
            template_values['include_closed'] = include_closed_raw
        template_values['course_app_contexts'] = get_visible_courses(
            include_closed=include_closed)

        template_values['app_context'] = self.app_context
        template_values['current_course'] = self.get_course()
        template_values['gcb_course_base'] = self.get_base_href(self)
        template_values['user_nav'] = safe_dom.NodeList().append(
            safe_dom.Text('%s | ' % users.get_current_user().email())
        ).append(
            safe_dom.Element(
                'a', href=users.create_logout_url(self.request.uri)
            ).add_text('Logout'))
        template_values[
            'page_footer'] = 'Page created on: %s' % datetime.datetime.now()
        template_values['coursebuilder_version'] = (
            os.environ['GCB_PRODUCT_VERSION'])
        template_values['application_id'] = app_identity.get_application_id()
        version = os.environ['CURRENT_VERSION_ID']
        if '.' not in version or not appengine_config.PRODUCTION_MODE:
            template_values['application_version'] = version
        else:
            version, deployed_at = version.split('.', 1)
            template_values['application_version'] = version
            template_values['deployed_at'] = datetime.datetime.utcfromtimestamp(
                int(deployed_at) >> 28)  # Yes, really.

        template_values['extra_css_href_list'] = self.EXTRA_CSS_HREF_LIST
        template_values['extra_js_href_list'] = self.EXTRA_JS_HREF_LIST
        template_values['powered_by_url'] = services.help_urls.get(
            'dashboard:powered_by')
        if not template_values.get('sections'):
            template_values['sections'] = []
        if not appengine_config.PRODUCTION_MODE:
            template_values['page_uuid'] = str(uuid.uuid1())

        template_values['profiler_includes'] = templatetags.profiler_includes()

        self.response.write(
            self.get_template('view.html').render(template_values))

    @classmethod
    def register_courses_menu_item(cls, menu_item):
        cls.actions_to_menu_items['courses'] = menu_item

    def format_title(self, text):
        """Formats standard title with or without course picker."""
        ret = safe_dom.NodeList()
        cb_text = 'Course Builder '
        ret.append(safe_dom.Text(cb_text))
        ret.append(safe_dom.Entity('&gt;'))
        ret.append(safe_dom.Text(' %s ' % self.app_context.get_title()))
        ret.append(safe_dom.Entity('&gt;'))
        dashboard_text = ' Dashboard '
        ret.append(safe_dom.Text(dashboard_text))
        ret.append(safe_dom.Entity('&gt;'))
        ret.append(safe_dom.Text(' %s' % text))
        return ret

    # def _render_course_outline_to_html(self, course):
    #     """Renders course outline to HTML."""

    #     units = []
    #     for unit in course.get_units():
    #         if course.get_parent_unit(unit.unit_id):
    #             continue  # Will be rendered as part of containing element.
    #         if unit.type == verify.UNIT_TYPE_ASSESSMENT:
    #             continue  # Will be rendered as part of containing unit
    #         elif unit.type == verify.UNIT_TYPE_LINK:
    #             continue # Will be rendered as part of parent element.
    #         elif unit.type == verify.UNIT_TYPE_UNIT:
    #             units.append(self._render_unit_outline(course, unit))
    #         elif unit.type == verify.UNIT_TYPE_CUSTOM:
    #             continue # Will be rendered as part of parent element.
    #         else:
    #             raise Exception('Unknown unit type: %s.' % unit.type)

    #     template_values = {
    #         'course': {
    #             'title': course.title,
    #             'is_editable': self.app_context.is_editable_fs(),
    #             'availability': {
    #                 'url': self.get_action_url('course_availability'),
    #                 'xsrf_token': self.create_xsrf_token('course_availability'),
    #                 'param': not self.app_context.now_available,
    #                 'class': (
    #                     'reveal-on-hover icon md md-lock-open'
    #                     if self.app_context.now_available else
    #                     'reveal-on-hover icon md md-lock')
    #             }
    #         },
    #         'units': units,
    #         'add_lesson_xsrf_token': self.create_xsrf_token('add_lesson'),
    #         'status_xsrf_token': self.create_xsrf_token('set_draft_status'),
    #         'unit_lesson_title_xsrf_token': self.create_xsrf_token(
    #             UnitLessonTitleRESTHandler.XSRF_TOKEN),
    #         'unit_title_template': resources_display.get_unit_title_template(
    #             course.app_context),
    #         'extra_info_title': ', '.join(self.COURSE_OUTLINE_EXTRA_INFO_TITLES)
    #     }
    #     return jinja2.Markup(
    #         self.get_template(
    #             'course_outline.html', []).render(template_values))

    # def _render_status_icon(self, resource, key, component_type):
    #     if not hasattr(resource, 'now_available'):
    #         return
    #     icon = safe_dom.Element(
    #         'div', data_key=str(key), data_component_type=component_type)
    #     common_classes = 'reveal-on-hover icon icon-draft-status md'
    #     if not self.app_context.is_editable_fs():
    #         common_classes += ' inactive'
    #     if resource.now_available:
    #         icon.add_attribute(
    #             alt=resources_display.PUBLISHED_TEXT,
    #             title=resources_display.PUBLISHED_TEXT,
    #             className=common_classes + ' md-lock-open',
    #         )
    #     else:
    #         icon.add_attribute(
    #             alt=resources_display.DRAFT_TEXT,
    #             title=resources_display.DRAFT_TEXT,
    #             className=common_classes + ' md-lock'
    #         )
    #     return icon

    # def _render_assessment_outline(self, unit):
    #     actions = []
    #     unit_data = {
    #         'title': unit.title,
    #         'class': 'assessment',
    #         'href': 'assessment?name=%s' % unit.unit_id,
    #         'unit_id': unit.unit_id,
    #         'actions': actions
    #     }

    #     actions.append(self._render_status_icon(unit, unit.unit_id, 'unit'))
    #     if self.app_context.is_editable_fs():
    #         url = self.canonicalize_url(
    #             '/dashboard?%s') % urllib.urlencode({
    #                 'action': 'edit_assessment',
    #                 'key': unit.unit_id})
    #         actions.append(self._create_edit_button_for_course_outline(url))

    #     return unit_data

    # def _render_link_outline(self, unit):
    #     actions = []
    #     unit_data = {
    #         'title': unit.title,
    #         'class': 'link',
    #         'href': unit.href or '',
    #         'unit_id': unit.unit_id,
    #         'actions': actions
    #     }
    #     actions.append(self._render_status_icon(unit, unit.unit_id, 'unit'))
    #     if self.app_context.is_editable_fs():
    #         url = self.canonicalize_url(
    #             '/dashboard?%s') % urllib.urlencode({
    #                 'action': 'edit_link',
    #                 'key': unit.unit_id})
    #         actions.append(self._create_edit_button_for_course_outline(url))
    #     return unit_data

    # def _render_custom_unit_outline(self, course, unit):
    #     actions = []
    #     unit_data = {
    #         'title': unit.title,
    #         'class': 'custom-unit',
    #         'href': unit.custom_unit_url,
    #         'unit_id': unit.unit_id,
    #         'actions': actions
    #     }
    #     actions.append(self._render_status_icon(unit, unit.unit_id, 'unit'))
    #     if self.app_context.is_editable_fs():
    #         url = self.canonicalize_url(
    #             '/dashboard?%s') % urllib.urlencode({
    #                 'action': 'edit_custom_unit',
    #                 'key': unit.unit_id,
    #                 'unit_type': unit.custom_unit_type})
    #         actions.append(self._create_edit_button_for_course_outline(url))
    #     return unit_data

    # def _render_unit_outline(self, course, unit):
    #     is_editable = self.app_context.is_editable_fs()

    #     actions = []
    #     unit_data = {
    #         'title': unit.title,
    #         'class': 'unit',
    #         'href': 'unit?unit=%s' % unit.unit_id,
    #         'unit_id': unit.unit_id,
    #         'actions': actions
    #     }

    #     actions.append(self._render_status_icon(unit, unit.unit_id, 'unit'))
    #     if is_editable:
    #         url = self.canonicalize_url(
    #             '/dashboard?%s') % urllib.urlencode({
    #                 'action': 'edit_unit',
    #                 'key': unit.unit_id})
    #         actions.append(self._create_edit_button_for_course_outline(url))

    #     if unit.pre_assessment:
    #         assessment = course.find_unit_by_id(unit.pre_assessment)
    #         if assessment:
    #             assessment_outline = self._render_assessment_outline(assessment)
    #             assessment_outline['class'] = 'pre-assessment'
    #             unit_data['pre_assessment'] = assessment_outline

    #     lessons = []
    #     for lesson in course.get_lessons(unit.unit_id):
    #         actions = []
    #         actions.append(
    #             self._render_status_icon(lesson, lesson.lesson_id, 'lesson'))
    #         if is_editable:
    #             url = self.get_action_url(
    #                 'edit_lesson', key=lesson.lesson_id)
    #             actions.append(self._create_edit_button_for_course_outline(url))

    #         extras = []
    #         for annotator in self.COURSE_OUTLINE_EXTRA_INFO_ANNOTATORS:
    #             extra_info = annotator(course, lesson)
    #             if extra_info:
    #                 extras.append(extra_info)

    #         lessons.append({
    #             'title': lesson.title,
    #             'class': 'lesson',
    #             'href': 'unit?unit=%s&lesson=%s' % (
    #                 unit.unit_id, lesson.lesson_id),
    #             'lesson_id': lesson.lesson_id,
    #             'actions': actions,
    #             'auto_index': lesson.auto_index,
    #             'extras': extras})

    #     unit_data['lessons'] = lessons

    #     if unit.post_assessment:
    #         assessment = course.find_unit_by_id(unit.post_assessment)
    #         if assessment:
    #             assessment_outline = self._render_assessment_outline(assessment)
    #             assessment_outline['class'] = 'post-assessment'
    #             unit_data['post_assessment'] = assessment_outline

    #     sub_units = course.get_subunits(unit.unit_id)
    #     if sub_units:
    #         sub_unit_rendered = []
    #         for sub_unit in sub_units:
    #             if sub_unit.type == verify.UNIT_TYPE_LINK:
    #                 sub_unit_rendered.append(self._render_link_outline(sub_unit))
    #             elif sub_unit.type == verify.UNIT_TYPE_CUSTOM:
    #                 sub_unit_rendered.append(self._render_custom_unit_outline(course, sub_unit))
    #             elif sub_unit.type == verify.UNIT_TYPE_ASSESSMENT:
    #                 if unit.post_assessment == sub_unit.unit_id or unit.pre_assessment == sub_unit.unit_id:
    #                     continue #pre and post are handled as a special case
    #                 else:
    #                     assessment_outline = self._render_assessment_outline(sub_unit)
    #                     assessment_outline['class'] = 'post-assessment'
    #                     sub_unit_rendered.append(assessment_outline)

    #         unit_data['sub_units']=sub_unit_rendered
    #     return unit_data

    # def get_question_preview(self):
    #     template_values = {}
    #     template_values['gcb_course_base'] = self.get_base_href(self)
    #     template_values['question'] = tags.html_to_safe_dom(
    #         '<question quid="%s">' % self.request.get('quid'), self)
    #     self.response.write(self.get_template(
    #         'question_preview.html', []).render(template_values))

    # def custom_post_handler(self):
    #     """Edit Custom Unit Settings view."""
    #     action = self.request.get('action')
    #     self._custom_post_actions[action](self)

    def get_action_url(self, action, key=None, extra_args=None, fragment=None):
        args = {'action': action}
        if key:
            args['key'] = key
        if extra_args:
            args.update(extra_args)
        url = '/%s?%s' % (self.LINK_URL, urllib.urlencode(args))
        if fragment:
            url += '#' + fragment
        return self.canonicalize_url(url)

    # def get_settings(self):
    #     # tab = tabs.Registry.get_tab(
    #     #     'settings', self.request.get('tab') or 'course')
    #     template_values = {
    #         'page_title': self.format_title('Settings > %s' % "tab.title"),
    #         'page_description': messages.SETTINGS_DESCRIPTION,
    #     }
    #     # exit_url = self.request.get('exit_url')
    #     # if tab.name == 'admin_prefs':
    #     #     self._edit_admin_preferences(template_values, '')
    #     # elif tab.name == 'advanced':
    #     #     self._get_settings_advanced(template_values, tab)
    #     # elif tab.name == 'about':
    #     #     self._get_about_course(template_values, tab)
    #     # else:
    #     #     self._show_edit_settings_section(
    #     #         template_values, '/course.yaml', tab.name, tab.title,
    #     #         tab.contents, exit_url)
    #     self.render_page(template_values)

    # def get_settings_section(self, template_values, tab):
    #     actions = []
    #     if self.app_context.is_editable_fs():
    #         actions.append({
    #             'id': 'edit_course_settings',
    #             'caption': 'Edit Settings',
    #             'action': self.get_action_url(
    #                 'edit_course_settings',
    #                 extra_args={
    #                     'section_names': tab.contents,
    #                     'tab': tab.name,
    #                     'tab_title': tab.title,
    #                     }),
    #             'xsrf_token': self.create_xsrf_token('edit_course_settings')})
    #     template_values['sections'] = [{
    #         'title': 'Course Settings',
    #         'actions': actions,
    #         'pre': ' ',
    #         }]

    #     course = self.get_course()
    #     environ = course.get_environ(self.app_context)
    #     display_dict = (course
    #                     .create_settings_schema()
    #                     .clone_only_items_named(tab.contents.split(','))
    #                     .get_display_dict())
    #     main_content = safe_dom.NodeList()
    #     for registry in display_dict['registries']:
    #         main_content.append(
    #                 CourseSettingsDisplayHelper.build_settings_section(
    #                     registry, environ))
    #     template_values['main_content'] = main_content

    # def get_settings_admin_prefs(self, template_values, tab):
    #     actions = []
    #     # Admin prefs setup.
    #     if self.app_context.is_editable_fs():
    #         actions.append({
    #             'id': 'edit_admin_prefs',
    #             'caption': 'Edit Prefs',
    #             'action': self.get_action_url(
    #                 'edit_admin_preferences',
    #                 extra_args={
    #                     'tab': tab.name,
    #                     'tab_title': tab.title,
    #                     }),
    #             'xsrf_token': self.create_xsrf_token('edit_admin_preferences')})
    #     admin_prefs_info = []
    #     admin_prefs = models.StudentPreferencesDAO.load_or_create()
    #     admin_prefs_info.append('Show hook edit buttons: %s' %
    #                             admin_prefs.show_hooks)
    #     admin_prefs_info.append('Show jinja context: %s' %
    #                             admin_prefs.show_jinja_context)

    #     template_values['sections'] = [
    #         {
    #             'title': 'Preferences',
    #             'description': messages.ADMIN_PREFERENCES_DESCRIPTION,
    #             'actions': actions,
    #             'children': admin_prefs_info},
    #         ]

    # def text_file_to_safe_dom(self, reader, content_if_empty):
    #     """Load text file and convert it to safe_dom tree for display."""
    #     info = []
    #     if reader:
    #         lines = reader.read().decode('utf-8')
    #         for line in lines.split('\n'):
    #             if not line:
    #                 continue
    #             pre = safe_dom.Element('pre')
    #             pre.add_text(line)
    #             info.append(pre)
    #     else:
    #         info.append(content_if_empty)
    #     return info

    # def text_file_to_string(self, reader, content_if_empty):
    #     """Load text file and convert it to string for display."""
    #     if reader:
    #         return reader.read().decode('utf-8')
    #     else:
    #         return content_if_empty

    # def _get_settings_advanced(self, template_values, tab):
    #     """Renders course settings view."""

    #     actions = []
    #     if self.app_context.is_editable_fs():
    #         actions.append({
    #             'id': 'edit_course_yaml',
    #             'caption': 'Advanced Edit',
    #             'action': self.get_action_url(
    #                 'create_or_edit_settings',
    #                 extra_args={
    #                     'tab': tab.name,
    #                     'tab_title': tab.title,
    #                     }),
    #             'xsrf_token': self.create_xsrf_token(
    #                 'create_or_edit_settings')})

    #     # course.yaml file content.
    #     yaml_reader = self.app_context.fs.open(
    #         self.app_context.get_config_filename())
    #     yaml_info = self.text_file_to_safe_dom(yaml_reader, '< empty file >')
    #     yaml_reader = self.app_context.fs.open(
    #         self.app_context.get_config_filename())
    #     yaml_lines = self.text_file_to_string(yaml_reader, '< empty file >')

    #     # course_template.yaml file contents
    #     course_template_reader = open(os.path.join(os.path.dirname(
    #         __file__), '../../course_template.yaml'), 'r')
    #     course_template_info = self.text_file_to_safe_dom(
    #         course_template_reader, '< empty file >')
    #     course_template_reader = open(os.path.join(os.path.dirname(
    #         __file__), '../../course_template.yaml'), 'r')
    #     course_template_lines = self.text_file_to_string(
    #         course_template_reader, '< empty file >')

    #     template_values['sections'] = [
    #         {
    #             'title': 'Contents of course.yaml file',
    #             'description': messages.CONTENTS_OF_THE_COURSE_DESCRIPTION,
    #             'actions': actions,
    #             'children': yaml_info,
    #             'code': yaml_lines,
    #             'mode': 'yaml'
    #         },
    #         {
    #             'title': 'Contents of course_template.yaml file',
    #             'description': messages.COURSE_TEMPLATE_DESCRIPTION,
    #             'children': course_template_info,
    #             'code': course_template_lines,
    #             'mode': 'yaml'
    #         }
    #     ]

    # def list_and_format_file_list(
    #     self, title, subfolder, tab_name,
    #     links=False, upload=False, prefix=None, caption_if_empty='< none >',
    #     edit_url_template=None, merge_local_files=False, sub_title=None,
    #     all_paths=None):
    #     """Walks files in folders and renders their names in a section."""

    #     # keep a list of files without merging
    #     unmerged_files = {}
    #     if merge_local_files:
    #         unmerged_files = dashboard_utils.list_files(
    #             self, subfolder, merge_local_files=False, all_paths=all_paths)

    #     items = safe_dom.NodeList()
    #     count = 0
    #     for filename in dashboard_utils.list_files(
    #             self, subfolder, merge_local_files=merge_local_files,
    #             all_paths=all_paths):
    #         if prefix and not filename.startswith(prefix):
    #             continue

    #         # make a <li> item
    #         li = safe_dom.Element('li')
    #         if links:
    #             url = urllib.quote(filename)
    #             li.add_child(safe_dom.Element(
    #                 'a', href=url).add_text(filename))
    #         else:
    #             li.add_text(filename)

    #         # add actions if available
    #         if (edit_url_template and
    #             self.app_context.fs.impl.is_read_write()):

    #             li.add_child(safe_dom.Entity('&nbsp;'))
    #             edit_url = edit_url_template % (
    #                 tab_name, urllib.quote(filename))
    #             # show [overridden] + edit button if override exists
    #             if (filename in unmerged_files) or (not merge_local_files):
    #                 li.add_text('[Overridden]').add_child(
    #                     self._create_edit_button(edit_url))
    #             # show an [override] link otherwise
    #             else:
    #                 li.add_child(safe_dom.A(edit_url).add_text('[Override]'))

    #         count += 1
    #         items.append(li)

    #     output = safe_dom.NodeList()

    #     if self.app_context.is_editable_fs() and upload:
    #         output.append(
    #             safe_dom.Element(
    #                 'a', className='gcb-button gcb-pull-right',
    #                 href='dashboard?%s' % urllib.urlencode(
    #                     {'action': 'manage_asset',
    #                      'tab': tab_name,
    #                      'key': subfolder})
    #             ).add_text(
    #                 'Upload to ' + subfolder.lstrip('/').rstrip('/'))
    #         ).append(
    #             safe_dom.Element(
    #                 'div', style='clear: both; padding-top: 2px;'
    #             )
    #         )
    #     if title:
    #         h3 = safe_dom.Element('h3')
    #         if count:
    #             h3.add_text('%s (%s)' % (title, count))
    #         else:
    #             h3.add_text(title)
    #         output.append(h3)
    #     if sub_title:
    #         output.append(safe_dom.Element('blockquote').add_text(sub_title))
    #     if items:
    #         output.append(safe_dom.Element('ol').add_children(items))
    #     else:
    #         if caption_if_empty:
    #             output.append(
    #                 safe_dom.Element('blockquote').add_text(caption_if_empty))
    #     return output

    # def _attach_filter_data(self, element):
    #     course = courses.Course(self)
    #     unit_list = []
    #     assessment_list = []
    #     for unit in self.get_units():
    #         if verify.UNIT_TYPE_UNIT == unit.type:
    #             unit_list.append((unit.unit_id, unit.title))
    #         if unit.is_assessment():
    #             assessment_list.append((unit.unit_id, unit.title))

    #     lessons_map = {}
    #     for (unit_id, unused_title) in unit_list:
    #         lessons_map[unit_id] = [
    #             (l.lesson_id, l.title) for l in course.get_lessons(unit_id)]

    #     element.add_attribute(
    #         data_units=transforms.dumps(unit_list + assessment_list),
    #         data_lessons_map=transforms.dumps(lessons_map),
    #         data_questions=transforms.dumps(
    #             [(question.id, question.description) for question in sorted(
    #                 QuestionDAO.get_all(), key=lambda q: q.description)]
    #         ),
    #         data_groups=transforms.dumps(
    #             [(group.id, group.description) for group in sorted(
    #                 QuestionGroupDAO.get_all(), key=lambda g: g.description)]
    #         ),
    #         data_types=transforms.dumps([
    #             (QuestionDTO.MULTIPLE_CHOICE, 'Multiple Choice'),
    #             (QuestionDTO.SHORT_ANSWER, 'Short Answer')])
    #     )

    # def _create_location_link(self, text, url, loc_id, count):
    #     return safe_dom.Element(
    #         'li', data_count=str(count), data_id=str(loc_id)).add_child(
    #         safe_dom.Element('a', href=url).add_text(text)).add_child(
    #         safe_dom.Element('span', className='count').add_text(
    #         ' (%s)' % count if count > 1 else ''))

    # def _create_locations_cell(self, locations):
    #     ul = safe_dom.Element('ul')
    #     for (assessment, count) in locations.get('assessments', {}).iteritems():
    #         ul.add_child(self._create_location_link(
    #             assessment.title, 'assessment?name=%s' % assessment.unit_id,
    #             assessment.unit_id, count
    #         ))

    #     for ((lesson, unit), count) in locations.get('lessons', {}).iteritems():
    #         ul.add_child(self._create_location_link(
    #             '%s: %s' % (unit.title, lesson.title),
    #             'unit?unit=%s&lesson=%s' % (unit.unit_id, lesson.lesson_id),
    #             lesson.lesson_id, count
    #         ))

    #     return safe_dom.Element('td', className='locations').add_child(ul)

    # def _create_list(self, list_items):
    #     ul = safe_dom.Element('ul')
    #     for item in list_items:
    #         ul.add_child(safe_dom.Element('li').add_child(item))
    #     return ul

    # def _create_list_cell(self, list_items):
    #     return safe_dom.Element('td').add_child(self._create_list(list_items))

    # def _create_edit_button(self, edit_url):
    #     return safe_dom.A(
    #         href=edit_url,
    #         className='icon md-mode-edit',
    #         title='Edit',
    #         alt='Edit',
    #     )

    # def _create_edit_button_for_course_outline(self, edit_url):
    #     # TODO(jorr): Replace _create_edit_button with this
    #     return safe_dom.A(
    #         href=edit_url,
    #         className='icon md md-mode-edit reveal-on-hover',
    #         title='Edit',
    #         alt='Edit',
    #     )

    # def _create_add_to_group_button(self):
    #     return safe_dom.Element(
    #         'div',
    #         className='icon md md-add-circle gcb-pull-right',
    #         title='Add to question group',
    #         alt='Add to question group'
    #     )

    # def _create_preview_button(self):
    #     return safe_dom.Element(
    #         'div',
    #         className='icon md md-visibility',
    #         title='Preview',
    #         alt='Preview'
    #     )

    # def _create_clone_button(self, question_id):
    #     return safe_dom.A(
    #         href='#',
    #         className='icon md md-content-copy',
    #         title='Clone',
    #         alt='Clone',
    #         data_key=str(question_id)
    #     )

    # def _add_assets_table(self, output, table_id, columns):
    #     """Creates an assets table with the specified columns.

    #     Args:
    #         output: safe_dom.NodeList to which the table should be appended.
    #         table_id: string specifying the id for the table
    #         columns: list of tuples that specifies column name and width.
    #             For example ("Description", 35) would create a column with a
    #             width of 35% and the header would be Description.

    #     Returns:
    #         The table safe_dom.Element of the created table.
    #     """
    #     container = safe_dom.Element('div', className='assets-table-container')
    #     output.append(container)
    #     table = safe_dom.Element('table', className='assets-table', id=table_id)
    #     container.add_child(table)
    #     thead = safe_dom.Element('thead')
    #     table.add_child(thead)
    #     tr = safe_dom.Element('tr')
    #     thead.add_child(tr)
    #     ths = safe_dom.NodeList()
    #     for (title, width) in columns:
    #         ths.append(safe_dom.Element(
    #             'th', style=('width: %s%%' % width)).add_text(title).add_child(
    #                 safe_dom.Element(
    #                     'span', className='md md-arrow-drop-up')).add_child(
    #                 safe_dom.Element(
    #                     'span', className='md md-arrow-drop-down')))
    #     tr.add_children(ths)
    #     return table

    # def _create_filter(self):
    #     return safe_dom.Element(
    #         'div', className='gcb-pull-right filter-container',
    #         id='question-filter'
    #     ).add_child(
    #         safe_dom.Element(
    #             'button', className='gcb-button gcb-pull-right filter-button'
    #         ).add_text('Filter')
    #     )

    # def _create_empty_footer(self, text, colspan, set_hidden=False):
    #     """Creates a <tfoot> that will be visible when the table is empty."""
    #     tfoot = safe_dom.Element('tfoot')
    #     if set_hidden:
    #         tfoot.add_attribute(style='display: none')
    #     empty_tr = safe_dom.Element('tr')
    #     return tfoot.add_child(empty_tr.add_child(safe_dom.Element(
    #         'td', colspan=str(colspan), style='text-align: center'
    #     ).add_text(text)))

    # def _get_question_locations(self, quid, location_maps, used_by_groups):
    #     """Calculates the locations of a question and its containing groups."""
    #     (qulocations_map, qglocations_map) = location_maps
    #     locations = qulocations_map.get(quid, None)
    #     if locations is None:
    #         locations = {'lessons': {}, 'assessments': {}}
    #     else:
    #         locations = copy.deepcopy(locations)
    #     # At this point locations holds counts of the number of times quid
    #     # appears in each lesson and assessment. Now adjust the counts by
    #     # counting the number of times quid appears in a question group in that
    #     # lesson or assessment.
    #     lessons = locations['lessons']
    #     assessments = locations['assessments']
    #     for group in used_by_groups:
    #         qglocations = qglocations_map.get(group.id, None)
    #         if not qglocations:
    #             continue
    #         for lesson in qglocations['lessons']:
    #             lessons[lesson] = lessons.get(lesson, 0) + 1
    #         for assessment in qglocations['assessments']:
    #             assessments[assessment] = assessments.get(assessment, 0) + 1

    #     return locations

    # def list_questions(self, all_questions, all_question_groups, location_maps):
    #     """Prepare a list of the question bank contents."""
    #     if not self.app_context.is_editable_fs():
    #         return safe_dom.NodeList()

    #     output = safe_dom.NodeList().append(
    #         safe_dom.Element(
    #             'a', className='gcb-button gcb-pull-right',
    #             href='dashboard?action=add_mc_question'
    #         ).add_text('Add Multiple Choice')
    #     ).append(
    #         safe_dom.Element(
    #             'a', className='gcb-button gcb-pull-right',
    #             href='dashboard?action=add_sa_question'
    #         ).add_text('Add Short Answer')
    #     ).append(
    #         safe_dom.Element(
    #             'a', className='gcb-button gcb-pull-right',
    #             href='dashboard?action=import_gift_questions'
    #         ).add_text('Import GIFT Questions')
    #     ).append(self._create_filter()).append(
    #         safe_dom.Element('div', style='clear: both; padding-top: 2px;')
    #     ).append(safe_dom.Element('h3').add_text(
    #         'Questions (%s)' % len(all_questions)
    #     ))

    #     # Create questions table
    #     table = self._add_assets_table(
    #         output, 'question-table', [
    #         ('Description', 25), ('Question Groups', 25),
    #         ('Course Locations', 25), ('Last Modified', 16), ('Type', 9)]
    #     )
    #     self._attach_filter_data(table)
    #     table.add_attribute(
    #         data_clone_question_token=self.create_xsrf_token('clone_question'))
    #     table.add_attribute(
    #         data_qg_xsrf_token=self.create_xsrf_token('add_to_question_group'))
    #     tbody = safe_dom.Element('tbody')
    #     table.add_child(tbody)

    #     table.add_child(self._create_empty_footer(
    #         'No questions available', 5, all_questions))

    #     question_to_group = {}
    #     for group in all_question_groups:
    #         for quid in group.question_ids:
    #             question_to_group.setdefault(long(quid), []).append(group)

    #     for question in all_questions:
    #         tr = safe_dom.Element('tr', data_quid=str(question.id))
    #         # Add description including action icons
    #         td = safe_dom.Element('td', className='description')
    #         tr.add_child(td)
    #         td.add_child(self._create_edit_button(
    #             'dashboard?action=edit_question&key=%s' % question.id))
    #         td.add_child(self._create_preview_button())
    #         td.add_child(self._create_clone_button(question.id))
    #         td.add_text(question.description)

    #         # Add containing question groups
    #         used_by_groups = question_to_group.get(question.id, [])
    #         cell = safe_dom.Element('td', className='groups')
    #         if all_question_groups:
    #             cell.add_child(self._create_add_to_group_button())
    #         cell.add_child(self._create_list(
    #             [safe_dom.Text(group.description) for group in sorted(
    #                 used_by_groups, key=lambda g: g.description)]
    #         ))
    #         tr.add_child(cell)

    #         # Add locations
    #         locations = self._get_question_locations(
    #             question.id, location_maps, used_by_groups)
    #         tr.add_child(self._create_locations_cell(locations))

    #         # Add last modified timestamp
    #         tr.add_child(safe_dom.Element(
    #             'td',
    #             data_timestamp=str(question.last_modified),
    #             className='timestamp'
    #         ))

    #         # Add question type
    #         tr.add_child(safe_dom.Element('td').add_text(
    #             'MC' if question.type == QuestionDTO.MULTIPLE_CHOICE else (
    #                 'SA' if question.type == QuestionDTO.SHORT_ANSWER else (
    #                 'Unknown Type'))
    #         ).add_attribute(style='text-align: center'))

    #         # Add filter information
    #         filter_info = {}
    #         filter_info['description'] = question.description
    #         filter_info['type'] = question.type
    #         filter_info['lessons'] = []
    #         unit_ids = set()
    #         for (lesson, unit) in locations.get('lessons', ()):
    #             unit_ids.add(unit.unit_id)
    #             filter_info['lessons'].append(lesson.lesson_id)
    #         filter_info['units'] = list(unit_ids) + [
    #             a.unit_id for a in  locations.get('assessments', ())]
    #         filter_info['groups'] = [qg.id for qg in used_by_groups]
    #         filter_info['unused'] = 0 if locations else 1
    #         tr.add_attribute(data_filter=transforms.dumps(filter_info))
    #         tbody.add_child(tr)

    #     return output

    # def get_question_description(self, quid_to_question, quid):
    #     if long(quid) in quid_to_question:
    #          return quid_to_question[long(quid)].description
    #     else:
    #          return 'Deleted Question'

    # def list_question_groups(
    #     self, all_questions, all_question_groups, locations_map):
    #     """Prepare a list of question groups."""
    #     if not self.app_context.is_editable_fs():
    #         return safe_dom.NodeList()

    #     output = safe_dom.NodeList()
    #     output.append(
    #         safe_dom.Element(
    #             'a', className='gcb-button gcb-pull-right',
    #             href='dashboard?action=add_question_group'
    #         ).add_text('Add Question Group')
    #     ).append(
    #         safe_dom.Element(
    #             'div', style='clear: both; padding-top: 2px;'
    #         )
    #     )
    #     output.append(safe_dom.Element('h3').add_text(
    #         'Question Groups (%s)' % len(all_question_groups)
    #     ))

    #     # Create question groups table
    #     table = self._add_assets_table(
    #         output, 'question-group-table', [
    #         ('Description', 25), ('Questions', 25), ('Course Locations', 25),
    #         ('Last Modified', 25)]
    #     )
    #     tbody = safe_dom.Element('tbody')
    #     table.add_child(tbody)

    #     if not all_question_groups:
    #         table.add_child(self._create_empty_footer(
    #             'No question groups available', 4))

    #     quid_to_question = {long(qu.id): qu for qu in all_questions}
    #     for question_group in all_question_groups:
    #         tr = safe_dom.Element('tr', data_qgid=str(question_group.id))
    #         # Add description including action icons
    #         td = safe_dom.Element('td', className='description')
    #         tr.add_child(td)
    #         td.add_child(self._create_edit_button(
    #             'dashboard?action=edit_question_group&key=%s' % (
    #             question_group.id)))
    #         td.add_text(question_group.description)

    #         # Add questions
    #         tr.add_child(self._create_list_cell([
    #             safe_dom.Text(descr) for descr in sorted([
    #                 self.get_question_description(quid_to_question, quid)
    #                 for quid in question_group.question_ids])
    #         ]).add_attribute(className='questions'))

    #         # Add locations
    #         tr.add_child(self._create_locations_cell(
    #             locations_map.get(question_group.id, {})))

    #         # Add last modified timestamp
    #         tr.add_child(safe_dom.Element(
    #             'td',
    #             data_timestamp=str(question_group.last_modified),
    #             className='timestamp'
    #         ))

    #         tbody.add_child(tr)

    #     return output

    # def list_labels(self):
    #     """Prepare a list of labels for use on the Assets page."""
    #     output = safe_dom.NodeList()
    #     if not self.app_context.is_editable_fs():
    #         return output

    #     output.append(
    #         safe_dom.A('dashboard?action=add_label',
    #                    className='gcb-button gcb-pull-right'
    #                   ).add_text('Add Label')
    #         ).append(
    #             safe_dom.Element(
    #                 'div', style='clear: both; padding-top: 2px;'
    #             )
    #         )
    #     output.append(
    #             safe_dom.Element('h3').add_text('Labels')
    #     )
    #     labels = LabelDAO.get_all()
    #     if labels:
    #         all_labels_ul = safe_dom.Element('ul')
    #         output.append(all_labels_ul)
    #         for label_type in sorted(
    #             models.LabelDTO.LABEL_TYPES,
    #             lambda a, b: cmp(a.menu_order, b.menu_order)):

    #             type_li = safe_dom.Element('li').add_text(label_type.title)
    #             all_labels_ul.add_child(type_li)
    #             labels_of_type_ul = safe_dom.Element('ul')
    #             type_li.add_child(labels_of_type_ul)
    #             for label in sorted(
    #                 labels, lambda a, b: cmp(a.title, b.title)):
    #                 if label.type == label_type.type:
    #                     li = safe_dom.Element('li')
    #                     labels_of_type_ul.add_child(li)
    #                     li.add_text(
    #                         label.title
    #                     ).add_attribute(
    #                         title='id: %s, type: %s' % (label.id, label_type))
    #                     if label_type not in (
    #                         models.LabelDTO.SYSTEM_EDITABLE_LABEL_TYPES):

    #                         li.add_child(
    #                             self._create_edit_button(
    #                                 'dashboard?action=edit_label&key=%s' %
    #                                 label.id,
    #                                 ).add_attribute(
    #                                     id='label_%s' % label.title))
    #     else:
    #         output.append(safe_dom.Element('blockquote').add_text('< none >'))
    #     return output

    # def get_assets(self):
    #     """Renders course assets view."""

    #     all_paths = self.app_context.fs.list(
    #         sites.abspath(self.app_context.get_home_folder(), '/'))
    #     # tab = tabs.Registry.get_tab(
    #     #     'assets', self.request.get('tab') or 'questions')
    #     items = safe_dom.NodeList()
    #     # tab.contents(self, items, tab, all_paths)
    #     # title_text = 'Assets > %s' % tab.title
    #     template_values = {
    #         'page_title': self.format_title("title_text"),
    #         'page_description': messages.ASSETS_DESCRIPTION,
    #         'main_content': items,
    #     }
    #     self.render_page(template_values)

    # def filer_url_template(self):
    #     return 'dashboard?action=manage_text_asset&tab=%s&uri=%s'

    # def get_assets_contrib(self, items, tab, all_paths):
    #     if not self.contrib_asset_listers:
    #         items.append(safe_dom.Text(
    #             'No assets extensions have been registered'))
    #     else:
    #         for asset_lister in self.contrib_asset_listers:
    #             items.append(asset_lister(self))

    # def get_assets_questions(self, items, tab, all_paths):
    #     all_questions = QuestionDAO.get_all()
    #     all_question_groups = QuestionGroupDAO.get_all()
    #     locations = courses.Course(
    #         self).get_component_locations()
    #     items.append(self.list_questions(
    #         all_questions, all_question_groups, locations))
    #     items.append(self.list_question_groups(
    #         all_questions, all_question_groups, locations[1]))

    # def get_assets_labels(self, items, tab, all_paths):
    #     items.append(self.list_labels())

    # def get_assets_assessments(self, items, tab, all_paths):
    #     items.append(self.list_and_format_file_list(
    #         'Assessments', '/assets/js/', tab.name, links=True,
    #         prefix='assets/js/assessment-', all_paths=all_paths))

    # def get_assets_activities(self, items, tab, all_paths):
    #     items.append(self.list_and_format_file_list(
    #         'Activities', '/assets/js/', tab.name, links=True,
    #         prefix='assets/js/activity-', all_paths=all_paths))

    # def get_assets_images(self, items, tab, all_paths):
    #     items.append(self.list_and_format_file_list(
    #         'Images & Documents', '/assets/img/', tab.name, links=True,
    #         upload=True, merge_local_files=True,
    #         edit_url_template=(
    #             'dashboard?action=manage_asset&tab=%s&key=%s'),
    #         caption_if_empty='< inherited from /assets/img/ >',
    #         all_paths=all_paths))

    # def get_assets_css(self, items, tab, all_paths):
    #     items.append(self.list_and_format_file_list(
    #         'CSS', '/assets/css/', tab.name, links=True,
    #         upload=True, edit_url_template=self.filer_url_template(),
    #         caption_if_empty='< inherited from /assets/css/ >',
    #         merge_local_files=True, all_paths=all_paths))

    # def get_assets_js(self, items, tab, all_paths):
    #     items.append(self.list_and_format_file_list(
    #         'JavaScript', '/assets/lib/', tab.name, links=True,
    #         upload=True, edit_url_template=self.filer_url_template(),
    #         caption_if_empty='< inherited from /assets/lib/ >',
    #         merge_local_files=True, all_paths=all_paths))

    # def get_assets_html(self, items, tab, all_paths):
    #     items.append(self.list_and_format_file_list(
    #         'HTML', '/assets/html/', tab.name, links=True,
    #         upload=True, edit_url_template=self.filer_url_template(),
    #         caption_if_empty='< inherited from /assets/html/ >',
    #         merge_local_files=True, all_paths=all_paths))

    # def get_assets_templates(self, items, tab, all_paths):
    #     items.append(self.list_and_format_file_list(
    #         'View Templates', '/views/', tab.name, upload=True,
    #         edit_url_template=self.filer_url_template(),
    #         caption_if_empty='< inherited from /views/ >',
    #         merge_local_files=True, all_paths=all_paths))

    # def get_analytics(self):
    #     """Renders course analytics view."""
    #     # tab = tabs.Registry.get_tab('analytics',
    #     #                             (self.request.get('tab') or
    #     #                              self.default_subtab_action['analytics']))
    #     title_text = 'Analytics > %s' % "tab.title"
    #     template_values = {
    #         'page_title': self.format_title(title_text),
    #         'main_content': analytics.generate_display_html(
    #             self, crypto.XsrfTokenManager, tab.contents),
    #         }
    #     self.render_page(template_values)

    def _render_roles_list(self):
        """Render roles list to HTML."""
        all_roles = sorted(RoleDAO.get_all(), key=lambda role: role.name)
        return safe_dom.Template(
            self.get_template('role_list.html'), roles=all_roles)

    def _render_roles_view(self):
        """Renders course roles view."""
        actions = [{
            'id': 'add_role',
            'caption': 'Add Role',
            'href': self.get_action_url('add_role')}]
        sections = [{
                'description': messages.ROLES_DESCRIPTION,
                'actions': actions,
                'pre': self._render_roles_list()
        }]
        template_values = {
            'page_title': self.format_title('Roles'),
            'sections': sections,
        }
        return template_values

    @classmethod
    def map_get_action_to_permission(cls, action, module, perm):
        """Maps a view/get action to a permission.

        Map a GET action that goes through the dashboard to a
        permission to control which users have access.

        Example:
            The i18n module maps multiple actions to the permission
            'access_i18n_dashboard'.  Users who have a role assigned with this
            permission are then allowed to perform these actions and thus
            access the translation tools.

        Args:
            action: a string specifying the action to map.
            module: The module with which the permission was registered via
                a call to models.roles.Roles.register_permission()
            permission: a string specifying the permission to which the action
                should be mapped.
        """
        checker = lambda ctx: roles.Roles.is_user_allowed(ctx, module, perm)
        cls.map_get_action_to_permission_checker(action, checker)

    @classmethod
    def map_get_action_to_permission_checker(cls, action, checker):
        """Map an action to a function to check permissions.

        Some actions (notably settings and the course overview) produce pages
        that have items that may be controlled by multiple permissions or
        more complex verification than a single permission allows.  This
        function allows modules to specify check functions.

        Args:
          action: A string specifying the name of the action being checked.
              This should have been registered via add_custom_get_action(),
              or present in the 'get_actions' list above in this file.
          checker: A function which is run when the named action is accessed.
              Registered functions should expect one parameter: the application
              context object, and return a Boolean value.
        """
        cls._get_action_to_permission[action] = checker

    @classmethod
    def unmap_get_action_to_permission(cls, action):
        del cls._get_action_to_permission[action]

    @classmethod
    def map_post_action_to_permission(cls, action, module, perm):
        """Maps an edit action to a permission. (See 'get' version, above.)"""
        checker = lambda ctx: roles.Roles.is_user_allowed(ctx, module, perm)
        cls.map_post_action_to_permission_checker(action, checker)

    @classmethod
    def map_post_action_to_permission_checker(cls, action, checker):
        """Map an edit action to check function.  (See 'get' version, above)."""
        cls._post_action_to_permission[action] = checker

    @classmethod
    def unmap_post_action_to_permission(cls, action):
        """Remove mapping to edit action.  (See 'get' version, above)."""
        del cls._post_action_to_permission[action]

    @classmethod
    def deprecated_add_external_permission(cls, permission_name,
                                           permission_description):
        """Adds extra permissions that will be registered by the Dashboard.

        Normally, permissions should be registered in their own modules.
        Due to historical accident, the I18N module registers permissions
        with the dashboard.  For backward compatibility with existing roles,
        this API is preserved, but not suggested for use by future modules.
        """
        cls._external_permissions[permission_name] = permission_description

    @classmethod
    def remove_external_permission(cls, permission_name):
        del cls._external_permissions[permission_name]

    @classmethod
    def permissions_callback(cls, unused_app_context):
        return cls._external_permissions.iteritems()

    @classmethod
    def current_user_has_access(cls, app_context):
        return cls.root_menu_group.can_view(app_context, exclude_links=True)

    @classmethod
    def generate_dashboard_link(cls, app_context):
        if cls.current_user_has_access(app_context):
            return [('dashboard', 'Dashboard')]
        return []


def make_help_menu():
    DashboardHandler.add_nav_mapping('help', 'Help', placement=6000)

    DashboardHandler.add_sub_nav_mapping(
        'help', 'documentation', 'Documentation',
        href=services.help_urls.get('help:documentation'), target='_blank')

    DashboardHandler.add_sub_nav_mapping(
        'help', 'forum', 'Support', href=services.help_urls.get('help:forum'),
        target='_blank')

    DashboardHandler.add_sub_nav_mapping(
        'help', 'videos', 'Videos', href=services.help_urls.get('help:videos'),
        target='_blank')

def get_visible_courses(include_closed=True):

    all_contexts = sorted(sites.get_all_courses(include_closed=include_closed),
                          key=lambda course: course.get_title().lower())

    if roles.Roles.is_super_admin():
        return all_contexts

    user_email = users.get_current_user().email()
    return [ac for ac in all_contexts if user_email in ac.course_admin_email]


def register_module():
    """Registers this module in the registry."""

    DashboardHandler.add_nav_mapping('edit', 'Create', placement=1000)
    DashboardHandler.add_nav_mapping('style', 'Style', placement=2000)
    DashboardHandler.add_nav_mapping('publish', 'Publish', placement=3000)
    DashboardHandler.add_nav_mapping('analytics', 'Manage', placement=4000)
    DashboardHandler.add_nav_mapping('settings', 'Settings', placement=5000)

    make_help_menu()

    # pylint: disable=protected-access
    DashboardHandler.add_sub_nav_mapping(
        'settings', 'roles', 'Roles', action='edit_roles',
        contents=DashboardHandler._render_roles_view)
    # pylint: enable=protected-access

    def on_module_enabled():
        roles.Roles.register_permissions(
            custom_module, DashboardHandler.permissions_callback)
        ApplicationHandler.AUTH_LINKS.append(
            DashboardHandler.generate_dashboard_link)

    global_routes = [
        (dashboard_utils.RESOURCES_PATH +'/js/.*', tags.JQueryHandler),
        (dashboard_utils.RESOURCES_PATH + '/.*',
            tags.DeprecatedResourcesHandler)]

    dashboard_handlers = [
        ('/dashboard', DashboardHandler),
    ]
    global custom_module  # pylint: disable=global-statement
    custom_module = custom_modules.Module(
        'Course Dashboard',
        'A set of pages for managing Course Builder course.',
        global_routes, dashboard_handlers,
        notify_module_enabled=on_module_enabled)
    return custom_module
