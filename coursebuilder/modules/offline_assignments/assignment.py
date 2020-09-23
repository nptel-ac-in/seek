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

"""Classes and methods to serving offline assignment."""

__authors__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

import datetime
import csv
import StringIO
import os
import urllib

from common import jinja_utils
from controllers import sites
from controllers.utils import BaseHandler
from controllers.utils import HUMAN_READABLE_DATETIME_FORMAT
from controllers.utils import ReflectiveRequestHandler
from common.utils import Namespace
from models import roles
from models import entities
from models import models
from models import courses
from models import student_work
from models import transforms
from models import utils
from modules.nptel import timezones
from modules.offline_assignments import question


class OfflineAssignmentHandler(BaseHandler,
                            question.OfflineAssignmentBaseHandler,
                            ReflectiveRequestHandler):
    """Handler for prog assignment."""

    default_action = 'list'
    get_actions = [default_action, 'edit']
    # No post actions. Uploading of scores has to be done by the admin.

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
    def get_student_answer(cls, unit, student):
        if student.is_transient:
            return None
        submitted_contents = student_work.Submission.get_contents(
                unit.unit_id, student.get_key())
        return (transforms.loads(submitted_contents)
                if submitted_contents else None)

    @classmethod
    def has_deadline_passed(cls, unit):
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
        assignment = dict()

        if len(content) > 0:
            assignment['question'] = content['question']
        if roles.Roles.is_course_admin(self.app_context):
            assignment['edit_action'] = self.get_edit_url(self.assignment_name)

        template_file = 'templates/offline_assignment.html'

        self.template_value['assignment'] = assignment
        self.template_value['navbar'] = {'course': True}
        self.template_value['unit'] = unit
        self.template_value['pa_unit_id'] = unit.unit_id

        self.template_value['pa_name'] = self.assignment_name
        self.template_value['base'] = self.get_template('base_course.html')

        locale = self.app_context.get_environ()['course']['locale']


        template = jinja_utils.get_template(
            template_file, [os.path.dirname(__file__)])
        self.render(template)


    @classmethod
    def score(cls, student, course, assessment_id, score, errors):
        unit = course.find_unit_by_id(assessment_id)
        error_str = 'Student: %s, course: %s, assessment_id: %s, error: %s'

        if not unit:
            errors.append(error_str % (
                student.email, course, assessment_id, 'Unit not found'))
            return False

        if cls.has_deadline_passed(unit):
            errors.append(error_str % (
                student.email, course._namespace, assessment_id, 'Deadline Passed'))
            return False

        submit_only_once = unit.workflow.submit_only_once()
        already_submitted = False
        submitted_contents = cls.get_student_answer(unit, student)
        if submitted_contents and submitted_contents['submitted']:
            already_submitted = True
        if submit_only_once and already_submitted:
            errors.append(error_str % (
                student.email, course._namespace, assessment_id, 'Already submitted'))

        answer_dict = dict()
        answer_dict['details'] = (
            'Last submitted on %s' % datetime.datetime.now())
        answer_dict['submitted'] = True

        # TODO(rthakker) Do this write in bulk
        student_work.Submission.write(
                assessment_id, student.get_key(), transforms.dumps(answer_dict))
        utils.set_score(student, assessment_id, score)

        # TODO(rthakker) Do this write in bulk
        course.get_progress_tracker().put_custom_unit_completed(
            student, assessment_id)
        return True

    @classmethod
    def bulk_score_by_course(cls, course, csv_list, errors):
        """
        Bulk score assessments by email.

        csv list should be of the following format:
        [
            [email, assessment_id, score],
            .
            .
        ]
        """


        students = []

        student_ids = [entry[0].strip() for entry in csv_list]
        students = models.StudentProfileDAO.bulk_get_student_by_email(
            student_ids)
        modified_students = []

        for i, entry in enumerate(csv_list):

            if len(entry) != 3:
                if len(entry) >= 1:
                    errors.append('Invalid row %s' % ','.join(entry))
                    continue

            assessment_id = entry[1].strip()
            try:
                score = float(entry[2])
            except ValueError:
                errors.append('Invalid row %s' % ','.join(entry))
                continue
            student = students[i]
            if student:
                if not cls.score(student, course, assessment_id, score, errors):
                    errors.append(
                        'Failed to score: %s, %s, %s' %
                        (student.email, assessment_id, score))
                else:
                    modified_students.append(student)
            else:
                errors.append('Student not found %s' % student_ids[i])

        # Bulk save the students
        entities.put(modified_students)

    @classmethod
    def bulk_score_by_unit(cls, course, unit, csv_list, errors):
        """
        Bulk scores assessments for a specific unit in a course by email
        """

        for i, row in enumerate(csv_list):
            if len(row) != 2:
                # The error will be handled in bulk_score_by_course
                continue
            # Insert unit_id into the row
            csv_list[i] = [row[0], str(unit.unit_id), row[1]]

        # Call bulk_score_by_course now that we have the unit_id field
        cls.bulk_score_by_course(course, csv_list, errors)

    @classmethod
    def bulk_score(cls, csv_list, errors):
        """
        Bulk score assessments by email.

        csv_list should be a dict of the following format:
        [
            [namespace1, email, assessment_id, score],
            .
            .
        ]
        """
        # Split the list by namespace
        csv_dict = dict()
        for entry in csv_list:
            if len(entry) != 4:
                if len(entry) >= 1:
                    errors.append('Invalid row %s' % ','.join(entry))
                continue

            namespace = entry[0].strip()
            if not namespace:
                errors.append('Invalid row %s' % ','.join(entry))
                continue

            score_list = csv_dict.get(namespace, [])
            score_list.append(entry[1:])
            csv_dict[namespace] = score_list

        # Call bulk score by course
        for namespace, score_list in csv_dict.iteritems():
            course_errors = []
            app_context = sites.get_app_context_for_namespace(namespace)
            if not app_context:
                errors.append('Course not found %s ' % namespace)
                continue
            course = courses.Course.get(app_context)
            with Namespace(namespace):
                cls.bulk_score_by_course(course, score_list, course_errors)
                if course_errors:
                    errors.append('Errors for course %s: %s' %
                        (namespace, transforms.dumps(course_errors)))
