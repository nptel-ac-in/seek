# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Explorer handlers"""

__author__ = [
    'nretallack@google.com (Nick Retallack)',
]

import graphene
import appengine_config
from modules.explorer import constants
from common import tags
# from common import users
from controllers import utils
from common import jinja_utils
from models import transforms
from modules.explorer import settings

from modules.explorer import graphql
from modules.gql import gql


def get_institution_name():
    try:
        return transforms.loads(settings.COURSE_EXPLORER_SETTINGS.value)[
            'institution_name']
    except (ValueError, KeyError):
        return ''


class ExplorerHandler(utils.ApplicationHandler, utils.QueryableRouteMixin):
    URL = ''
    PAGE_LENGTH = 200

    @classmethod
    def can_handle_route_method_path_now(cls, route, method, path):
        return settings.GCB_ENABLE_COURSE_EXPLORER_PAGE.value

    @classmethod
    def load_navbar_links(cls):
        """
        Loads the explorer navbar links from course settings and returns
        as a dict
        """

        data = settings.get_course_explorer_settings_data()
        return {
            'left': data.get('navbar_links_left', list()),
            'right': data.get('navbar_links_right', list())
        }

    def get(self):
        include_closed = self.request.get('include_closed') == 'yes'
        q = self.request.get('q')
        template_value = {
            'institution_name': get_institution_name(),
            'use_flattened_html_imports': (
                appengine_config.USE_FLATTENED_HTML_IMPORTS),
            'navbar_links': self.load_navbar_links(),
            'include_closed': include_closed,
            'filter_text': q,
        }

        site_info_query_str = """{
            site {
                title, logo {url, altText},
                courseExplorer {extraContent, youtubeVideo}},
                currentUser {
                    email, loggedIn, canViewDashboard, canViewSpocDashboard,
                    canViewSpocAdmin, loginUrl (destUrl: "/"), hasProfile,
                    logoutUrl (destUrl: "/")}}"""

        initial_courses_query_str = """{
            courseList(args: {
                    includeClosed: false, filterText: "", category: "all",
                    status: "all", tags: "", firstLoad: true} ) {
                edges {
                    node {
                        id, title, url, explorerSummary, explorerInstructorName,
                        enrollment {enrolled}, openForRegistration,
                        showInExplorer,  startDate, endDate, estimatedWorkload,
                        category {name, category},  tags {name}, featured
                    }}, pageInfo {endCursor, hasNextPage}},
                categories {name, category}}"""

        site_info_result = graphene.Schema(query=gql.Query).execute(
            request=site_info_query_str)

        initial_courses_result = graphene.Schema(query=gql.Query).execute(
            request=initial_courses_query_str)

        template_value.update(site_info_result.data)
        template_value.update(initial_courses_result.data)

        template_value['page_length'] = self.PAGE_LENGTH

        if initial_courses_result.data['courseList']['pageInfo']['hasNextPage']:
            template_value['courseCursor'] = initial_courses_result.data['courseList']['pageInfo']['endCursor']
        else:
            template_value['courseCursor'] = None

        self.response.write(jinja_utils.get_template(
            'explorer.html', [constants.TEMPLATE_DIR, constants.VIEWS_TEMPLATE_DIR], handler=self).render(
                template_value))

global_routes = utils.map_handler_urls([
    ExplorerHandler,
])

# Static assets required for explorer
global_routes += [
    ('/assets/css/main.css', tags.ResourcesHandler),
    ('/explorer', ExplorerHandler)
]

namespaced_routes = []
