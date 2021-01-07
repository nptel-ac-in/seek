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

"""Base class for local chapet module."""

__author__ = 'Thejesh GN (tgn@google.com)'

import os
import urllib
from common import jinja_utils

class LocalChapterBase(object):
    LINK_URL = 'dashboard'
    NAME = 'Local Chapters'
    DASHBOARD_NAV = 'local_chapter'
    DASHBOARD_SHOW_LIST_TAB = 'local_chapters'
    DASHBOARD_ADD_LOCAL_CHAPTER = 'add_local_chapter'
    DASHBOARD_BULK_ADD_LOCAL_CHAPTER = 'bulk_add_local_chapter'
    DASHBOARD_EDIT_LOCAL_CHAPTER = 'edit_local_chapter'
    DASHBOARD_DELETE_LOCAL_CHAPTER = 'delete_local_chapter'
    LOCAL_CHAPTER_SECTION = 'local_chapter'
    LOCAL_CHAPTER_ORG_COLLEGE = "college"
    LOCAL_CHAPTER_ORG_INDUSTRY = "industry"


    @classmethod
    def get_template(self, template_name, dirs):
        """Sets up an environment and Gets jinja template."""
        return jinja_utils.get_template(
            template_name, dirs + [os.path.dirname(__file__)])
