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

"""Classes and methods to serving programming assignment."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import os

from models import student_work
from models import entities
from models import transforms
from common import jinja_utils

from modules.subjective_assignments import question
from modules.course_staff import evaluate
from modules.manual_review import manage
from modules.manual_review import staff

class SubjectiveAssignmentCourseStaffBase(
        question.SubjectiveAssignmentBaseHandler):
    # TODO(rthakker) change these to list_subjective, list_evaluate and so on.
    LIST_ACTION = 'list'
    EVALUATE_ACTION = 'evaluate'
    POST_SCORE_ACTION = 'submit_score'
    POST_SAVE_ACTION = 'save_comments'

class SubjectiveAssignmentCourseStaffHandler(
        SubjectiveAssignmentCourseStaffBase):

    @classmethod
    def store_feedback(cls, handler, mark_completed):
        user = handler.current_user
        evaluator = handler.evaluator

        if not evaluator.can_grade:
            handler.error(404)
            handler.redirect('/course_staff')
            return

        key = handler.request.get('key')
        if not key:
            handler.error(404)
            handler.redirect('/course_staff')
            return

        step = entities.get(key)
        if not step:
            handler.error(404)
            handler.redirect('/course_staff')
            return

        if step.evaluator != user.user_id() and not evaluator.can_override:
            handler.error(404)
            handler.redirect('/course_staff')
            return

        score = 0
        course = handler.get_course()

        if handler.request.get('score'):
            score = float(handler.request.get('score'))

        manage.Manager.write_manual_review(
            step, handler.request.get('comments'), score, course,
            mark_completed=mark_completed)

    @classmethod
    def get_list_subjective(cls, handler):
        user = handler.current_user
        evaluator = handler.evaluator

        assignment_name = handler.request.get('name')
        course = handler.get_course()
        unit = course.find_unit_by_id(assignment_name)
        if not unit:
            handler.error(404)
            handler.redirect('/course')
            return

        show_evaluated = handler.request.get('show_evaluated')
        override = evaluator.can_override and handler.request.get('override')
        if evaluate.EvaluationHandler.can_evaluate(unit):
            handler.template_value['can_evaluate'] = True
            handler.template_value['show_evaluated'] = show_evaluated
            handler.template_value['show_override'] = evaluator.can_override and not override
            if override:
                override_work = staff.ManualEvaluationStep.all(
                    ).filter(
                        staff.ManualEvaluationStep.unit_id.name, assignment_name
                    ).filter('removed =', False
                    ).fetch(None)
                handler.template_value['override_work'] = override_work
            elif show_evaluated:
                completed_work = staff.ManualEvaluationStep.all(
                    ).filter(
                        staff.ManualEvaluationStep.evaluator.name, user.user_id()
                    ).filter(
                        staff.ManualEvaluationStep.state.name, staff.REVIEW_STATE_COMPLETED
                    ).filter(
                        staff.ManualEvaluationStep.unit_id.name, assignment_name
                    ).filter('removed =', False
                    ).fetch(None)
                handler.template_value['completed_work'] = completed_work
            else:
                pending_work = staff.ManualEvaluationStep.all(
                    ).filter(
                        staff.ManualEvaluationStep.evaluator.name, user.user_id()
                    ).filter(
			"%s != " % staff.ManualEvaluationStep.state.name,
                        staff.REVIEW_STATE_COMPLETED
                    ).filter(
                        staff.ManualEvaluationStep.unit_id.name, assignment_name
                    ).filter('removed =', False
                    ).fetch(None)
                handler.template_value['pending_work'] = pending_work
        else:
            handler.template_value['can_evaluate'] = False
        handler.template_value['unit'] = unit
        handler.template_value['unit_id'] = unit.unit_id


        template_file = 'templates/course_staff/evaluations.html'
        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__)])
        handler.render(template)

    @classmethod
    def get_evaluate_subjective(cls, handler):
        user = handler.current_user
        evaluator = handler.evaluator

        key = handler.request.get('key')
        if not key:
            handler.error(404)
            handler.redirect('/course_staff')
            return

        step = entities.get(key)
        if not step:
            handler.error(404)
            handler.redirect('/course_staff')
            return

        if step.evaluator != user.user_id() and not evaluator.can_override:
            handler.error(404)
            handler.redirect('/course_staff')
            return

        unit_id = step.unit_id
        course = handler.get_course()
        unit = course.find_unit_by_id(unit_id)
        if not unit:
            handler.error(404)
            handler.redirect('/course')
            return

        submission = student_work.Submission.get_contents_by_key(
            step.submission_key)
        if not submission:
            handler.error(404)
            handler.redirect('/course_staff')
            return
        content = cls.get_content(course, unit)
        submission_content = transforms.loads(submission)

        if cls.ESSAY == content[cls.OPT_QUESTION_TYPE]:
            handler.template_value['essay'] = submission_content['essay']
        else:
            if 'copied_file' in submission_content.keys():
                copied_file = submission_content['copied_file']
                # For backward compatibility, checking for both the following
                # cases:
                # 1. copied_file is a list
                # 2. copied_file is a dict (will get depreciated soon)
                if isinstance(copied_file, list):
                    handler.template_value['file_meta_list'] = copied_file
                else:
                    handler.template_value['file_meta_list'] = [copied_file]

        handler.template_value['save_comments_xsrf_token'] = handler.create_xsrf_token('save_comments')
        handler.template_value['submit_xsrf_token'] = handler.create_xsrf_token('submit_score')
        handler.template_value['reviewee'] = step.reviewee_key.id_or_name()
        handler.template_value['key'] = key
        handler.template_value['score'] = step.score if step.score else ''
        handler.template_value['comments'] = step.comments if step.comments else ''

        handler.template_value['unit'] = unit
        handler.template_value['unit_id'] = unit.unit_id

        template_file = 'templates/course_staff/evaluate.html'
        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__)])
        handler.render(template)

    @classmethod
    def post_save_comments(cls, handler):
        cls.store_feedback(handler, False)
        transforms.send_json_response(handler, 200, 'OK')


    @classmethod
    def post_submit_score(cls, handler):
        cls.store_feedback(handler, True)
        handler.redirect('/course_staff')
