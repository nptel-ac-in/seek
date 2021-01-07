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

"""Base class for service account module."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import os
import urllib
from common import jinja_utils

class GoogleServiceAccountBase(object):
    LINK_URL = 'dashboard'
    NAME = 'Service Account'
    DESCRIPTION = ('Settings related to service account,'
        'such as google drive integration')
    DASHBOARD_NAV = 'google_service_account'
    DASHBOARD_SHOW_LIST_ACTION = 'google_service_account'
    DASHBOARD_SHOW_LIST_TAB = 'google_service_account'
    DASHBOARD_EDIT_SERVICE_ACCOUNT_ACTION = 'edit_google_service_account'
    DASHBOARD_PAGE_TITLE = 'Google Service Accounts'

    @classmethod
    def get_template(self, template_name, dirs):
        """Sets up an environment and Gets jinja template."""
        return jinja_utils.get_template(
            template_name, dirs + [os.path.dirname(__file__)])
