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

"""Base class for manual review"""

__authors__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

from modules.subjective_assignments import question

class ManualReviewBase(object):
    NAME = 'Manual Review'
    DASHBOARD_NAV = 'manual_review'
    DASHBOARD_TAB = 'manual_review'
    COURSE_STAFF_VIEW_ACTION = 'manual_review_course_staff'
    ASSESSMENT_VIEW_ACTION = 'manual_review_assessment'
    DELETE_ACTION = 'delete_manual_review'
    ASSIGN_ACTION = 'assign_manual_review'
    SUPPORTED_UNIT_TYPES = [
        question.SubjectiveAssignmentBaseHandler.UNIT_TYPE_ID
    ]
    ASSIGN_CRON_JOB_URL = '/cron/manual_review/assign_review'
    REASSIGN_CRON_JOB_URL = '/cron/manual_review/reassign_review'
    FIX_DRIVE_PERMISSIONS_CRON_JOB_URL = (
        '/cron/manual_review/fix_drive_permissions')
    CALCULATE_FINAL_SCORE_CRON_JOB_URL = (
        '/cron/manual_review/calculate_final_score')
    FIX_MISSING_MANUAL_EVALUATION_SUMMARY_CRON_JOB_URL = (
        '/cron/manual_review/fix_missing_manual_evaluation_summary')
    FIX_NUM_ASSIGNED_CRON_JOB_URL = (
        '/cron/manual_review/fix_num_assigned')
