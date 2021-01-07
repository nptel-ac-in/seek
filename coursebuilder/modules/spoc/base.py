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

"""Base class for SPOC."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

from models import config

custom_module = None

GLOBAL_SPOC_EMAILS = config.ConfigProperty(
    'global_spoc_emails', str,
    'Global SPOC Emails'
    '', '', label='Global SPOC Emails')

SPOC_UPDATE_SCHOLARSHIP = config.ConfigProperty(
    'spoc_update_scholarship', bool,
    'Allow SPoC to enable/disable scholarship status', False)

class SPOCBase(object):
    MODULE_NAME = 'Local Chapter SPOC'
    SPOC_PERMISSION = 'local_chapter_spoc'
    SPOC_ROLE_NAME = 'Local Chapter SPOC'
    SPOC_ROLE_PERMISSIONS = [
        SPOC_PERMISSION
    ]
    SCOPE_ADMIN = 'admin'
    DASHBOARD_LIST_ACTION = 'spoc_student_list'
