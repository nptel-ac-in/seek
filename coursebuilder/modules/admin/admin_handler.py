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

"""Presents a friendly base class for admin handlers."""

__authors__ = [
    'Nick Retallack (nretallack@google.com)'
    'Rishav Thakker (rthakker@google.com)'
]

from common import crypto
from modules.admin import admin


class AbstractGlobalAdminCustomAction(admin.GlobalAdminHandler):

    REGISTER_GET_ACTION = False
    REGISTER_POST_ACTION = False

    @classmethod
    def get(cls, handler):
        if not handler.can_view(cls.ACTION):
            if handler.app_context:
                handler.redirect(handler.app_context.get_slug(), abort=True)
            else:
                handler.redirect('/', abort=True)
            return False
        return True

    @classmethod
    def render_content(cls, handler, content):
        handler.render_page({
            'page_title': cls.PAGE_TITLE,
            'main_content': content,
        })

    @classmethod
    def post(cls, handler):
        # check for cross-site request forgery
        xsrf_token = handler.request.headers.get(
            'CSRF-Token', handler.request.get(
                'xsrf_token_{}'.format(handler.ACTION)))
        if not crypto.XsrfTokenManager.is_xsrf_token_valid(
                xsrf_token, cls.ACTION):
            handler.abort(403)
            return False

        # check permissions
        if not handler.can_edit(cls.ACTION):
            if handler.app_context:
                handler.redirect(handler.app_context.get_slug(), abort=True)
            else:
                handler.redirect('/', abort=True)
            return False
        return True

    @classmethod
    def add_to_menu(cls, group, item, title, **kwargs):
        cls.add_menu_item(
            group, item, title, action=cls.ACTION,
            href=cls.URL, **kwargs
        )
        if cls.REGISTER_GET_ACTION:
            cls.register_get_action()
        if cls.REGISTER_POST_ACTION:
            cls.register_post_action()

    @classmethod
    def register_get_action(cls):
        cls.add_custom_get_action(cls.ACTION, cls.get)

    @classmethod
    def register_post_action(cls):
        cls.add_custom_post_action(cls.ACTION, cls.post)
