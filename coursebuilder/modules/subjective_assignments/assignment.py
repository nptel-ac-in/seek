# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Classes and methods to serving subjective assignment."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import datetime
import os
import json
import urllib
import appengine_config

from google.appengine.api import urlfetch_errors
from apiclient import errors as http_errors
from common import jinja_utils
from controllers import sites
from controllers.utils import BaseHandler
from controllers.utils import HUMAN_READABLE_DATETIME_FORMAT
from controllers.utils import ReflectiveRequestHandler
from models import custom_modules
from models import custom_units
from models import roles
from models import student_work
from models import transforms
from modules.manual_review import manage
from modules.subjective_assignments import drive_service
from modules.subjective_assignments import (
    course_staff as subjective_course_staff)
from modules.google_service_account import service_account_models
from modules.google_service_account import google_service_account
from modules.nptel import timezones
from modules.course_staff import course_staff
from modules.course_staff import evaluate
import question


class SubjectiveAssignmentHandler(BaseHandler,
                            question.SubjectiveAssignmentBaseHandler,
                            ReflectiveRequestHandler):
    """Handler for prog assignment."""

    default_action = 'list'
    get_actions = [default_action, 'edit']
    post_actions = ['submit', 'save_draft']

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
    def submit_essay_answer(
        cls, unit, student, submitted, answer):
        answer_dict = dict()
        answer_dict['essay'] = answer
        answer_dict['submitted'] = submitted
        student_work.Submission.write(
            unit.unit_id, student.get_key(), transforms.dumps(answer_dict))

    @classmethod
    def submit_dir_answer(
        cls, unit, student, submitted, orig_file_list, copied_file):
        answer_dict = dict()
        answer_dict['student_file_list'] = orig_file_list
        answer_dict['submitted'] = submitted
        answer_dict['copied_file'] = copied_file
        student_work.Submission.write(
            unit.unit_id, student.get_key(), transforms.dumps(answer_dict))

    @classmethod
    def get_student_answer(cls, unit, student):
        if student.is_transient:
            return None
        submitted_contents = student_work.Submission.get_contents(
                unit.unit_id, student.get_key())
        return (transforms.loads(submitted_contents)
                if submitted_contents else None)

    @classmethod
    def get_submission(cls, unit, student):
        if student.is_transient:
            return None
        return student_work.Submission.get(unit.unit_id, student.get_key())

    @classmethod
    def get_contents_from_submission(cls, submission):
        if submission and submission.contents:
            raw = transforms.loads(submission.contents)
            if raw:
                return transforms.loads(raw)


    def has_deadline_passed(self, unit):
        submission_due_date = unit.workflow.get_submission_due_date()
        if submission_due_date:
            time_now = datetime.datetime.now()
            if time_now > submission_due_date:
                return True
        return False

    def get_list(self):
        student = self.personalize_page_and_get_enrolled()
        if not student:
            self.redirect('/preview')
            return

        self.assignment_name = self.request.get('name')
        course = self.get_course()
        unit = course.find_unit_by_id(self.assignment_name)
        if not unit:
            self.error(404)
            self.redirect('/course')
            return

        content = self.get_content(course, unit)
        blob_dict = content.get(self.BLOB, {})
        max_file_limit = blob_dict.get(self.OPT_MAX_FILE_LIMIT)
        if not max_file_limit:
            max_file_limit = 1
        readonly_view = False
        due_date_exceeded = False
        assignment = {
            'success': None
        }

        submission_due_date = unit.workflow.get_submission_due_date()
        if submission_due_date:
            assignment['submission_due_date'] = (
                submission_due_date.replace(
                    tzinfo=timezones.UTC).astimezone(timezones.IST).strftime(
                        HUMAN_READABLE_DATETIME_FORMAT.replace('UTC', 'IST')))

            if self.has_deadline_passed(unit):
                readonly_view = True
                due_date_exceeded = True

        assignment['due_date_exceeded'] = due_date_exceeded
        submit_only_once = unit.workflow.submit_only_once()
        self.template_value['submit_only_once'] = submit_only_once
        submission = self.get_submission(unit, student)
        submitted_contents = self.get_contents_from_submission(submission)
        if submission:
            assignment['updated_on'] = submission.updated_on.replace(
                tzinfo=timezones.UTC).astimezone(timezones.IST).strftime(
                HUMAN_READABLE_DATETIME_FORMAT)
        else:
            assignment['updated_on'] = None

        already_submitted = False
        if submitted_contents and submitted_contents['submitted']:
            already_submitted = True
        if submit_only_once and already_submitted:
            readonly_view = True
        assignment['already_submitted'] = already_submitted
        self.template_value['readonly'] = readonly_view


        if readonly_view:
            score = course.get_score(student, unit.unit_id)
            if score is not None:
                assignment['score'] = '%s' % (float(score))
        if len(content) > 0:
            assignment['question'] = content.get('question')
        if roles.Roles.is_course_admin(self.app_context):
            assignment['edit_action'] = self.get_edit_url(self.assignment_name)
        if not due_date_exceeded:
            assignment['submit_xsrf_token'] = self.create_xsrf_token('submit')
            assignment['submit_action'] = self.get_action_url(
                    'submit', self.assignment_name)
            assignment['save_draft_xsrf_token'] = self.create_xsrf_token(
                'save_draft')

        if self.ESSAY == content.get(self.OPT_QUESTION_TYPE):
            template_file = 'essay.html'
            if submitted_contents and 'essay' in submitted_contents.keys():
                assignment['success'] = self.request.get('success')
                assignment['previous_submission'] = submitted_contents['essay']
        else:
            template_file = 'snapshot.html'
            assignment['failed'] = self.request.get('failed')
            if not assignment['failed'] and submitted_contents:
                assignment['success'] = self.request.get('success')
                orig_file_list = None
                if 'student_file_list' in submitted_contents.keys():
                    orig_file_list = submitted_contents['student_file_list']
                elif 'student_file' in submitted_contents.keys():
                    # for backword compatibility
                    orig_file_list = [submitted_contents['student_file']]

                if orig_file_list:
                    assignment['orig_file_list'] = orig_file_list
                    assignment['orig_file_list_str'] = json.dumps(orig_file_list)

                if 'copied_file' in submitted_contents.keys():
                    copied_file = submitted_contents['copied_file']
                    if isinstance(copied_file, dict):
                        assignment['copied_file'] = [copied_file]
                    else:
                        assignment['copied_file'] = copied_file

        self.template_value['assignment'] = assignment
        self.template_value['navbar'] = {'course': True}
        self.template_value['unit'] = unit
        self.template_value['pa_unit_id'] = unit.unit_id

        self.template_value['pa_name'] = self.assignment_name
        self.template_value['base'] = self.get_template('base_course.html')

        self.template_value['max_file_limit'] = str(max_file_limit)

        # Drive Credentials
        oauth2_client_id = (
            google_service_account.GoogleServiceManager.
            get_or_create_default_settings_by_type(
                service_account_models.GoogleServiceAccountTypes.
                OAUTH2_CLIENT_ID))
        self.template_value['google_oauth2_client_id'] = oauth2_client_id
        locale = self.app_context.get_environ()['course']['locale']


        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__)])
        self.render(template)

    def post_save_draft(self):
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return
        if not student.user_id:
            student.user_id = self.get_user().user_id()

        essay = self.request.get('essay')
        self.assignment_name = self.request.get('id')

        course = self.get_course()
        unit = course.find_unit_by_id(self.assignment_name)

        if self.has_deadline_passed(unit):
            self.error(404)
            return

        if not unit:
            self.error(404)
            return
        submitted_contents = self.get_student_answer(unit, student)
        submitted = submitted_contents and submitted_contents['submitted']

        submit_only_once = unit.workflow.submit_only_once()
        if submit_only_once and submitted:
            return
        self.submit_essay_answer(unit, student, submitted, essay)
        course.get_progress_tracker().put_custom_unit_in_progress(
            student, unit.unit_id)
        transforms.send_json_response(self, 200, 'Saved.')

    @classmethod
    def create_student_submission_folder(cls, student, dir_id, errors):
        """Creates a folder with student id inside the specified folder"""
        return (
            drive_service.DriveManager.get_or_create_drive_folder_with_parent(
                parent_folder_id=dir_id, folder_name=str(student.user_id),
                errors=errors))

    @classmethod
    def copy_file(cls, assignment, dir_id, student, file_list, errors):
        student_folder = cls.create_student_submission_folder(
            student, dir_id, errors)
        if not student_folder:
            errors.append('Could not create student folder. Aborting.')
            return

        copied_file_list = []
        timestamp = str(datetime.datetime.now())
        for idx, file_dict in enumerate(file_list):
            file_id = file_dict['fileId']
            filename = file_dict['fileName']
            try:
                copied_file_list.append(
                    drive_service.DriveManager.copy_file(
                        fileId=file_id, convert=False, ocr=False,
                        visibility="PRIVATE",
                        body={
                            'parents' : [{'id': student_folder['id']}],
                            'title': filename
                        }).execute())
            except http_errors.HttpError, error:
                errors.append(str(error))
                return None
            except urlfetch_errors.DeadlineExceededError, error:
                errors.append(str(error))
                return None
        return copied_file_list

    def post_submit(self):
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return
        if not student.user_id:
            student.user_id = self.get_user().user_id()
        assignment_name = self.request.get('name')

        course = self.get_course()
        unit = course.find_unit_by_id(assignment_name)

        if self.has_deadline_passed(unit):
            self.error(404)
            return

        if not unit:
            self.error(404)
            return
        content = self.get_content(course, unit)
        if self.ESSAY == content.get(self.OPT_QUESTION_TYPE):
            essay = self.request.get('essay')
            self.submit_essay_answer(unit, student, True, essay)
        else:
            file_list = self.request.get('file_list')
            if not file_list:
                self.redirect(self.get_action_url('list', assignment_name))
                return

            file_list = json.loads(file_list)

            if not isinstance(file_list, list):
                self.redirect(self.get_action_url('list', assignment_name))
                return

            errors = []
            blob_dict = content.get(self.BLOB, {})
            drive_folder_id = blob_dict[self.OPT_DRIVE_DIR_ID]
            max_file_limit = blob_dict.get(self.OPT_MAX_FILE_LIMIT)
            if not max_file_limit:
                max_file_limit = 1
            if len(file_list) > max_file_limit:
                self.redirect(self.get_action_url('list', assignment_name))
                return
            copied_file = self.copy_file(
                assignment_name, drive_folder_id, student, file_list, errors)
            if copied_file:
                self.submit_dir_answer(unit, student, True, file_list,
                                       copied_file)
            else:
                self.redirect(self.get_action_url(
                    'list', assignment_name, extra_args={'failed': True}))
                return
        manage.Manager.submit_for_evaluation(course, unit, student)

        course.get_progress_tracker().put_custom_unit_completed(
            student, unit.unit_id)
        self.redirect(self.get_action_url(
            'list', assignment_name, extra_args={'success': True}))


