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

"""Contain classes to run deferred tasks."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import logging
from mapreduce import context

from google.appengine.api import namespace_manager
from google.appengine.ext import db

from controllers import sites
from controllers.utils import BaseHandler
from common.utils import Namespace
from models import entities
from modules.course_staff import course_staff
from models import utils
from models import student_work
from models import jobs
from models import models
from models import courses
from models import transforms
from modules.manual_review import staff
from modules.manual_review import manage
from modules.subjective_assignments import question


@db.transactional(xg=True)
def remove_step(step):
    """Function to remove a manual evaluation step and perform related tasks"""
    evaluator_key = db.Key.from_path(
        course_staff.CourseStaff.kind(), step.evaluator)
    evaluator, summary = entities.get(
        [evaluator_key, step.manual_evaluation_summary_key])
    if summary:
        summary.decrement_count(step.state)
    else:
        manage.COUNTER_DELETE_REVIEWER_SUMMARY_MISS.inc()
    step.removed = True
    if evaluator:
        evaluator.num_assigned -= 1
    entities.put([entity for entity in [step, summary, evaluator] if entity])

def assign_course_staff(entity):
    """
    Function to assign a submission to a course staff. The entity can be
    either of type ManualEvaluationSummary or of type ManualEvaluationStep
    since both of them have the fields required here.
    """
    unit_id = entity.unit_id
    submission_key = entity.submission_key
    students = entities.get([entity.reviewee_key])
    if not students:
        return False
    student = students[0]

    namespace = namespace_manager.get_namespace()
    if namespace:
        app_context = sites.get_app_context_for_namespace(namespace)
        if app_context:
            course = courses.Course.get(app_context)
            if course:
                unit = course.find_unit_by_id(unit_id)
                if unit and submission_key and student:
                    manage.Manager.find_and_add_evaluator(
                        course, unit, submission_key, student)
                    return True
    logging.error('Could not load unit for entity ' + entity.key().name())
    return False

def reshare_submission_with_evaluator(step):
    """Function to share the step's submission contents with the course staff"""

    unit_id = step.unit_id
    namespace = namespace_manager.get_namespace()
    if namespace:
        app_context = sites.get_app_context_for_namespace(namespace)
        if app_context:
            course = courses.Course.get(app_context)
            if course:
                unit = course.find_unit_by_id(unit_id)
                if unit:
                    content = (question.SubjectiveAssignmentBaseHandler.
                               get_content(course, unit))
                    if question.SubjectiveAssignmentBaseHandler.BLOB != (
                            content.get(
                                question.SubjectiveAssignmentBaseHandler.
                                OPT_QUESTION_TYPE)):
                        # Not a drive type submission, skip.
                        return

                    if transforms.loads(step.drive_permission_list):
                        # Permission list already present, skip.
                        return

                    evaluator = course_staff.CourseStaff.get_by_key_name(
                        step.evaluator)
                    submission_key = step.submission_key
                    submission_contents = (
                        manage.Manager.get_submission_contents_dict(
                            submission_key))

                    if submission_contents and evaluator:
                        drive_permission_list_dump = transforms.dumps(
                            manage.Manager.share_submission_with_evaluator(
                                submission_contents, evaluator.email))

                        step.drive_permission_list = drive_permission_list_dump
                        entities.put([step])
                        return
                    logging.error('Invalid evaluator or submission for step '
                                  + step.key().name())
                    return
    logging.error('Could not load unit for step ' + step.key())

class AssignSubmission(jobs.MapReduceJob):
    """A job that submits request for reevaluation."""

    def __init__(self, app_context):
        super(AssignSubmission, self).__init__(app_context)
        self._job_name = 'job-%s-%s' % (
            self.__class__.__name__, self._namespace)

    @staticmethod
    def get_description():
        return 'Assign for manual review'

    @staticmethod
    def entity_class():
        return staff.ManualEvaluationSummary

    @staticmethod
    def map(entity):
        if entity.assigned_count > 0:
            return
        assign_course_staff(entity)

    @staticmethod
    def reduce(key, data_list):
        pass

# TODO(rthakker) While re-assigning reviews to course staff, check whether
# we should assign even the COMPLETED reviews. Currently not doing that.


