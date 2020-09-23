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

"""Methods to register Mentor module."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


import os

from controllers import sites
from controllers.utils import BaseHandler
from controllers.utils import ReflectiveRequestHandler
from controllers.utils import XsrfTokenManager
from models import custom_modules
from models import transforms
from models.models import Student
from modules.dashboard import dashboard
from modules.dashboard import tabs
from modules.mentor import base
from modules.mentor import mentor
from modules.mentor import mentor_list
from modules.mentor import settings


# Module registration
custom_module = None


def register_module():
    """Registers this module in the registry."""
    namespaced_routes = [
        ('/student/mentee', mentor.MenteeListHandler),
        ('/student/mentor', mentor.MentorHandler)
    ]

    global_routes = [
        (mentor.BulkAddNewMentorRESTHandler.URI, mentor.BulkAddNewMentorRESTHandler)
    ]

    tabs.Registry.register(
        base.MentorBase.DASHBOARD_NAV,
        base.MentorBase.DASHBOARD_SHOW_LIST_TAB,
        'Mentor List',
        mentor_list.MentorListHandler)

    dashboard.DashboardHandler.add_custom_get_action(
        base.MentorBase.DASHBOARD_GET_ADD_TAB,
        mentor_list.AddMentorHandler.get_add_mentors_page)

    dashboard.DashboardHandler.add_custom_get_action(
        base.MentorBase.DASHBOARD_NAV, None)

    dashboard.DashboardHandler.add_custom_post_action(
        base.MentorBase.DASHBOARD_ADD_MENTORS,
        mentor_list.AddMentorHandler.add_mentors)
    dashboard.DashboardHandler.add_custom_post_action(
        base.MentorBase.DASHBOARD_REMOVE_MENTOR,
        mentor_list.MentorListHandler.remove_mentor)

    dashboard.DashboardHandler.add_nav_mapping(
        base.MentorBase.DASHBOARD_NAV, base.MentorBase.NAME)


    settings.MentorSettings.register()

    global custom_module
    custom_module = custom_modules.Module(
        base.MentorBase.NAME,
        'Provides mentor support',
        global_routes, namespaced_routes)
    return custom_module
