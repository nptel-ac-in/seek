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

"""Contain dashboard related classes for manual review."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

from models import custom_modules
from modules.admin import admin
from modules.dashboard import dashboard
from modules.student_list import dashboard as student_list_dashboard
from modules.student_list import base
from modules.student_list import settings

custom_module = None

def register_module():
    """Registers this module in the registry."""

    dashboard.DashboardHandler.add_custom_get_action(
        base.StudentListBase.DETAILS_ACTION,
        student_list_dashboard.StudentListDashboardHandler.get_details)

    dashboard.DashboardHandler.add_custom_post_action(
        base.StudentListBase.ENROLL_ACTION,
        student_list_dashboard.StudentListDashboardHandler.post_enroll)

    dashboard.DashboardHandler.add_custom_post_action(
        base.StudentListBase.UNENROLL_ACTION,
        student_list_dashboard.StudentListDashboardHandler.post_unenroll)

    dashboard.DashboardHandler.add_sub_nav_mapping(
        base.StudentListBase.DASHBOARD_CATEGORY,
        base.StudentListBase.DASHBOARD_NAV, base.StudentListBase.NAME,
        contents=(student_list_dashboard.StudentListDashboardHandler
                  .display_html))

    # Global admin view
    admin.BaseAdminHandler.add_menu_item(
        base.StudentListBase.ADMIN_CATEGORY, base.StudentListBase.ADMIN_NAV,
        base.StudentListBase.ADMIN_NAME,
        action=base.StudentListBase.ADMIN_NAV,
        sub_group_name=base.StudentListBase.ADMIN_SUBGROUP)

    admin.GlobalAdminHandler.add_custom_get_action(
        base.StudentListBase.ADMIN_NAV,
        settings.StudentListBaseAdminHandler.get_student_list)

    admin.GlobalAdminHandler.add_custom_get_action(
        base.StudentListBase.ADMIN_DETAILS_ACTION,
        settings.StudentListBaseAdminHandler.get_student_details)


    global custom_module
    custom_module = custom_modules.Module(
        'Student List',
        'A set of classes for managing students',
        [], [])
    return custom_module
