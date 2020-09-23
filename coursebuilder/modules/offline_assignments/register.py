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

"""Methods related to module registration"""

__authors__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

import os
import appengine_config

from controllers import sites
from models import custom_modules
from models import custom_units
from modules.dashboard import dashboard
from modules.course_staff import evaluate
from modules.course_staff import course_staff
from modules.dashboard import tabs
from modules.offline_assignments import question
from modules.offline_assignments import base
from modules.offline_assignments import assignment
from modules.offline_assignments import dashboard as off_ass_dashboard
from modules.offline_assignments import settings
from modules.offline_assignments import course_staff as offline_course_staff

custom_unit = None
custom_module = None

def delete_assignement(course, unit):
    return question.OfflineAssignmentBaseHandler.delete_file(course, unit)

def visible_url(unit):
    return question.OfflineAssignmentBaseHandler.get_public_url(unit)

def import_assignment(src_course, src_unit, dst_course, dst_unit):
    content = question.OfflineAssignmentBaseHandler.get_content(
        src_course, src_unit)
    question.OfflineAssignmentBaseHandler.set_content(
        dst_course, dst_unit, content)

def register_module():
    """Registers this module in the registry."""

    # Course Dashboard
    tabs.Registry.register(
        base.OfflineAssignmentBase.DASHBOARD_NAV,
        base.OfflineAssignmentBase.DASHBOARD_TAB,
        base.OfflineAssignmentBase.DESCRIPTION,
        off_ass_dashboard.OfflineAssignmentDashboardHandler)

    dashboard.DashboardHandler.add_custom_get_action(
        base.OfflineAssignmentBase.DASHBOARD_DEFAULT_ACTION, None)

    dashboard.DashboardHandler.add_nav_mapping(
        base.OfflineAssignmentBase.DASHBOARD_NAV,
        base.OfflineAssignmentBase.NAME,
    )
    dashboard.DashboardHandler.add_custom_get_action(
        base.OfflineAssignmentBase.OFFLINE_ASSIGNMENT_DETAILS_ACTION,
        off_ass_dashboard.OfflineAssignmentDashboardHandler.get_assignment_scores
        )

    dashboard.DashboardHandler.add_custom_get_action(
        base.OfflineAssignmentBase.SCORE_OFFLINE_ASSIGNMENT_ACTION,
        off_ass_dashboard.OfflineAssignmentDashboardHandler.get_bulk_score
        )

    dashboard.DashboardHandler.add_custom_post_action(
        base.OfflineAssignmentBase.SCORE_OFFLINE_ASSIGNMENT_ACTION,
        off_ass_dashboard.OfflineAssignmentDashboardHandler.post_bulk_score
        )

    # Course Staff Custom Handlers
    evaluate.EvaluationHandler.add_custom_get_action(
        offline_course_staff.OfflineAssignmentsCourseStaffBase.LIST_ACTION,
        offline_course_staff.OfflineAssignmentsCourseStaffHandler.get_list_offline
    )

    evaluate.EvaluationHandler.add_custom_get_action(
        offline_course_staff.OfflineAssignmentsCourseStaffBase.EVALUATE_ACTION,
        offline_course_staff.OfflineAssignmentsCourseStaffHandler.get_evaluate_offline
    )

    evaluate.EvaluationHandler.add_custom_post_action(
        offline_course_staff.OfflineAssignmentsCourseStaffBase.POST_SCORE_ACTION,
        offline_course_staff.OfflineAssignmentsCourseStaffHandler.post_score_offline
    )

    associated_js_files_handlers = [
        ('/modules/offline_assignments/editor/(.*)', sites.make_zip_handler(
            os.path.join(
                appengine_config.BUNDLE_ROOT,
                'modules/offline_assignments/lib/ckeditor.zip'))),
        (
            settings.OfflineAssignmentRESTHandler.URI,
            settings.OfflineAssignmentRESTHandler
        )
        ]


    question_handlers = [
        (base.OfflineAssignmentBase.UNIT_URL,
         assignment.OfflineAssignmentHandler),
         (question.OfflineAssignmentRESTHandler.URI,
         question.OfflineAssignmentRESTHandler)]

    global custom_module
    custom_module = custom_modules.Module(
        base.OfflineAssignmentBase.NAME,
        base.OfflineAssignmentBase.DESCRIPTION,
        associated_js_files_handlers, question_handlers)

    custom_unit = custom_units.CustomUnit(
        base.OfflineAssignmentBase.UNIT_TYPE_ID,
        base.OfflineAssignmentBase.NAME,
        question.OfflineAssignmentRESTHandler,
        visible_url,
        cleanup_helper=delete_assignement,
        import_helper=import_assignment,
        is_graded=True)

    # Add custom unit details to course staff module
    course_staff.CourseStaff.add_custom_unit(
        base.OfflineAssignmentBase.UNIT_TYPE_ID,
        offline_course_staff.OfflineAssignmentsCourseStaffBase.LIST_ACTION)

    return custom_module
