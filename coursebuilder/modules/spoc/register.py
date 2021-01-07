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

"""Registers this module in the registry"""

__author__ = 'Rishav Thakker (rthakker@google.com)'

from modules.dashboard import dashboard
from modules.spoc import roles as spoc_roles
from modules.spoc import settings
from modules.spoc import base
from modules.spoc import dashboard as spoc_dashboard
from modules.spoc import scripts
from models import custom_modules
from models import roles

custom_module = None

def register_module():
    """Registers this module in the registry"""

    permissions = []

    def permissions_callback(unused_application_context):
        return permissions

    def on_module_enabled():
        spoc_roles.on_module_enabled(custom_module, permissions)
        roles.Roles.register_permissions(custom_module, permissions_callback)

        dashboard.DashboardHandler.add_custom_get_action(
            spoc_dashboard.SPOCDashboardHandler.LIST_ACTION,
            spoc_dashboard.SPOCDashboardHandler.display_html)

        dashboard.DashboardHandler.add_custom_get_action(
            spoc_dashboard.SPOCDashboardHandler.DOWNLOAD_ACTION,
            spoc_dashboard.SPOCDashboardHandler.download_student_list)

        dashboard.DashboardHandler.add_sub_nav_mapping(
            spoc_dashboard.SPOCDashboardHandler.DASHBOARD_CATEGORY,
            spoc_dashboard.SPOCDashboardHandler.LIST_ACTION,
            spoc_dashboard.SPOCDashboardHandler.NAME,
            action=spoc_dashboard.SPOCDashboardHandler.LIST_ACTION,
            can_view=spoc_dashboard.SPOCDashboardHandler.can_view)

        dashboard.DashboardHandler.map_get_action_to_permission_checker(
            spoc_dashboard.SPOCDashboardHandler.LIST_ACTION,
            spoc_dashboard.SPOCDashboardHandler.can_view
        )

        dashboard.DashboardHandler.map_get_action_to_permission_checker(
            spoc_dashboard.SPOCDashboardHandler.DOWNLOAD_ACTION,
            spoc_dashboard.SPOCDashboardHandler.can_view
        )

        dashboard.DashboardHandler.add_custom_post_action(
            spoc_dashboard.SPOCDashboardHandler.SAVE_ACTION,
            spoc_dashboard.SPOCDashboardHandler.save_student_data
        )

        dashboard.DashboardHandler.map_post_action_to_permission_checker(
            spoc_dashboard.SPOCDashboardHandler.SAVE_ACTION,
            spoc_dashboard.SPOCDashboardHandler.can_edit
        )

        settings.custom_module = custom_module
        spoc_dashboard.custom_module = custom_module
        base.custom_module = custom_module

    settings.populate_menu()
    global_routes = settings.global_routes
    global_routes += scripts.global_routes

    global custom_module # pylint: disable=global-statement
    custom_module = custom_modules.Module(
        base.SPOCBase.MODULE_NAME,
        'Module for Local Chapter SPOC',
        global_routes, [],
        notify_module_enabled=on_module_enabled)
    return custom_module