custom_unit = None
custom_module = None


def delete_assignement(course, unit):
    return question.SubjectiveAssignmentBaseHandler.delete_file(course, unit)


def import_assignment(src_course, src_unit, dst_course, dst_unit):
    content = question.SubjectiveAssignmentBaseHandler.get_content(
        src_course, src_unit)
    question.SubjectiveAssignmentBaseHandler.set_content(
        dst_course, dst_unit, content)


def visible_url(unit):
    return question.SubjectiveAssignmentBaseHandler.get_public_url(unit)


def register_module():
    """Registers this module in the registry."""
    associated_js_files_handlers = [
        ('/modules/subjective/editor/(.*)', sites.make_zip_handler(
            os.path.join(
                appengine_config.BUNDLE_ROOT,
                'modules/subjective_assignments/lib/ckeditor.zip'))),
        ]


    question_handlers = [
        (question.SubjectiveAssignmentBaseHandler.UNIT_URL,
         SubjectiveAssignmentHandler),
        (question.SubjectiveAssignmentRESTHandler.URI,
         question.SubjectiveAssignmentRESTHandler)]

    # Course Staff Custom Handlers
    evaluate.EvaluationHandler.add_custom_get_action(
        (subjective_course_staff.
         SubjectiveAssignmentCourseStaffBase.LIST_ACTION),
        (subjective_course_staff.
         SubjectiveAssignmentCourseStaffHandler.get_list_subjective)
    )

    evaluate.EvaluationHandler.add_custom_get_action(
        (subjective_course_staff.
         SubjectiveAssignmentCourseStaffBase.
         EVALUATE_ACTION),
        (subjective_course_staff.
         SubjectiveAssignmentCourseStaffHandler.
         get_evaluate_subjective)
    )

    evaluate.EvaluationHandler.add_custom_post_action(
        (subjective_course_staff.
         SubjectiveAssignmentCourseStaffBase.
         POST_SCORE_ACTION),
        (subjective_course_staff.
         SubjectiveAssignmentCourseStaffHandler.
         post_submit_score)
    )

    evaluate.EvaluationHandler.add_custom_post_action(
        (subjective_course_staff.
         SubjectiveAssignmentCourseStaffBase.
         POST_SAVE_ACTION),
        (subjective_course_staff.
         SubjectiveAssignmentCourseStaffHandler.
         post_save_comments)
    )

    global custom_module
    custom_module = custom_modules.Module(
        question.SubjectiveAssignmentBaseHandler.NAME,
        question.SubjectiveAssignmentBaseHandler.DESCRIPTION,
        associated_js_files_handlers, question_handlers)

    custom_unit = custom_units.CustomUnit(
        question.SubjectiveAssignmentBaseHandler.UNIT_TYPE_ID,
        question.SubjectiveAssignmentBaseHandler.NAME,
        question.SubjectiveAssignmentRESTHandler,
        visible_url,
        cleanup_helper=delete_assignement,
        import_helper=import_assignment,
        is_graded=True)

    # Add custom unit details to course staff
    course_staff.CourseStaff.add_custom_unit(
        question.SubjectiveAssignmentBaseHandler.UNIT_TYPE_ID,
        'list')

    return custom_module
