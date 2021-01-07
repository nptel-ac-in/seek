# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Custom handlers needed for student list."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import os
import logging
import jinja2

from google.appengine.ext import db
from google.appengine.api import namespace_manager



class InteractiveTableHandler(object):
    """
    Displays data in a nice tabular format.

    Use this class as a mix-in with any webapp2.RequestHandler for
    a tabular display of data.
    """

    CURSOR_PARAM = 'cursor'
    NUM_ENTRIES_PARAM = 'num'
    DEFAULT_NUM_ENTRIES = '50'
    REVERSE_QUERY_PARAM = 'reverse_query'
    ORDER_PARAM = 'order'
    SEARCH_STR_PARAM = 'q'

    TEMPLATE_FILE = 'templates/profile_list.html'
    TEMPLATE_DIRS = [os.path.dirname(__file__)]

    NAME = 'Override this'
    IN_ACTION = 'Override this'
    LIST_ACTION = 'Override this'
    DETAILS_ACTION = 'Override this'
    DEFAULT_ORDER = 'Override this'

    # Override if required. If set to None, the functions will not change the
    # existing namespace
    TARGET_NAMESPACE = None

    @classmethod
    def get_reverse_order(cls, order):
        if not order:
            return None
        if order[0] == '-':
            return order[1:]
        else:
            return '-' + order


    @classmethod
    def get_by_search_str(cls, search_str):
        """
        This method is called to retrieve search results when
        cls.SEARCH_STR_PARAM is provided in the request.

        Override this.
        """
        raise NotImplementedError

    @classmethod
    def run_query(cls, cursor=None):
        """
        This function is called to run a query on the database when
        no cls.SEARCH_STR_PARAM is provided in the url.

        Override this.
        """
        raise NotImplementedError

    @classmethod
    def post_query_fn(cls, objects, template_value):
        """
        This function is called just after performing the query.
        Returns the modified 'objects' variable.

        Override if required.
        """
        return objects

    @classmethod
    def generate_table(cls, handler, template_value, **kwargs):
        """Generates table data in template_value"""

        try:
            cursor = handler.request.get(cls.CURSOR_PARAM)
            no_of_entries = handler.request.get(
                cls.NUM_ENTRIES_PARAM, cls.DEFAULT_NUM_ENTRIES)
            if no_of_entries == 'all':
                no_of_entries = None
            else:
                no_of_entries = int(no_of_entries)
            reverse_query = handler.request.get(cls.REVERSE_QUERY_PARAM)
        except ValueError:
            return False

        order = handler.request.get(cls.ORDER_PARAM, cls.DEFAULT_ORDER)
        search_str = handler.request.get(cls.SEARCH_STR_PARAM)

        objects = None
        query = None
        new_cursor = None
        last_page = False
        old_namespace = None

        if cls.TARGET_NAMESPACE is not None:
            old_namespace = namespace_manager.get_namespace()
            namespace_manager.set_namespace(cls.TARGET_NAMESPACE)

        if search_str:
            # Settings offset and no_of_entries manually
            no_of_entries = 1
            obj = cls.get_by_search_str(search_str)
            if obj:
                objects = [obj]
            else:
                objects = []

            last_page = True
        else:
            try:
                query = cls.run_query(cursor=cursor, **kwargs)
                if query:
                    if reverse_query:
                        query = query.order(
                            cls.get_reverse_order(order))
                    else:
                        query = query.order(order)

                    objects = query.fetch(no_of_entries)

                    if reverse_query:
                        objects.reverse()
                        new_cursor = cursor
                        cursor = query.cursor()
                    else:
                        new_cursor = query.cursor()
                else:
                    logging.error('run_query returned None')
                    objects = []

            except db.PropertyError as e:
                logging.error('Failed to query objects %s', e)
                return False

        if cls.TARGET_NAMESPACE is not None:
            namespace_manager.set_namespace(old_namespace)

        objects = cls.post_query_fn(objects, template_value)

        invert_order = order[0] == '-'
        order = order.replace('-', '')

        template_value['objects'] = objects
        template_value['new_cursor'] = new_cursor
        template_value['cursor'] = cursor
        template_value['no_of_entries'] = 'all' if no_of_entries is None else no_of_entries
        template_value['order'] = order
        template_value['invert_order'] = invert_order
        # TODO(rthakker) make search by user_id default.
        # Also need to edit the templates accordingly.
        template_value['search_str'] = search_str

        template_value['list_action'] = cls.LIST_ACTION
        template_value['details_action'] = cls.DETAILS_ACTION
        return True

    @classmethod
    def classmethod_render_table(cls, handler, template_value, **kwargs):
        """Renders data in a tabular format"""

        if not cls.generate_table(handler, template_value, **kwargs):
            handler.error(400)
            handler.render_page({
                'page_title': cls.NAME,
                'main_content': 'Invalid parameters'
            })

        content = jinja2.utils.Markup(
            handler.get_template(
                cls.TEMPLATE_FILE,
                cls.TEMPLATE_DIRS).render(template_value))

        handler.render_page({
            'page_title': cls.NAME,
            'main_content': content,
            'in_action': cls.IN_ACTION
        })

    def render_table(self, template_value, **kwargs):
        """
        This function will work only if this class is used as a mix-in with
        another Handler class
        """
        self.classmethod_render_table(self, template_value, **kwargs)
