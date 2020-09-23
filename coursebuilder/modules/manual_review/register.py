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

"""Implementation of the review subsystem."""

__author__ = [
    'abhinavk@google.com (Abhinav Khandelwal)',
]

from models import custom_modules
from modules.manual_review import assign
from modules.manual_review import dashboard as manual_review_dashboard
from modules.manual_review import base
from modules.dashboard import dashboard
from modules.dashboard import tabs

custom_module = None


def register_module():
    """Registers this module in the registry."""

    # Register the dashboard handler
    tabs.Registry.register(
        base.ManualReviewBase.DASHBOARD_NAV,
        base.ManualReviewBase.DASHBOARD_TAB,
        base.ManualReviewBase.NAME,
        manual_review_dashboard.ManualReviewDashboardHandler)

    dashboard.DashboardHandler.add_custom_get_action(
        base.ManualReviewBase.DASHBOARD_NAV, None)

    dashboard.DashboardHandler.add_custom_get_action(
        base.ManualReviewBase.COURSE_STAFF_VIEW_ACTION,
        (manual_review_dashboard.ManualReviewDashboardHandler.
         view_manual_review_by_course_staff)
    )

    dashboard.DashboardHandler.add_custom_get_action(
        base.ManualReviewBase.ASSESSMENT_VIEW_ACTION,
        (manual_review_dashboard.ManualReviewDashboardHandler.
         view_manual_review_by_assessment)
    )

    dashboard.DashboardHandler.add_custom_get_action(
        base.ManualReviewBase.ASSIGN_ACTION,
        (manual_review_dashboard.ManualReviewDashboardHandler.
         assign_manual_review)
    )

    dashboard.DashboardHandler.add_custom_get_action(
        base.ManualReviewBase.DELETE_ACTION,
        (manual_review_dashboard.ManualReviewDashboardHandler.
         delete_manual_review)
    )

    dashboard.DashboardHandler.add_nav_mapping(
        base.ManualReviewBase.DASHBOARD_NAV, base.ManualReviewBase.NAME)

    # register cron handler
    cron_handlers = [
        (base.ManualReviewBase.ASSIGN_CRON_JOB_URL,
	     assign.AssignSubmissionHandler),
        (base.ManualReviewBase.REASSIGN_CRON_JOB_URL,
	     assign.ReassignSubmissionHandler),
        (base.ManualReviewBase.FIX_DRIVE_PERMISSIONS_CRON_JOB_URL,
         assign.FixDrivePermissionsHandler),
        (base.ManualReviewBase.CALCULATE_FINAL_SCORE_CRON_JOB_URL,
         assign.CalculateFinalScoreHandler),
        (base.ManualReviewBase.FIX_MISSING_MANUAL_EVALUATION_SUMMARY_CRON_JOB_URL,
         assign.FixMissingManualEvaluationSummaryHandler),
        (base.ManualReviewBase.FIX_NUM_ASSIGNED_CRON_JOB_URL,
         assign.FixNumAssignedHandler)]

    global custom_module
    custom_module = custom_modules.Module(
        'Manual Review Engine',
        'A set of classes for managing staff.manual_review process.',
        cron_handlers, [])
    return custom_module
