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

"""Methods to register Local Chapter module."""

__author__ = 'Thejesh GN (tgn@google.com)'

from controllers import sites
from controllers.utils import BaseHandler
from controllers.utils import ReflectiveRequestHandler
from controllers.utils import XsrfTokenManager
from models import custom_modules
from models import transforms
from models.models import Student
from modules.admin import admin
from modules.local_chapter import base
from modules.local_chapter import local_chapter
from modules.courses import settings as course_settings

# Module registration
custom_module = None

def register_module():
    """Registers this module in the registry."""

    global_routes = [
        (local_chapter.LocalChapterRESTHandler.URI,
         local_chapter.LocalChapterRESTHandler),
        (local_chapter.AddNewLocalChapterRESTHandler.URI,
         local_chapter.AddNewLocalChapterRESTHandler),
        (local_chapter.BulkAddNewLocalChapterRESTHandler.URI,
         local_chapter.BulkAddNewLocalChapterRESTHandler)
    ]

    admin.BaseAdminHandler.add_menu_item(
        'analytics', 'local_chapters', 'Local Chapters',
        action='local_chapters', sub_group_name='advanced')

    admin.GlobalAdminHandler.add_custom_get_action('local_chapters',
        local_chapter.LocalChapterBaseAdminHandler.local_chapters)
    admin.GlobalAdminHandler.add_custom_get_action('bulk_add_local_chapter',
        local_chapter.LocalChapterBaseAdminHandler.bulk_add_local_chapter)
    admin.GlobalAdminHandler.add_custom_get_action('add_local_chapter',
        local_chapter.LocalChapterBaseAdminHandler.add_local_chapter)
    admin.GlobalAdminHandler.add_custom_get_action('edit_local_chapter',
        local_chapter.LocalChapterBaseAdminHandler.edit_local_chapter)

    global custom_module
    custom_module = custom_modules.Module(
        base.LocalChapterBase.NAME,
        'Provides Local Chapter support',
        global_routes, [])
    return custom_module


@classmethod
def unregister_module():
    """Unregisters this module in the registry."""
    global custom_module
    admin.GlobalAdminHandler.remove_custom_get_action('local_chapters')
    admin.GlobalAdminHandler.remove_custom_get_action('bulk_add_local_chapter')
    admin.GlobalAdminHandler.remove_custom_get_action('add_local_chapter')
    admin.GlobalAdminHandler.remove_custom_get_action('edit_local_chapter')
    return custom_modules