class ReassignSubmissionByCourseStaff(jobs.MapReduceJob):
    """A Job that reassigns submissions for particular course staff"""

    def __init__(self, app_context, course_staff_user_ids):
        super(ReassignSubmissionByCourseStaff, self).__init__(app_context)
        self._course_staff_user_ids = course_staff_user_ids
        self._job_name = 'job-%s-%s-%s' % (
            self.__class__.__name__, self._namespace,
            str(self._course_staff_user_ids))

    @staticmethod
    def get_description():
        return 'Reassign manual review by course staff'

    @staticmethod
    def entity_class():
        return staff.ManualEvaluationStep

    def build_additional_mapper_params(self, app_context):
        return {
            'course_staff_user_ids': self._course_staff_user_ids
        }

    @staticmethod
    def map(entity):
        mapper_params = context.get().mapreduce_spec.mapper.params
        if entity.removed or entity.state == staff.REVIEW_STATE_COMPLETED:
            return

        course_staff_user_ids = mapper_params['course_staff_user_ids']
        if entity.evaluator not in course_staff_user_ids:
            return
        remove_step(entity)
        assign_course_staff(entity)

    @staticmethod
    def reduce(key, data_list):
        pass


class ReassignSubmissionByExcludingCourseStaff(jobs.MapReduceJob):
    """A job that reassigns submissions for all but specified course staff"""

    def __init__(self, app_context, exclude_course_staff_user_ids=None):
        super(ReassignSubmissionByExcludingCourseStaff, self).__init__(
            app_context)
        self._exclude_course_staff_user_ids = exclude_course_staff_user_ids
        self._job_name = 'job-%s-%s-%s' % (
            self.__class__.__name__, self._namespace,
            str(self._exclude_course_staff_user_ids))

    @staticmethod
    def get_description():
        return 'Reassign manual review for course staff'

    @staticmethod
    def entity_class():
        return staff.ManualEvaluationStep

    def build_additional_mapper_params(self, app_context):
        return {
            'exclude_course_staff_user_ids': self._exclude_course_staff_user_ids
        }

    @staticmethod
    def map(entity):
        mapper_params = context.get().mapreduce_spec.mapper.params
        if entity.removed or entity.state == staff.REVIEW_STATE_COMPLETED:
            return

        exclude_course_staff_user_ids = mapper_params[
            'exclude_course_staff_user_ids']
        if entity.evaluator in exclude_course_staff_user_ids:
            return
        remove_step(entity)
        assign_course_staff(entity)

    @staticmethod
    def reduce(key, data_list):
        pass


class FixDrivePermissions(jobs.MapReduceJob):
    """
    A job that re-shares the submission files with the course staff if required.

    Required for the manual review step objects created before the automatic
    sharing was implemented.
    """

    def __init__(self, app_context):
        super(FixDrivePermissions, self).__init__(app_context)
        self._job_name = 'job-%s-%s' % (
            self.__class__.__name__, self._namespace)

    @staticmethod
    def get_description():
        return 'Fix drive permissions for course staff'

    @staticmethod
    def entity_class():
        return staff.ManualEvaluationStep

    @staticmethod
    def map(entity):
        if entity.removed or entity.state == staff.REVIEW_STATE_COMPLETED:
            return
        reshare_submission_with_evaluator(entity)

    @staticmethod
    def reduce(key, data_list):
        pass


class CalculateFinalScore(jobs.MapReduceJob):
    """
    A Job that calculates the final score of a submission based on its
    ManualEvaluationStep objects
    """

    def __init__(self, app_context):
        super(CalculateFinalScore, self).__init__(app_context)
        self._job_name = 'job-%s-%s' % (
            self.__class__.__name__, self._namespace)

    @staticmethod
    def get_description():
        return 'Calculate final score for submissions'

    @staticmethod
    def entity_class():
        return staff.ManualEvaluationSummary

    @staticmethod
    def map(entity):
        if entity.completed_count == 0:
            return

        # Get the scoring method
        namespace = namespace_manager.get_namespace()
        app_context = sites.get_app_context_for_namespace(namespace)
        course = courses.Course.get(app_context)
        unit = course.find_unit_by_id(entity.unit_id)
        content = question.SubjectiveAssignmentRESTHandler.get_content(
            course, unit)
        method = content.get('scoring_method')

        # Get the manual evaluation steps
        steps = staff.ManualEvaluationStep.all().filter(
            'manual_evaluation_summary_key =', entity.key()
        ).filter('state =', staff.REVIEW_STATE_COMPLETED
        ).filter('removed =', False)

        # Calculate final score
        final_score = manage.Manager.calculate_final_score(steps, method)
        if final_score is None:
            return
        student = models.Student.get(entity.reviewee_key)
        utils.set_score(student, str(entity.unit_id), final_score)
        student.put()

    @staticmethod
    def reduce(key, data_list):
        pass

