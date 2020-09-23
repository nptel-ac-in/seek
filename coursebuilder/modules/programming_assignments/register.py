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

"""Methods to register Programming Assignments module."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


import os
import appengine_config

from common import tags
from models import analytics
from models import data_sources
from models import custom_modules
from models import custom_units
from controllers import sites
from modules.dashboard import dashboard
from modules.dashboard import tabs
from modules.programming_assignments import analytics as panalytics
from modules.programming_assignments import assignment
from modules.programming_assignments import base
from modules.programming_assignments import dashboard as pdashboard
from modules.programming_assignments import question
from modules.programming_assignments import reevaluator
from modules.programming_assignments import settings
from modules.scoring import base as scoring_base

custom_unit = None
custom_module = None


def register_module():
    """Registers this module in the registry."""
    data_sources.Registry.register(
        panalytics.ProgrammingStatsDataSource)

    tab_name = 'programming_assignment_stats'
    stats = analytics.Visualization(
        tab_name, base.ProgAssignment.NAME,
        'templates/prog_assignment_stats.html',
        data_source_classes=[panalytics.ProgrammingStatsDataSource])
    tabs.Registry.register(
        'analytics', tab_name, base.ProgAssignment.NAME, [stats])

    settings.ProgrammingAssignmentSettings.register()

    tabs.Registry.register(
        scoring_base.ScoringBase.DASHBOARD_NAV,
        base.ProgAssignment.DASHBOARD_REEVALUATION_TAB,
        'Programming Assignments',
        pdashboard.ProgAssignmentDashboardHandler)

    tabs.Registry.register(
        base.ProgAssignment.DASHBOARD_NAV,
        base.ProgAssignment.DASHBOARD_TEST_RUN_TAB,
        'Test Run Details',
        pdashboard.ProgAssignmentTestRunHandler)

    tabs.Registry.register(
        base.ProgAssignment.DASHBOARD_NAV,
        base.ProgAssignment.DASHBOARD_DOWNLOAD_TAB,
        'Download',
        pdashboard.ProgAssignmentDownloadDashboardHandler)


    dashboard.DashboardHandler.add_custom_get_action(
        base.ProgAssignment.DASHBOARD_NAV, None)

    dashboard.DashboardHandler.add_custom_post_action(
        base.ProgAssignment.REEVAL_ACTION,
        pdashboard.ProgAssignmentDashboardHandler.confirm_reevaluation_page)
    dashboard.DashboardHandler.add_custom_post_action(
        base.ProgAssignment.REEVAL_CONFIRMED_ACTION,
        pdashboard.ProgAssignmentDashboardHandler.reevalaute_assignment)

    dashboard.DashboardHandler.add_custom_post_action(
        base.ProgAssignment.DOWNLOAD_ACTION,
        pdashboard.ProgAssignmentDownloadDashboardHandler.download_assignment)

    dashboard.DashboardHandler.add_custom_get_action(
        base.ProgAssignment.TEST_RUN_ACTION,
        pdashboard.ProgAssignmentTestRunHandler.get_show_results)

    dashboard.DashboardHandler.add_nav_mapping(
        base.ProgAssignment.DASHBOARD_NAV, base.ProgAssignment.NAME)

    associated_js_files_handlers = [
        ('/static/edit_area/(.*)', sites.make_zip_handler(
            os.path.join(
                appengine_config.BUNDLE_ROOT, 'lib/edit-area.zip'))),
        ('/static/prettify/(.*)', sites.make_zip_handler(
            os.path.join(
                appengine_config.BUNDLE_ROOT, 'lib/google-code-prettify.zip'))),
        ('/cron/compute_programming_test_case_stats',
         panalytics.ComputeProgrammingStatsHandler),
        ('/cron/reevaluate_programming_submissions',
         reevaluator.ReevaulateSubmissionHandler),
        ('/modules/programming_assignments/assets/.*', tags.ResourcesHandler)]

    prog_assignment_handlers = [
        (base.ProgAssignment.UNIT_URL, assignment.ProgAssignmentHandler),
        (question.ProgAssignmentRESTHandler.URI,
         question.ProgAssignmentRESTHandler)]

    global custom_module  # pylint: disable=global-statement
    custom_module = custom_modules.Module(
        base.ProgAssignment.NAME,
        'A set pages to manage programming assignments.',
        associated_js_files_handlers, prog_assignment_handlers)

    global custom_unit  # pylint: disable=global-statement
    custom_unit = custom_units.CustomUnit(
        base.ProgAssignment.UNIT_TYPE_ID,
        base.ProgAssignment.NAME,
        question.ProgAssignmentRESTHandler,
        base.ProgAssignment.get_public_url,
        create_helper=question.create_assignment,
        cleanup_helper=base.ProgAssignment.delete_content,
        import_helper=question.import_assignment,
        is_graded=True)
    return custom_module
