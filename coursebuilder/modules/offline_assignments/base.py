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

"""Classes containing metadata about OfflineAssignments"""

import os
from common import jinja_utils

__authors__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

class OfflineAssignmentBase(object):
    UNIT_TYPE_ID = 'com.google.coursebuilder.offline_assignment'
    UNIT_URL = '/offline_assignment'
    NAME = 'Offline Assignment'
    DESCRIPTION = 'Offline Assignment'

    OPT_QUESTION_TYPE = "type"
    LIST_OFFLINE_ASSIGNMENT_ACTION = 'list_offline_assignment'
    OFFLINE_ASSIGNMENT_DETAILS_ACTION = 'offline_assignment_details'
    SCORE_OFFLINE_ASSIGNMENT_ACTION = 'score_offline_assignment'

    DASHBOARD_NAV = 'offline_assignment'
    DASHBOARD_TAB = 'offline_assignment'
    DASHBOARD_DEFAULT_ACTION = 'offline_assignment'
    DASHBOARD_CATEGORY = 'analytics'

    ADMIN_NAV = 'admin_offline_assignment'
    ADMIN_ACTION = 'admin_offline_assignment'
    ADMIN_CATEGORY = 'analytics'
    ADMIN_SUBGROUP = 'advanced'
    ADMIN_NAME = ADMIN_DESCRIPTION = 'Bulk Score Offline Assignments'

    @classmethod
    def get_template(cls, template_name, dirs):
        """Sets up an environment and gets jinja template"""
        return jinja_utils.get_template(
            template_name, dirs + [os.path.dirname(__file__)])
