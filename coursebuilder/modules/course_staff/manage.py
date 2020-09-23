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

"""Handlers for Adding/Removing Course Staffs for a course."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import os
import jinja2

from common import safe_dom
from models import models
from modules.course_staff import base
from modules.manual_review import assign

import course_staff

class CourseStaffDashboardHandler(base.CourseStaffBase):
    @classmethod
    def display_html(cls, handler):
        template_values = {}
        template_values['page_title'] = 'Manage Course Staff'
        possible_course_staff_list = course_staff.CourseStaff.all().fetch(None)
        if len(possible_course_staff_list) > 0:
            template_values['course_staff_list'] = possible_course_staff_list

        template_values['add_course_staff_xsrf_token'] = (
            handler.create_xsrf_token('add_course_staff'))
        template_values['remove_course_staff_xsrf_token'] = (
            handler.create_xsrf_token('remove_course_staff'))

        template_values['course_staff_not_allowed_to_grade_xsrf_token'] = (
            handler.create_xsrf_token('course_staff_not_allowed_to_grade'))
        template_values['course_staff_allowed_to_grade_xsrf_token'] = (
            handler.create_xsrf_token('course_staff_allowed_to_grade'))
        template_values['course_staff_can_not_override_xsrf_token'] = (
            handler.create_xsrf_token('course_staff_can_not_override'))
        template_values['course_staff_can_override_xsrf_token'] = (
            handler.create_xsrf_token('course_staff_can_override'))
        return jinja2.utils.Markup(
            handler.get_template(
                'templates/course_staff_list.html',
                [os.path.dirname(__file__)]).render(template_values))


    @classmethod
    def add_course_staff(cls, handler):
        template_values = {}
        template_values['page_title'] = 'Added Course Staffs'
        course_staff_email_list = handler.request.get('course_staff_email_list')
        emails = course_staff_email_list.split('\n')
        added_course_staff_list = []
        not_found_course_staff_list = []

        for e in emails:
            email = e.strip()
            if not email:
                continue
            p = models.StudentProfileDAO.get_profile_by_email(email)
            if p is None:
                not_found_course_staff_list.append(email)
            elif not course_staff.CourseStaff.get(p):
                cs = course_staff.CourseStaff.create(p)
                cs.can_grade = True
                cs.email = email
                cs.put()
                added_course_staff_list.append(email)

        content = safe_dom.NodeList()
        if len(added_course_staff_list) > 0:
            content.append(
                safe_dom.Element('h3').add_text('Successfully added Course Staffs'))
            l = safe_dom.Element('ol')
            for m in added_course_staff_list:
                l.add_child(safe_dom.Element('li').add_text(m))
            content.append(l)

        if len(not_found_course_staff_list) > 0:
            content.append(
                safe_dom.Element('h3').add_text('Course Staff Addition Failed'))
            l = safe_dom.Element('ol')
            for m in not_found_course_staff_list:
                l.add_child(safe_dom.Element('li').add_text(m))
            content.append(l)

        if len(not_found_course_staff_list) == 0 and len(added_course_staff_list) == 0:
            content.append(
                safe_dom.Element('h3').add_text(
                    'No Emails specified for adding to course_staff list'))

        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV,
            in_tab=cls.DASHBOARD_SHOW_LIST_TAB)


    @classmethod
    def remove_course_staff(cls, handler):
        course_staff_id = handler.request.get('course_staff_id')

        p = course_staff.CourseStaff.get(course_staff_id)
        if p:
            p.delete()
            # Reassign all associated ManualReviewStep objects.
            job = assign.ReassignSubmissionByCourseStaff(
                handler.app_context, [course_staff_id])
            job.submit()
            handler.redirect(handler.get_action_url(
                cls.DASHBOARD_NAV,
                extra_args={'tab': cls.DASHBOARD_SHOW_LIST_TAB}))

    @classmethod
    def course_staff_not_allowed_to_grade(cls, handler):
        course_staff_id = handler.request.get('course_staff_id')

        p = course_staff.CourseStaff.get(course_staff_id)
        if p:
            p.can_grade = False
            p.put()
	handler.redirect(handler.get_action_url(
            cls.DASHBOARD_NAV,
            extra_args={'tab': cls.DASHBOARD_SHOW_LIST_TAB}))

    @classmethod
    def course_staff_allowed_to_grade(cls, handler):
        course_staff_id = handler.request.get('course_staff_id')

        p = course_staff.CourseStaff.get(course_staff_id)
        if p:
            p.can_grade = True
            p.put()
	handler.redirect(handler.get_action_url(
            cls.DASHBOARD_NAV,
            extra_args={'tab': cls.DASHBOARD_SHOW_LIST_TAB}))

    @classmethod
    def course_staff_can_override(cls, handler):
        course_staff_id = handler.request.get('course_staff_id')

        p = course_staff.CourseStaff.get(course_staff_id)
        if p:
            p.can_override = True
            p.put()
	handler.redirect(handler.get_action_url(
            cls.DASHBOARD_NAV,
            extra_args={'tab': cls.DASHBOARD_SHOW_LIST_TAB}))

    @classmethod
    def course_staff_can_not_override(cls, handler):
        course_staff_id = handler.request.get('course_staff_id')

        p = course_staff.CourseStaff.get(course_staff_id)
        if p:
            p.can_override = False
            p.put()
	handler.redirect(handler.get_action_url(
            cls.DASHBOARD_NAV,
            extra_args={'tab': cls.DASHBOARD_SHOW_LIST_TAB}))
