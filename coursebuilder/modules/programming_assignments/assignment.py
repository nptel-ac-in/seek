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

"""Classes and methods to serve Programming Assignments."""

__author__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Ambika Agarwal (ambikaagarwal@google.com)']


import copy
import datetime
import os
import urllib

from common import jinja_utils
from controllers.utils import BaseHandler
from controllers.utils import HUMAN_READABLE_DATETIME_FORMAT
from controllers.utils import ReflectiveRequestHandler
from models import roles
from models import student_work
from models import transforms
from modules.programming_assignments import base
from modules.programming_assignments import evaluator
from modules.programming_assignments import prog_models
from modules.programming_assignments import result
from modules.nptel import timezones


class ProgAssignmentHandler(BaseHandler, base.ProgAssignment,
                            ReflectiveRequestHandler):
    """Handler for prog assignment."""

    default_action = 'list'
    get_actions = [default_action, 'edit']
    post_actions = ['submit', 'save_code']

    def get_action_url(self, action, name, extra_args=None):
        args = {}
        args['action'] = action
        if name:
            args['name'] = name
        if extra_args:
            args.update(extra_args)
        return self.canonicalize_url(
            '%s?%s' % (self.UNIT_URL, urllib.urlencode(args)))

    def get_edit_url(self, name):
        args = {}
        args['unit_type'] = self.UNIT_TYPE_ID
        args['action'] = 'edit_custom_unit'
        args['key'] = name
        return self.canonicalize_url(
            '%s?%s' % ('/dashboard', urllib.urlencode(args)))


    @classmethod
    def submit_student_answer(cls, unit, student, lang, answer):
        answer_dict = dict()
        answer_dict[lang] = answer
        student_work.Submission.write(
            unit.unit_id, student.get_key(), transforms.dumps(answer_dict))

    @classmethod
    def get_student_answer(cls, unit, student):
        submitted_contents = student_work.Submission.get_contents(
                unit.unit_id, student.get_key())
        if submitted_contents:
            return transforms.loads(submitted_contents)
        return dict()

    @classmethod
    def get_server_response(cls, student, unit_id):
        answer_entity = prog_models.ProgrammingAnswersEntity.get(
            student, unit_id)
        if not answer_entity:
            return None
        return result.ProgramEvaluationResult.deserialize(answer_entity.data)

    @classmethod
    def get_evaluation_result(cls, course, unit, content, student, is_public,
                              lang, filename, answer):
        """Evaluates the programming assignment answer using some evaluator"""

        course_settings = cls.get_course_settings(course)

        # Default to nsjail
        evaluator_id = content.get('evaluator', 'nsjail')
        evaluator_class = evaluator.ProgramEvaluatorRegistory.get(evaluator_id)

        if not evaluator_class:
            evaluation_result = result.ProgramEvaluationResult()
            evaluation_result.set_status(result.Status.BACKEND_ERROR)
        else:
            prog_evaluator = evaluator_class(
                course, course_settings, unit, content)
            evaluation_result = prog_evaluator.evaluate(
                student, is_public, lang, filename, answer)

        return evaluation_result

    def parse_result(self, student, unit, tests):
        if not self.request.get('show_result'):
            return None
        evaluation_result = self.get_server_response(student, unit.unit_id)
        if (result.Status.BACKEND_ERROR == evaluation_result.status
            or result.Status.OTHER == evaluation_result.status):
            return None
        return evaluation_result

    def has_deadline_passed(self, unit):
        submission_due_date = unit.workflow.get_submission_due_date()
        if submission_due_date:
            time_now = datetime.datetime.now()
            if time_now > submission_due_date:
                return True
        return False

    def get_users_prog_lang_choice(self, saved_contents, submitted_contents):
        if self.request.get('lang'):
            return self.request.get('lang')

        if saved_contents and len(saved_contents.keys()) == 1:
            return saved_contents.keys()[0]

        if submitted_contents and len(submitted_contents.keys()) == 1:
            return submitted_contents.keys()[0]


    def _validate_request(self, supports_transient_student):
        student = self.personalize_page_and_get_enrolled(
            supports_transient_student=supports_transient_student)
        course = None
        unit = None
        if not student:
            self.error(404)
            return False, student, course, unit

        if not student.is_transient and not student.user_id:
            student.user_id = self.get_user().user_id()

        course = self.get_course()
        if not course:
            self.error(404)
            return False, student, course, unit

        assignment_name = self.request.get('name')
        unit = course.find_unit_by_id(assignment_name)
        if not unit:
            self.error(404)
            return False, student, course, unit
        return True, student, course, unit


    def get_list(self):
        success, student, course, unit = self._validate_request(True)
        if not success:
            return
        self.assignment_name = self.request.get('name')
        assignment = {}
        if self.request.get('answer'):
            assignment['answer'] = self.request.get('answer')


        content = self.get_content(course, unit)
        readonly_view = student.is_transient
        due_date_exceeded = False

        submission_due_date = unit.workflow.get_submission_due_date()
        private_tests_with_solutions = []
        if submission_due_date:
            assignment['submission_due_date'] = (
                submission_due_date.replace(tzinfo=timezones.UTC).astimezone(timezones.IST).strftime(
                    HUMAN_READABLE_DATETIME_FORMAT))

            if self.has_deadline_passed(unit):
                readonly_view = True
                due_date_exceeded = True
                private_tests_with_solutions = content['private_testcase']

        assignment['due_date_exceeded'] = due_date_exceeded
        self.template_value['readonly'] = readonly_view

        if not student.is_transient:
            saved_contents = prog_models.SavedProgrammingCodeEntity.get_code(
                student, unit.unit_id)
        else:
            saved_contents = None

        all_lang_data = dict()
        for l in content.get('allowed_languages', []):
            language_code = l['language']
            if language_code not in self.ALLOWED_LANGUAGES:
                continue
            per_lang_data = copy.deepcopy(l)
            per_lang_data['name'] = self.PROG_LANG_FILE_MAP[language_code]
            per_lang_data['syntax'] = self.PROG_LANG_SYNTAX_MAP[language_code]
            per_lang_data['syntax_mode'] = self.PROG_LANG_SYNTAX_MODE[language_code]
            if saved_contents and language_code in saved_contents.keys():
                code = saved_contents[language_code]['code']
                filename = saved_contents[language_code]['filename']
                per_lang_data['saved_code'] = code
                per_lang_data['filename'] = filename
                per_lang_data['last_code'] = (
                    evaluator.ProgramEvaluator.get_full_code(
                        per_lang_data, code))
            elif per_lang_data['code_template']:
                per_lang_data['saved_code'] = per_lang_data['code_template']
            else:
                per_lang_data['saved_code'] = ''

            if ('show_sample_solution' in content and
                content['show_sample_solution'] and
                per_lang_data['sample_solution']):
                assignment['has_sample_solution'] = True
                per_lang_data['solution'] = (
                    evaluator.ProgramEvaluator.get_full_code(
                        per_lang_data, per_lang_data['sample_solution']))
            all_lang_data[language_code] = per_lang_data

        assignment['all_lang_data'] = all_lang_data

        if not student.is_transient:
            submitted_contents = self.get_student_answer(unit, student)
        else:
            submitted_contents = None
        if submitted_contents:
            submitted_lang = submitted_contents.keys()[0]
            if submitted_lang in all_lang_data.keys():
                if readonly_view:
                    submitted_code = submitted_contents[submitted_lang]['code']
                    assignment['previous_submission_lang'] = submitted_lang
                    assignment['previous_submission'] = (
                        evaluator.ProgramEvaluator.get_full_code(
                            all_lang_data[submitted_lang], submitted_code))

        if ((readonly_view or self.request.get('post_submit')) and
            not student.is_transient):
            score = course.get_score(student, unit.unit_id)
            if score is not None:
	        assignment['score'] = '%s' % (float(score))

        if len(content) > 0:
            assignment['question'] = content['question']
            tests = content['public_testcase']
        else:
            tests = []
        assignment['sample_tests'] = tests + private_tests_with_solutions

        if roles.Roles.is_course_admin(self.app_context):
            assignment['edit_action'] = self.get_edit_url(unit.unit_id)
        if not due_date_exceeded:
            assignment['submit_xsrf_token'] = self.create_xsrf_token('submit')
            assignment['submit_action'] = self.get_action_url(
                    'submit', unit.unit_id)
            assignment['save_code_xsrf_token'] = self.create_xsrf_token(
                'save_code')

        response = self.parse_result(student, unit, tests)
        if response is not None:
            assignment['response'] = response

        if unit.html_check_answers:
            assignment['check_answers'] = 'True'

        if self.request.get('ierr'):
            assignment['ierr'] = self.request.get('answer')

        assignment['selected_lang'] = self.get_users_prog_lang_choice(
            saved_contents, submitted_contents)
        self.template_value['assignment'] = assignment
        self.template_value['navbar'] = {'course': True}
        self.template_value['unit'] = unit
        self.template_value['unit_id'] = unit.parent_unit
        self.template_value['pa_unit_id'] = unit.unit_id
        self.template_value['pa_name'] = self.assignment_name
        self.template_value['base'] = self.get_template('base_course.html')
        self.template_value['course_navbar'] = self.get_template('course_navbar.html')

        locale = self.app_context.get_environ()['course']['locale']
        template_file = 'read_view.html'
        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__) + '/templates'])
        self.render(template)

    def get_edit(self):
        url = self.canonicalize_url(
            '/dashboard?%s') % urllib.urlencode({
                'action': 'edit_prog_assignment',
                'key': self.request.get('name')})
        self.redirect(url)

    def return_error(self, reason):
        extra_args = dict()
        extra_args = {'answer': reason}
        lang = self.request.get('prog-lang')
        if lang:
            extra_args['lang'] = lang
        self.redirect(self.get_action_url(
            'list',
            self.request.get('name'),
            extra_args=extra_args))

    def return_backend_error(self):
        self.return_error('Could not compile at this time. Try Later.')

    def response_size_exceeded_error(self, extra_args=None):
        prog_result = 'Response Size Exceeded.'
        extra_args['answer'] = prog_result
        self.redirect(self.get_action_url(
            'list',
            self.request.get('name'),
            extra_args=extra_args))

    @classmethod
    def create_lang_dict(cls, filename, code):
        return {'filename': filename, 'code': code}

    def post_save_code(self):
        success, student, course, unit = self._validate_request(False)
        if not success:
            return
        if self.has_deadline_passed(unit):
            self.error(404)
            return

        lang = self.request.get('prog-lang')
        answer = self.request.get('prog-input')
        filename = self.request.get('filename')

        prog_models.SavedProgrammingCodeEntity.save_code(
            student, unit.unit_id, lang,
            self.create_lang_dict(filename, answer))
        course.get_progress_tracker().put_custom_unit_in_progress(
            student, unit.unit_id)
        transforms.send_json_response(self, 200, 'Saved.')

    def post_submit(self):
        success, student, course, unit = self._validate_request(False)
        if not success:
            return
        if self.has_deadline_passed(unit):
            self.redirect(self.get_action_url('list', unit.unit_id))
            return

        lang = self.request.get('prog-lang')
        if not lang:
            self.redirect(self.get_action_url('list', unit.unit_id))
            return

        filename = self.request.get('filename-' + lang)
        answer = self.request.get('prog-input-' + lang)
        if not filename or not answer:
            self.redirect(self.get_action_url('list', unit.unit_id))
            return

        btype = self.request.get('btype')

        content = self.get_content(course, unit)
        if len(content) == 0:
            self.return_backend_error()
            return

        # Determine if the submission is to test public test cases or private
        # test cases.
        is_public = (btype != 'submit')

        lang_dict = self.create_lang_dict(filename, answer)
        prog_models.SavedProgrammingCodeEntity.save_code(
            student, unit.unit_id, lang, lang_dict)
        if not is_public:
            self.submit_student_answer(unit, student, lang, lang_dict)

        evaluation_result = self.get_evaluation_result(
            course=course, unit=unit, content=content, student=student,
            is_public=is_public, lang=lang, filename=filename, answer=answer)

        if result.Status.BACKEND_ERROR == evaluation_result.status:
            self.return_backend_error()
            return
        if result.Status.OTHER == evaluation_result.status:
            self.return_error(evaluation_result.reason)
            return

        if is_public:
            course.get_progress_tracker().put_custom_unit_in_progress(
                student, unit.unit_id)
            self.redirect(self.get_action_url(
                'list', unit.unit_id,
                extra_args={'show_result': True, 'lang': lang}))
            return

        course.get_progress_tracker().put_custom_unit_completed(
            student, unit.unit_id)
        self.redirect(self.get_action_url(
            'list', unit.unit_id,
            extra_args={'post_submit': True, 'lang': lang}))
