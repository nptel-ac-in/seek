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

"""Handlers for Adding/Removing Mentors for a course."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import os
import csv
import StringIO
import jinja2


from common import safe_dom
from controllers.utils import ApplicationHandler
from models.models import Student
from modules.mentor.mentor_model import Mentor
from modules.mentor import base
from modules.local_chapter import local_chapter_model


class MentorListHandler(base.MentorBase):
    """Mentor List Handler handler."""
    @classmethod
    def display_html(cls, handler):
        """Adds mentors for the instance."""
        template_values = {}
        template_values['page_title'] = handler.format_title('Mentors')
        possible_mentor_list = Mentor.get_all_mentors()
        if len(possible_mentor_list) > 0:
            template_values['mentors'] = possible_mentor_list

        template_values['remove_mentor_xsrf_token'] = (
            handler.create_xsrf_token('remove_mentor'))

        return jinja2.utils.Markup(
            handler.get_template(
                'views/mentor.html',
                [os.path.dirname(__file__)]).render(template_values))

    @classmethod
    def remove_mentor(cls, handler):
        mentor_id = handler.request.get('mentor_id')
        Mentor.delete_mentor(mentor_id)

	handler.redirect(handler.get_action_url(
            cls.DASHBOARD_NAV,
            extra_args={'tab': cls.DASHBOARD_SHOW_LIST_TAB}))

class AddMentorHandler(base.MentorBase):
    """Handler to add a new mentor"""

    @classmethod
    def display_html(cls, handler):
        template_values = {}
        template_values['page_title'] = handler.format_title('Add Mentors')
        template_values['add_mentors_xsrf_token'] = (
            handler.create_xsrf_token('add_mentors'))

        return jinja2.utils.Markup(
            handler.get_template(
                'views/mentor_add.html',
                [os.path.dirname(__file__)]).render(template_values))

    @classmethod
    def get_add_mentors_page(cls, handler):
        content = cls.display_html(handler)
        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_SHOW_LIST_TAB)

    @classmethod
    def parse_mentor_csv(cls, mentor_csv_text):
        """
        Parses the CSV text containing mentor email and local chapter ID
        and returns a list of tuples
        """
        temp_file = StringIO.StringIO(mentor_csv_text)
        csv_data = csv.reader(temp_file, delimiter=',')
        return csv_data

    @classmethod
    def add_mentors(cls, handler):
        template_values = {}
        template_values['page_title'] = handler.format_title('Added Mentors')
        mentor_email_lc_list = cls.parse_mentor_csv(
            handler.request.get('mentor_email_list'))

        added_mentors = []
        not_found_mentors = []

        for m in mentor_email_lc_list:
            if len(m) < 1:
                continue

            email = m[0].strip()
            if len(m) >= 2:
                college_id = m[1].strip()
            else:
                college_id = ''

            if not email:
                continue
            p = Student.get_by_email(email)
            if (p is None or (college_id and
                    local_chapter_model.LocalChapterDAO
                    .get_local_chapter_by_key(
                    college_id) is None)):
                not_found_mentors.append(email)
            else:
                mentor = Mentor.get_or_create(user_id=p.user_id)
                if college_id:
                    mentor.local_chapter = True
                    mentor.college_id = college_id
                else:
                    mentor.local_chapter = False
                mentor.put()
                added_mentors.append(email)

        content = safe_dom.NodeList()
        if len(added_mentors) > 0:
            content.append(
                safe_dom.Element('h3').add_text('Successfully added Mentors'))
            l = safe_dom.Element('ol')
            for m in added_mentors:
                l.add_child(safe_dom.Element('li').add_text(m))
            content.append(l)

        if len(not_found_mentors) > 0:
            content.append(
                safe_dom.Element('h3').add_text('Mentor Addition Failed'))
            l = safe_dom.Element('ol')
            for m in not_found_mentors:
                l.add_child(safe_dom.Element('li').add_text(m))
            content.append(l)

        if len(not_found_mentors) == 0 and len(added_mentors) == 0:
            content.append(
                safe_dom.Element('h3').add_text(
                    'No Emails specified for adding to mentor list'))

        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_SHOW_LIST_TAB)
