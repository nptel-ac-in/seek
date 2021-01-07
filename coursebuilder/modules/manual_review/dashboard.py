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

"""Contain dashboard related classes for manual review."""

__authors__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

import os
import json
import jinja2

from google.appengine.ext import db

from models import roles
from models import transforms
from models import models
from modules.course_staff import course_staff
from modules.manual_review import base
from modules.manual_review import staff
from modules.manual_review import manage
from modules.student_list import base as student_list_base

# STUDENT_LIST_ENABLED = False
STUDENT_LIST_ENABLED = True

# TODO(rthakker) Find a better way to see if the module is registered.
# This does not work in v10.5
# if 'modules.student_list.register' in os.environ['GCB_REGISTERED_MODULES']:
#     from modules.student_list import base as student_list_base
#     STUDENT_LIST_ENABLED = True

class ManualReviewDashboardHandler(base.ManualReviewBase):
    """Handler for Manual Review"""

    @classmethod
    def display_html(cls, handler):

        if not roles.Roles.is_course_admin(handler.app_context):
            return 'Forbidden'

        course = handler.get_course()
        if not course:
            return 'Course not found'

        template_value = dict()
        # Get a list of subjective assignments
        units = []
        for unit in course.get_units():
            if not unit.is_custom_unit():
                continue
            if unit.custom_unit_type in cls.SUPPORTED_UNIT_TYPES:
                units.append(unit)

        template_value['units'] = units
        # Get a list of course staff
        possible_course_staff_list = course_staff.CourseStaff.all().fetch(None)
        if possible_course_staff_list:
            template_value['course_staff_list'] = possible_course_staff_list

        # Cron Job urls
        assign_cron_job_url = '%s?namespace=%s' % (
            base.ManualReviewBase.ASSIGN_CRON_JOB_URL,
            handler.app_context.namespace)
        template_value['assign_cron_job_url'] = assign_cron_job_url

        reassign_cron_job_url = '%s?namespace=%s' % (
            base.ManualReviewBase.REASSIGN_CRON_JOB_URL,
            handler.app_context.namespace)
        template_value['reassign_cron_job_url'] = reassign_cron_job_url

        calculate_final_score_cron_job_url = '%s?namespace=%s' % (
            base.ManualReviewBase.CALCULATE_FINAL_SCORE_CRON_JOB_URL,
            handler.app_context.namespace)
        template_value['calculate_final_score_cron_job_url'] = (
            calculate_final_score_cron_job_url)

        return jinja2.utils.Markup(
            handler.get_template(
                'templates/list.html',
                [os.path.dirname(__file__)]).render(template_value))

    @classmethod
    def view_manual_review_by_course_staff(cls, handler):

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '403 Unauthorized'
            })
            return

        course = handler.get_course()
        key = handler.request.get('key')
        cs = None
        if key:
            cs = course_staff.CourseStaff.get_by_key_name(key)
        if not cs:
            handler.redirect(handler.get_action_url(
                cls.DASHBOARD_CATEGORY + '_' + cls.DASHBOARD_NAV))
            return

        template_value = dict()
        template_value['course_staff'] = cs

        units = []
        for unit in course.get_units():
            if not unit.is_custom_unit():
                continue
            if unit.custom_unit_type in cls.SUPPORTED_UNIT_TYPES:
                units.append(unit)
        template_value['units'] = units

        template_value['view_by_assessment_action'] = handler.get_action_url(
            cls.ASSESSMENT_VIEW_ACTION)
        template_value['dashboard_home_action'] = handler.get_action_url(
            cls.DASHBOARD_CATEGORY + '_' + cls.DASHBOARD_NAV)

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/view_by_course_staff.html',
                [os.path.dirname(__file__)]).render(template_value))
        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV)

    @classmethod
    def view_manual_review_by_assessment(cls, handler):

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '403 Unauthorized'
            })
            return

        course = handler.get_course()
        key = handler.request.get('key')
        evaluator_id = handler.request.get('evaluator_id')
        unit = None
        if key:
            unit = course.find_unit_by_id(key)
        if not unit:
            handler.redirect(handler.get_action_url(
                cls.DASHBOARD_CATEGORY + '_' + cls.DASHBOARD_NAV))
            return

        template_value = dict()
        template_value['unit'] = unit

        assigned_reviews_filter = staff.ManualEvaluationStep.all().filter(
            'unit_id =', key
        ).filter('removed =', False)

        removed_reviews_filter = staff.ManualEvaluationStep.all().filter(
            'unit_id =', key
        ).filter('removed =', True)

        if evaluator_id:
            assigned_reviews_filter = assigned_reviews_filter.filter(
                'evaluator =', evaluator_id)
            removed_reviews_filter = removed_reviews_filter.filter(
                'evaluator =', evaluator_id)

            # Need to show unassigned reviews only when they're not specific to
            # a course staff
            unassigned_reviews = []
            template_value['evaluator'] = (
                models.StudentProfileDAO.get_profile_by_user_id(evaluator_id))
        else:
            unassigned_reviews_filter = staff.ManualEvaluationSummary.all(
            ).filter(
                'completed_count =', 0
            ).filter('assigned_count =', 0
            ).filter('expired_count =', 0
            ).filter('unit_id =', key)

            unassigned_reviews = unassigned_reviews_filter.fetch(None)

        assigned_reviews = assigned_reviews_filter.fetch(None)
        removed_reviews = removed_reviews_filter.fetch(None)

        assigned_reviews_dict = dict()
        for review in assigned_reviews:
            if review.reviewee_key.name() not in assigned_reviews_dict:
                assigned_reviews_dict[review.reviewee_key.name()] = [review]
            else:
                assigned_reviews_dict[review.reviewee_key.name()].append(review)

        assigned_student_key_names = [
            r.reviewee_key.name() for r in assigned_reviews]
        unassigned_student_key_names = [
            r.reviewee_key.name() for r in unassigned_reviews]
        removed_student_key_names = [
            r.reviewee_key.name() for r in removed_reviews]
        required_student_key_names = list(set(
            assigned_student_key_names + unassigned_student_key_names +
            removed_student_key_names))

        assigned_ids = [step.evaluator for step in assigned_reviews]
        evaluator_profiles = (
            models.StudentProfileDAO.bulk_get_student_profile_by_id(
                assigned_ids))

        removed_ids = [step.evaluator for step in removed_reviews]
        removed_evaluator_profiles = (
            models.StudentProfileDAO.bulk_get_student_profile_by_id(
                removed_ids))

        all_evaluator_profiles_dict = dict((e.user_id, e) for e in (
            evaluator_profiles + removed_evaluator_profiles) if e)


        template_value['assigned_reviews'] = assigned_reviews
        template_value['assigned_reviews_dict'] = assigned_reviews_dict
        template_value['removed_reviews'] = removed_reviews
        template_value['unassigned_reviews'] = unassigned_reviews
        template_value['evaluator_profiles'] = evaluator_profiles
        template_value['all_evaluator_profiles_dict'] = (
            all_evaluator_profiles_dict)
        template_value['removed_evaluator_profiles'] = (
            removed_evaluator_profiles)

        possible_course_staff_list = course_staff.CourseStaff.all().fetch(None)
        if possible_course_staff_list:
            course_staff_id_list = [
                cs.user_id for cs in possible_course_staff_list]
            course_staff_profiles = (
                models.StudentProfileDAO.
                bulk_get_student_profile_by_id(course_staff_id_list))
            template_value['course_staff_profiles'] = course_staff_profiles

        template_value['delete_action'] = handler.get_action_url(
            cls.DELETE_ACTION)
        template_value['assign_action'] = handler.get_action_url(
            cls.ASSIGN_ACTION)
        template_value['dashboard_home_action'] = handler.get_action_url(
            cls.DASHBOARD_CATEGORY + '_' + cls.DASHBOARD_NAV)

        if STUDENT_LIST_ENABLED:
            template_value['student_details_action'] = handler.get_action_url(
                student_list_base.StudentListBase.DETAILS_ACTION)

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/view_by_unit.html',
                [os.path.dirname(__file__)]).render(template_value))

        handler.render_page(
            {
                'page_title': handler.format_title(cls.NAME),
                'main_content': content},
            in_action=cls.DASHBOARD_NAV)

    @classmethod
    def assign_manual_review(cls, handler):
        """Assigns a manual review"""

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '403 Unauthorized'
            })
            return

        reviewee_key = handler.request.get('reviewee_key')
        unit_id = handler.request.get('unit_id')
        evaluator_id = handler.request.get('evaluator_id')
        evaluator_email = handler.request.get('evaluator_email')

        if not (reviewee_key and unit_id):
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '400 Bad Request missing Invalid params'
            })
            return

        if not evaluator_id:
            if evaluator_email:
                evaluator_student, is_unique = (
                    models.Student.get_first_by_email(evaluator_email))
                evaluator_id = evaluator_student.user_id

        course = handler.get_course()
        unit = course.find_unit_by_id(unit_id)
        student = models.Student.get(reviewee_key)
        if None in (course, unit, student):
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '404 Not found course or unit or student'
            })
            return
        if manage.Manager.submit_for_evaluation(course, unit, student,
                evaluator_id=evaluator_id):
            template_value = {
                'message': ('Successfully assigned manual review for student %s'
                            % (student.email))
            }
        else:
            handler.error(404)
            template_value = {
                'message': ('Could not find any course staff for %s'
                                 % student.email)
            }

        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/result.html',
                [os.path.dirname(__file__)]).render(template_value))
        handler.render_page({
            'page_title': handler.format_title(cls.NAME),
            'main_content': content
        })

    @classmethod
    def delete_manual_review(cls, handler):
        """Detelets a manual review step"""

        if not roles.Roles.is_course_admin(handler.app_context):
            handler.error(403)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '403 Unauthorized'
            })
            return

        key = handler.request.get('key')
        if not key:
            handler.error(400)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '400 Bad Request missing `key` param'
            })
            return

        # TODO(rthakker) add xsrf
        try:
            manage.Manager.delete_manual_evaluator(key)
        except Exception as e:
            handler.error(404)
            handler.render_page({
                'page_title': handler.format_title(cls.NAME),
                'main_content': '404 Not found'
            })
            return

        template_value = {
            'message': 'Successfully removed manual review'
        }
        content = jinja2.utils.Markup(
            handler.get_template(
                'templates/result.html',
                [os.path.dirname(__file__)]).render(template_value))
        handler.render_page({
            'page_title': handler.format_title(cls.NAME),
            'main_content': content
        })