class FixMissingManualEvaluationSummary(jobs.MapReduceJob):
    """
    Job to perform a fix in the situation when the submission is present
    but the manual evaluation submmary object is not present.
    """

    def __init__(self, app_context):
        super(FixMissingManualEvaluationSummary, self).__init__(app_context)
        self._job_name = 'job-%s-%s' % (
            self.__class__.__name__, self._namespace)

    @staticmethod
    def get_description():
        return 'Fix missing manual evaluation summary'

    @staticmethod
    def entity_class():
        return student_work.Submission

    @staticmethod
    def map(entity):

        namespace = namespace_manager.get_namespace()
        app_context = sites.get_app_context_for_namespace(namespace)
        course = courses.Course.get(app_context)
        unit = course.find_unit_by_id(entity.unit_id)
        if not unit:
            logging.error("Did not find unit for " + entity.key().name())
            return

        if unit.custom_unit_type != (
                question.SubjectiveAssignmentBaseHandler.UNIT_TYPE_ID):
            return

        # Try getting Manual evaluation summary for this
        submission_key = entity.key()
        summary_key_name = staff.ManualEvaluationSummary.key_name(
            submission_key)
        summary = staff.ManualEvaluationSummary.get_by_key_name(
            summary_key_name)
        if not summary:
            # Create the ManualEvaluationSummary object
            student = models.Student.get_student_by_user_id(
                entity.reviewee_key.name())
            manage.Manager.submit_for_evaluation(course, unit, student)

    @staticmethod
    def reduce(key, data_list):
        pass


class FixNumAssigned(jobs.MapReduceJob):
    """
    A Job that fixes the num_assigned count for course staff.
    """

    def __init__(self, app_context):
        super(FixNumAssigned, self).__init__(app_context)
        self._job_name = 'job-%s-%s' % (
            self.__class__.__name__, self._namespace)

    @staticmethod
    def get_description():
        return 'Fix num_assigned for Course Staff'

    @staticmethod
    def entity_class():
        return course_staff.CourseStaff

    @staticmethod
    def map(entity):
        # Get the steps
        steps = staff.ManualEvaluationStep.all().filter(
            'evaluator =', entity.key().name()
        ).fetch(None)

        # Calculate the count
        assigned_steps = [s for s in steps if not s.removed]
        num_assigned = len(assigned_steps)
        logging.debug('num_assigned for %s: %s', entity.email, num_assigned)
        entity.num_assigned = num_assigned
        entity.put()

    @staticmethod
    def reduce(key, data_list):
        pass


class AssignSubmissionHandler(BaseHandler):
    """Runs job for assigning submissions to course staff."""

    def get(self):
        namespace = self.request.get('namespace')
        if namespace:
            app_context = sites.get_app_context_for_namespace(namespace)
            if app_context:
                job = AssignSubmission(app_context)
                job.submit()
                self.response.write('OK\n')
                return
        self.response.write('Failed\n')


class ReassignSubmissionHandler(BaseHandler):
    """Runs job to reassign submissions from a course staff"""

    def get(self):
        """Endpoint to reassign all submissions assigned to ex-course staff"""
        namespace = self.request.get('namespace')
        if namespace:
            app_context = sites.get_app_context_for_namespace(namespace)
            if app_context:
                course_staff_ids = None
                with Namespace(namespace):
                    staff_list = course_staff.CourseStaff.all().fetch(None)
                    course_staff_ids = [s.user_id for s in staff_list]
                job = ReassignSubmissionByExcludingCourseStaff(
                    app_context,
                    exclude_course_staff_user_ids=course_staff_ids)
                job.submit()
                self.response.write('OK\n')
                return
        self.response.write('Failed\n')


class FixDrivePermissionsHandler(BaseHandler):
    """Runs job for fixing submission file permissions for course staff."""

    def get(self):
        namespace = self.request.get('namespace')
        if namespace:
            app_context = sites.get_app_context_for_namespace(namespace)
            if app_context:
                job = FixDrivePermissions(app_context)
                job.submit()
                self.response.write('OK\n')
                return
        self.response.write('Failed\n')


class CalculateFinalScoreHandler(BaseHandler):
    """Runs job for calculating the final score of submissions."""

    def get(self):
        namespace = self.request.get('namespace')
        if namespace:
            app_context = sites.get_app_context_for_namespace(namespace)
            if app_context:
                job = CalculateFinalScore(app_context)
                job.submit()
                self.response.write('OK\n')
                return
        self.response.write('Failed\n')

class FixMissingManualEvaluationSummaryHandler(BaseHandler):
    """Runs job for fixing missing manual evaluation summary."""

    def get(self):
        namespace = self.request.get('namespace')
        if namespace:
            app_context = sites.get_app_context_for_namespace(namespace)
            if app_context:
                job = FixMissingManualEvaluationSummary(app_context)
                job.submit()
                self.response.write('OK\n')
                return
        self.response.write('Failed\n')


class FixNumAssignedHandler(BaseHandler):
    """Runs FixNumAssigned job"""

    def get(self):
        namespace = self.request.get('namespace')
        if namespace:
            app_context = sites.get_app_context_for_namespace(namespace)
            if app_context:
                job = FixNumAssigned(app_context)
                job.submit()
                self.response.write('OK\n')
                return
        self.response.write('Failed\n')
