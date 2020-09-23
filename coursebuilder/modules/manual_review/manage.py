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

"""Implementation of the review subsystem."""

__author__ = [
    'johncox@google.com (John Cox)',
]

import datetime
import random
import logging

from models import counters
from models import custom_modules
from models import entities
from models import student_work
from models import utils
from models import transforms
import models.review
from modules.course_staff import course_staff
from modules.manual_review import staff
from modules.review import domain
from modules.review import peer
from google.appengine.ext import db
from modules.subjective_assignments import question
from modules.subjective_assignments import drive_service
from modules.nptel import utils

import staff


# In-process increment-only performance counters.
COUNTER_ADD_REVIEWER_BAD_SUMMARY_KEY = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-bad-summary-key',
    'number of times add_manual-evaluator() failed due to a bad manual-review summary key')
COUNTER_ADD_REVIEWER_SET_ASSIGNER_KIND_HUMAN = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-set-assigner-kind-human',
    ("number of times add_manual-evaluator() changed an existing step's assigner_kind "
     'to ASSIGNER_KIND_HUMAN'))
COUNTER_ADD_REVIEWER_CREATE_REVIEW_STEP = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-create-manual-review-step',
    'number of times add_manual-evaluator() created a new manual-review step')
COUNTER_ADD_REVIEWER_EXPIRED_STEP_REASSIGNED = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-expired-step-reassigned',
    'number of times add_manual-evaluator() reassigned an expired step')
COUNTER_ADD_REVIEWER_FAILED = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-failed',
    'number of times add_manual-evaluator() had a fatal error')
COUNTER_ADD_REVIEWER_REMOVED_STEP_UNREMOVED = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-removed-step-unremoved',
    'number of times add_manual-evaluator() unremoved a removed manual-review step')
COUNTER_ADD_REVIEWER_START = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-start',
    'number of times add_manual-evaluator() has started processing')
COUNTER_ADD_REVIEWER_SUCCESS = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-success',
    'number of times add_manual-evaluator() completed successfully')
COUNTER_ADD_REVIEWER_UNREMOVED_STEP_FAILED = counters.PerfCounter(
    'gcb-pr-add-manual-evaluator-unremoved-step-failed',
    ('number of times add_manual-evaluator() failed on an unremoved step with a fatal '
     'error'))

COUNTER_ASSIGNMENT_CANDIDATES_QUERY_RESULTS_RETURNED = counters.PerfCounter(
    'gcb-pr-assignment-candidates-query-results-returned',
    ('number of results returned by the query returned by '
     'get_assignment_candidates_query()'))

COUNTER_DELETE_REVIEWER_ALREADY_REMOVED = counters.PerfCounter(
    'gcb-pr-manual-review-delete-manual-evaluator-already-removed',
    ('number of times delete_manual-evaluator() called on manual-review step with removed '
     'already True'))
COUNTER_DELETE_REVIEWER_FAILED = counters.PerfCounter(
    'gcb-pr-manual-review-delete-manual-evaluator-failed',
    'number of times delete_manual-evaluator() had a fatal error')
COUNTER_DELETE_REVIEWER_START = counters.PerfCounter(
    'gcb-pr-manual-review-delete-manual-evaluator-start',
    'number of times delete_manual-evaluator() has started processing')
COUNTER_DELETE_REVIEWER_STEP_MISS = counters.PerfCounter(
    'gcb-pr-manual-review-delete-manual-evaluator-step-miss',
    'number of times delete_manual-evaluator() found a missing manual-review step')
COUNTER_DELETE_REVIEWER_SUCCESS = counters.PerfCounter(
    'gcb-pr-manual-review-delete-manual-evaluator-success',
    'number of times delete_manual-evaluator() completed successfully')
COUNTER_DELETE_REVIEWER_SUMMARY_MISS = counters.PerfCounter(
    'gcb-pr-manual-review-delete-manual-evaluator-summary-miss',
    'number of times delete_manual-evaluator() found a missing manual-review summary')

COUNTER_EXPIRE_REVIEW_CANNOT_TRANSITION = counters.PerfCounter(
    'gcb-pr-expire-manual-review-cannot-transition',
    ('number of times expire_manual-review() was called on a manual-review step that could '
     'not be transitioned to REVIEW_STATE_EXPIRED'))
COUNTER_EXPIRE_REVIEW_FAILED = counters.PerfCounter(
    'gcb-pr-expire-manual-review-failed',
    'number of times expire_manual-review() had a fatal error')
COUNTER_EXPIRE_REVIEW_START = counters.PerfCounter(
    'gcb-pr-expire-manual-review-start',
    'number of times expire_manual-review() has started processing')
COUNTER_EXPIRE_REVIEW_STEP_MISS = counters.PerfCounter(
    'gcb-pr-expire-manual-review-step-miss',
    'number of times expire_manual-review() found a missing manual-review step')
COUNTER_EXPIRE_REVIEW_SUCCESS = counters.PerfCounter(
    'gcb-pr-expire-manual-review-success',
    'number of times expire_manual-review() completed successfully')
COUNTER_EXPIRE_REVIEW_SUMMARY_MISS = counters.PerfCounter(
    'gcb-pr-expire-manual-review-summary-miss',
    'number of times expire_manual-review() found a missing manual-review summary')

COUNTER_EXPIRE_OLD_REVIEWS_FOR_UNIT_EXPIRE = counters.PerfCounter(
    'gcb-pr-expire-old-manual-reviews-for-unit-expire',
    'number of records expire_old_manual-reviews_for_unit() has expired')
COUNTER_EXPIRE_OLD_REVIEWS_FOR_UNIT_SKIP = counters.PerfCounter(
    'gcb-pr-expire-old-manual-reviews-for-unit-skip',
    ('number of times expire_old_manual-reviews_for_unit() skipped a record due to an '
     'error'))
COUNTER_EXPIRE_OLD_REVIEWS_FOR_UNIT_START = counters.PerfCounter(
    'gcb-pr-expire-old-manual-reviews-for-unit-start',
    'number of times expire_old_manual-reviews_for_unit() has started processing')
COUNTER_EXPIRE_OLD_REVIEWS_FOR_UNIT_SUCCESS = counters.PerfCounter(
    'gcb-pr-expire-old-manual-reviews-for-unit-success',
    'number of times expire_old_manual-reviews_for_unit() completed successfully')

COUNTER_EXPIRY_QUERY_KEYS_RETURNED = counters.PerfCounter(
    'gcb-pr-expiry-query-keys-returned',
    'number of keys returned by the query returned by get_expiry_query()')

COUNTER_GET_NEW_REVIEW_ALREADY_ASSIGNED = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-already-assigned',
    ('number of times get_new_manual-review() rejected a candidate because the '
     'manual-evaluator is already assigned to or has already completed it'))
COUNTER_GET_NEW_REVIEW_ASSIGNMENT_ATTEMPTED = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-assignment-attempted',
    'number of times get_new_manual-review() attempted to assign a candidate')
COUNTER_GET_NEW_REVIEW_CANNOT_UNREMOVE_COMPLETED = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-cannot-unremove-completed',
    ('number of times get_new_manual-review() failed because the manual-evaluator already had '
     'a completed, removed manual-review step'))
COUNTER_GET_NEW_REVIEW_FAILED = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-failed',
    'number of times get_new_manual-review() had a fatal error')
COUNTER_GET_NEW_REVIEW_NOT_ASSIGNABLE = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-none-assignable',
    'number of times get_new_manual-review() failed to find an assignable manual-review')
COUNTER_GET_NEW_REVIEW_REASSIGN_EXISTING = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-reassign-existing',
    ('number of times get_new_manual-review() unremoved and reassigned an existing '
     'manual-review step'))
COUNTER_GET_NEW_REVIEW_START = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-start',
    'number of times get_new_manual-review() has started processing')
COUNTER_GET_NEW_REVIEW_SUCCESS = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-success',
    'number of times get_new_manual-review() found and assigned a new manual-review')
COUNTER_GET_NEW_REVIEW_SUMMARY_CHANGED = counters.PerfCounter(
    'gcb-pr-get-new-manual-review-summary-changed',
    ('number of times get_new_manual-review() rejected a candidate because the manual-review '
     'summary changed during processing'))

COUNTER_GET_REVIEW_STEP_KEYS_BY_KEYS_RETURNED = counters.PerfCounter(
    'gcb-pr-get-manual-review-step-keys-by-keys-returned',
    'number of keys get_manual-review_step_keys_by() returned')
COUNTER_GET_REVIEW_STEP_KEYS_BY_FAILED = counters.PerfCounter(
    'gcb-pr-get-manual-review-step-keys-by-failed',
    'number of times get_manual-review_step_keys_by() had a fatal error')
COUNTER_GET_REVIEW_STEP_KEYS_BY_START = counters.PerfCounter(
    'gcb-pr-get-manual-review-step-keys-by-start',
    'number of times get_manual-review_step_keys_by() started processing')
COUNTER_GET_REVIEW_STEP_KEYS_BY_SUCCESS = counters.PerfCounter(
    'gcb-pr-get-manual-review-step-keys-by-success',
    'number of times get_manual-review_step_keys_by() completed successfully')

COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_FAILED = counters.PerfCounter(
    'gcb-pr-get-submission-and-manual-review-step-keys-failed',
    'number of times get_submission_and_manual-review_step_keys() had a fatal error')
COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_RETURNED = counters.PerfCounter(
    'gcb-pr-get-submission-and-manual-review-step-keys-keys-returned',
    'number of keys get_submission_and_manual-review_step_keys() returned')
COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_START = counters.PerfCounter(
    'gcb-pr-get-submission-and-manual-review-step-keys-start',
    ('number of times get_submission_and_manual-review_step_keys() has begun '
     'processing'))
COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_SUBMISSION_MISS = (
    counters.PerfCounter(
        'gcb-pr-get-submission-and-manual-review-step-keys-submission-miss',
        ('number of times get_submission_and_manual-review_step_keys() failed to find '
         'a submission_key')))
COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_SUCCESS = counters.PerfCounter(
    'gcb-pr-get-submission-and-manual-review-step_keys-success',
    ('number of times get_submission-and-manual-review-step-keys() completed '
     'successfully'))

COUNTER_START_REVIEW_PROCESS_FOR_ALREADY_STARTED = counters.PerfCounter(
    'gcb-pr-start-manual-review-process-for-already-started',
    ('number of times start_manual-review_process_for() called when manual-review already '
     'started'))
COUNTER_START_REVIEW_PROCESS_FOR_FAILED = counters.PerfCounter(
    'gcb-pr-start-manual-review-process-for-failed',
    'number of times start_manual-review_process_for() had a fatal error')
COUNTER_START_REVIEW_PROCESS_FOR_START = counters.PerfCounter(
    'gcb-pr-start-manual-review-process-for-start',
    'number of times start_manual-review_process_for() has started processing')
COUNTER_START_REVIEW_PROCESS_FOR_SUCCESS = counters.PerfCounter(
    'gcb-pr-start-manual-review-process-for-success',
    'number of times start_manual-review_process_for() completed successfully')

COUNTER_WRITE_REVIEW_COMPLETED_ASSIGNED_STEP = counters.PerfCounter(
    'gcb-pr-write-manual-review-completed-assigned-step',
    'number of times write_manual-review() transitioned an assigned step to completed')
COUNTER_WRITE_REVIEW_COMPLETED_EXPIRED_STEP = counters.PerfCounter(
    'gcb-pr-write-manual-review-completed-expired-step',
    'number of times write_manual-review() transitioned an expired step to completed')
COUNTER_WRITE_REVIEW_CREATED_NEW_REVIEW = counters.PerfCounter(
    'gcb-pr-write-manual-review-created-new-manual-review',
    'number of times write_manual-review() created a new manual-review')
COUNTER_WRITE_REVIEW_FAILED = counters.PerfCounter(
    'gcb-pr-write-manual-review-failed',
    'number of times write_manual-review() had a fatal error')
COUNTER_WRITE_REVIEW_REVIEW_MISS = counters.PerfCounter(
    'gcb-pr-write-manual-review-manual-review-miss',
    'number of times write_manual-review() found a missing manual-review')
COUNTER_WRITE_REVIEW_START = counters.PerfCounter(
    'gcb-pr-write-manual-review-start',
    'number of times write_manual-review() started processing')
COUNTER_WRITE_REVIEW_STEP_MISS = counters.PerfCounter(
    'gcb-pr-write-manual-review-step-miss',
    'number of times write_manual-review() found a missing manual-review step')
COUNTER_WRITE_REVIEW_SUMMARY_MISS = counters.PerfCounter(
    'gcb-pr-write-manual-review-summary-miss',
    'number of times write_manual-review() found a missing manual-review summary')
COUNTER_WRITE_REVIEW_SUCCESS = counters.PerfCounter(
    'gcb-pr-write-manual-review-success',
    'number of times write_manual-review() completed successfully')
COUNTER_WRITE_REVIEW_UPDATED_EXISTING_REVIEW = counters.PerfCounter(
    'gcb-pr-write-manual-review-updated-existing-manual-review',
    'number of times write_manual-review() updated an existing manual-review')


# Number of entities to fetch when querying for all manual-review steps that meet
# given criteria. Ideally we'd cursor through results rather than setting a
# ceiling, but for now let's allow as many removed results as unremoved.
_REVIEW_STEP_QUERY_LIMIT = 2 * staff.MAX_UNREMOVED_REVIEW_STEPS



class Error(Exception):
    """Base error class."""


class ConstraintError(Error):
    """Raised when data is found indicating a constraint is violated."""


class NotAssignableError(Error):
    """Raised when manual-review assignment is requested but cannot be satisfied."""


class RemovedError(Error):
    """Raised when an op cannot be performed on a step because it is removed."""

    def __init__(self, message, value):
        """Constructs a new RemovedError."""
        super(RemovedError, self).__init__(message)
        self.value = value

    def __str__(self):
        return '%s: removed is %s' % (self.message, self.value)


class ReviewProcessAlreadyStartedError(Error):
    """Raised when someone attempts to start a manual-review process in progress."""


class TransitionError(Error):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, message, before, after):
        """Constructs a new TransitionError.

        Args:
            message: string. Exception message.
            before: string in staff.ReviewStates (though this is unenforced).
                State we attempted to transition from.
            after: string in staff.ReviewStates (though this is unenforced).
                State we attempted to transition to.
        """
        super(TransitionError, self).__init__(message)
        self.after = after
        self.before = before

    def __str__(self):
        return '%s: attempted to transition from %s to %s' % (
            self.message, self.before, self.after)

class Manager(object):
    """Object that manages the manual-review subsystem."""

    @classmethod
    @db.transactional()
    def _increment_evaluator_num_assigned_in_txn(cls, user_id, num_increment=1):
        """Increments and returns evaluator.num_assigned in a transaction"""
        cs = course_staff.CourseStaff.get_by_key_name(user_id)
        if cs.num_assigned:
            cs.num_assigned += num_increment
        else:
            cs.num_assigned = num_increment
        cs.put()
        return cs.num_assigned

    @classmethod
    @db.transactional()
    def _increment_evaluator_num_graded_in_txn(cls, user_id, num_increment=1):
        """Increments and returns evaluator.num_graded in a transaction"""
        cs = course_staff.CourseStaff.get_by_key_name(user_id)
        if cs.num_graded:
            cs.num_graded += num_increment
        else:
            cs.num_graded = num_increment
        cs.put()
        return cs.num_graded

    @classmethod
    def _decrement_evaluator_num_assigned_in_txn(cls, user_id, num_decrement=1):
        """Decrements and returns evaluator.num_assigned in a transaction"""
        num_decrement *= -1
        return cls._increment_evaluator_num_assigned_in_txn(
            user_id, num_increment=num_decrement)

    @classmethod
    def _decrement_evaluator_num_graded_in_txn(cls, user_id, num_decrement=1):
        """Decrements and returns evaluator.num_graded in a transaction"""
        num_decrement *= -1
        return cls._increment_evaluator_num_graded_in_txn(
            user_id, num_increment=num_decrement)

    @classmethod
    def calculate_final_score(cls, steps, method):
        """
        Calculates final score.

        `method` can be one of 'average', 'min', 'max'
        """
        scores = [step.score for step in steps]
        final_score = None
        if method == 'average':
            final_score = sum(scores)/len(scores)
        elif method == 'min':
            final_score = min(scores)
        elif method == 'max':
            final_score = max(scores)
        return final_score

    @classmethod
    def submit_for_evaluation(cls, course, unit, student, evaluator_id=None):
        unit_id = str(unit.unit_id)
        submission_key = student_work.Submission.get_key(unit_id, student.get_key())
        summary = staff.ManualEvaluationSummary.get_by_key_name(
            staff.ManualEvaluationSummary.key_name(submission_key))
        if summary and summary.assigned_count > 0:
            return
        return cls.find_and_add_evaluator(
            course, unit, submission_key, student, evaluator_id)

    @classmethod
    def _create_submission(cls, unit_id, submission_key, reviewee_key):
        summary = staff.ManualEvaluationSummary.get_by_key_name(
            staff.ManualEvaluationSummary.key_name(submission_key))
        if not summary:
            summary = staff.ManualEvaluationSummary(
                reviewee_key=reviewee_key, submission_key=submission_key,
                unit_id=unit_id)
            summary.put()

    @classmethod
    def find_evaluator(cls, student, evaluator_id=None):
        staff_list = None
        if evaluator_id:
            cs = course_staff.CourseStaff.get_by_key_name(evaluator_id)
            if cs:
                if not cs.can_grade:
                    staff_list = []
                else:
                    staff_list = [cs]
            else:
                staff_list = []
        else:
            staff_list = course_staff.CourseStaff.all(
                ).filter(course_staff.CourseStaff.can_grade.name, True
                ).fetch(None)

        filtered_list = [s for s in staff_list if s.user_id != student.user_id]
        return sorted(filtered_list,
                      key=lambda staff: staff.num_assigned - staff.num_graded)

    @classmethod
    def get_submission_contents_dict(cls, submission_key):
        """Returns a dict of the submission contents form the submission key"""
        submission = student_work.Submission.get(submission_key)
        if submission:
            submission_contents = transforms.loads(submission.contents)

            # The submission_cointents seems to have gone through
            # transforms.dumps twice.. Hence using transforms.loads on it twice
            # in case.
            # TODO(rthakker) This is bad, make sure it gets transforms.dumped
            # only once.
            if (isinstance(submission_contents, str) or
                    isinstance(submission_contents, unicode)):
                submission_contents = transforms.loads(submission_contents)
            return submission_contents

    @classmethod
    def unshare_submission_with_evaluator(cls, step):
        """Revokes view of the file from the evaluator"""

        errors = []
        for permission in transforms.loads(step['drive_permission_list']):
            drive_service.DriveManager.remove_permission_by_id(
                permission['file_id'], permission['permission_id'], errors)

        if errors:
            logging.error('Failed to un-share with evaluator')
            return False
        return True

    @classmethod
    def share_submission_with_evaluator(
            cls, submission_contents, evaluator_email):
        """Shares the drive files with the evaluator"""

        errors = []
        permission_list = []
        for f in submission_contents['copied_file']:
            permission_dict = drive_service.DriveManager.share_drive_file(
                f['id'], {
                    'type': 'user',
                    'role': 'reader',
                    'value': evaluator_email
                }, errors)
            if permission_dict:
                permission_list.append({
                    'file_id': f['id'],
                    'permission_id': permission_dict['id']
                })
            else:
                errors.append('Failed to share file %s with evaluator'
                               % f['id'])
        # TODO(rthakker) Handle errors better
        if errors:
            logging.error('Failed to share with evaluator %s', evaluator_email)
        return permission_list

    @classmethod
    def find_and_add_evaluator(cls, course, unit, submission_key, student,
            evaluator_id=None):
        """Finds and adds a manual evaluator. Also shares the file if required"""
        unit_id = str(unit.unit_id)
        evaluator = cls.find_evaluator(student, evaluator_id)
        drive_permission_list_dump = None
        # Share the file with the evaluator
        content = question.SubjectiveAssignmentBaseHandler.get_content(
            course, unit)
        num_reviewers = content.get(
            question.SubjectiveAssignmentBaseHandler.OPT_NUM_REVIEWERS, 1)

        # TODO(rthakker) add this to filter once all required entries have
        # indices.
        existing_steps = staff.ManualEvaluationStep.all(
        ).filter('submission_key =', submission_key
        ).fetch(None)
        existing_steps = [step for step in existing_steps if not step.removed]

        existing_evaluators = [step.evaluator for step in existing_steps]
        existing_evaluator_count = len(existing_evaluators)
        required_evaluator_count = num_reviewers - existing_evaluator_count

        if evaluator:
            i = 0
            assigned_evaluator_count = 0
            while (assigned_evaluator_count < min(
                    required_evaluator_count, len(evaluator)) and
                    i < len(evaluator)):
                if question.SubjectiveAssignmentBaseHandler.BLOB == (
                        content.get(question.SubjectiveAssignmentBaseHandler.
                                    OPT_QUESTION_TYPE)):
                    submission_contents = cls.get_submission_contents_dict(
                        submission_key)
                    if submission_contents:
                        drive_permission_list_dump = transforms.dumps(
                            cls.share_submission_with_evaluator(
                                submission_contents, evaluator[i].email))
                if evaluator[i].user_id not in existing_evaluators:
                    cls.add_evaluator(
                        unit_id, submission_key, student.key(), evaluator[i],
                        drive_permission_list=drive_permission_list_dump)
                    assigned_evaluator_count += 1
                i += 1
            return True
        else:
            cls._create_submission(unit_id, submission_key, student.key())
            return False

    @classmethod
    def add_evaluator(cls, unit_id, submission_key, reviewee_key, evaluator,
            drive_permission_list=None):
        """Adds a manual-evaluator for a submission.

        If there is no pre-existing manual-review step, one will be created.

        Attempting to add an existing unremoved step in REVIEW_STATE_ASSIGNED or
        REVIEW_STATE_COMPLETED is an error.

        If there is an existing unremoved manual-review in REVIEW_STATE_EXPIRED, it
        will be put in REVIEW_STATE_ASSIGNED. If there is a removed manual-review in
        REVIEW_STATE_ASSIGNED or REVIEW_STATE_EXPIRED, it will be put in
        REVIEW_STATE_ASSIGNED and unremoved. If it is in REVIEW_STATE_COMPLETED,
        it will be unremoved but its state will not change. In all these cases
        the assigner kind will be set to ASSIGNER_KIND_HUMAN.

        Args:
            unit_id: string. Unique identifier for a unit.
            submission_key: db.Key of models.student_work.Submission. The
                submission being registered.
            reviewee_key: db.Key of models.models.Student. The student who
                authored the submission.
            evaluator: db.Key of models.models.Student. The student to add as
                a manual-evaluator.

        Raises:
            staff.TransitionError: if there is a pre-existing manual-review step found
                in staff.REVIEW_STATE_ASSIGNED|COMPLETED.

        Returns:
            db.Key of written manual-review step.
        """
        try:
            COUNTER_ADD_REVIEWER_START.inc()
            key = cls._add_manual_evaluator(
                unit_id, submission_key, reviewee_key, evaluator,
                drive_permission_list=drive_permission_list)
            COUNTER_ADD_REVIEWER_SUCCESS.inc()
            return key
        except Exception as e:
            nptel_utils.print_exception_with_line_number(e)
            COUNTER_ADD_REVIEWER_FAILED.inc()
            raise e

    @classmethod
    @db.transactional(xg=True)
    def _add_manual_evaluator(cls, unit_id, submission_key, reviewee_key,
            evaluator, drive_permission_list=None):
        found = staff.ManualEvaluationStep.get_by_key_name(
            staff.ManualEvaluationStep.key_name(submission_key, evaluator))
        if not found:
            return cls._add_new_manual_evaluator(
                unit_id, submission_key, reviewee_key, evaluator,
                drive_permission_list=drive_permission_list)
        else:
            return cls._add_manual_evaluator_update_step(found, evaluator,
            drive_permission_list=drive_permission_list)

    @classmethod
    def _add_new_manual_evaluator(
        cls, unit_id, submission_key, reviewee_key, evaluator,
        drive_permission_list=None):
        summary = staff.ManualEvaluationSummary.get_by_key_name(
            staff.ManualEvaluationSummary.key_name(submission_key))
        if summary:
            summary.increment_count(staff.REVIEW_STATE_ASSIGNED)
        else:
            summary = staff.ManualEvaluationSummary(
                assigned_count=1, reviewee_key=reviewee_key,
                submission_key=submission_key, unit_id=unit_id)

        # Synthesize summary key to avoid a second synchronous put op.
        summary_key = db.Key.from_path(
            staff.ManualEvaluationSummary.kind(),
            staff.ManualEvaluationSummary.key_name(submission_key))

        step = staff.ManualEvaluationStep(
            assigner_kind=staff.ASSIGNER_KIND_HUMAN,
            manual_evaluation_summary_key=summary_key, reviewee_key=reviewee_key,
            evaluator=evaluator.user_id, state=staff.REVIEW_STATE_ASSIGNED,
            submission_key=submission_key, unit_id=unit_id)

        if drive_permission_list:
            step.drive_permission_list = drive_permission_list

        cls._increment_evaluator_num_assigned_in_txn(evaluator.user_id)
        step_key, written_summary_key = entities.put([step, summary])

        if summary_key != written_summary_key:
            COUNTER_ADD_REVIEWER_BAD_SUMMARY_KEY.inc()
            raise AssertionError(
                'Synthesized invalid manual-review summary key %s' % repr(summary_key))

        COUNTER_ADD_REVIEWER_CREATE_REVIEW_STEP.inc()
        return step_key

    @classmethod
    def _add_manual_evaluator_update_step(cls, step, evaluator,
            drive_permission_list=None):
        should_increment_human = False
        should_increment_reassigned = False
        should_increment_unremoved = False
        summary = entities.get(step.manual_evaluation_summary_key)

        if not summary:
            COUNTER_ADD_REVIEWER_BAD_SUMMARY_KEY.inc()
            raise AssertionError(
                'Found invalid manual-review summary key %s' % repr(
                    step.manual_evaluation_summary_key))

        if not step.removed:
            if step.state == staff.REVIEW_STATE_EXPIRED:
                should_increment_reassigned = True
                step.state = staff.REVIEW_STATE_ASSIGNED
                summary.decrement_count(staff.REVIEW_STATE_EXPIRED)
                summary.increment_count(staff.REVIEW_STATE_ASSIGNED)
                evaluator.num_assigned += 1
                cls._increment_evaluator_num_assigned_in_txn(evaluator.user_id)
            elif step.state == staff.REVIEW_STATE_COMPLETED:
                step.state = staff.REVIEW_STATE_ASSIGNED
                summary.decrement_count(staff.REVIEW_STATE_COMPLETED)
                summary.increment_count(staff.REVIEW_STATE_ASSIGNED)
                cls._increment_evaluator_num_assigned_in_txn(evaluator.user_id)
                cls._increment_evaluator_num_graded_in_txn(evaluator.user_id)
        else:
            should_increment_unremoved = True
            step.removed = False
            cls._increment_evaluator_num_assigned_in_txn(evaluator.user_id)

            if step.state != staff.REVIEW_STATE_EXPIRED:
                summary.increment_count(step.state)
            else:
                should_increment_reassigned = True
                step.state = staff.REVIEW_STATE_ASSIGNED
                summary.decrement_count(staff.REVIEW_STATE_EXPIRED)
                summary.increment_count(staff.REVIEW_STATE_ASSIGNED)

        if step.assigner_kind != staff.ASSIGNER_KIND_HUMAN:
            should_increment_human = True
            step.assigner_kind = staff.ASSIGNER_KIND_HUMAN

        if drive_permission_list:
            step.drive_permission_list = drive_permission_list

        step_key = entities.put([step, summary])[0]

        if should_increment_human:
            COUNTER_ADD_REVIEWER_SET_ASSIGNER_KIND_HUMAN.inc()
        if should_increment_reassigned:
            COUNTER_ADD_REVIEWER_EXPIRED_STEP_REASSIGNED.inc()
        if should_increment_unremoved:
            COUNTER_ADD_REVIEWER_REMOVED_STEP_UNREMOVED.inc()

        return step_key

    @classmethod
    def delete_manual_evaluator(cls, manual_review_step_key):
        """Deletes the given manual_review step.

        We do not physically delete the manual_review step; we mark it as removed,
        meaning it will be ignored from most queries and the associated manual_review
        summary will have its corresponding state count decremented. Calling
        this method on a removed manual_review step is an error.

        Args:
            manual_review_step_key: db.Key of models.student_work.ManualEvaluationStep. The
                manual_review step to delete.

        Raises:
            RemovedError: if called on a manual_review step that has already
                been marked removed.
            KeyError: if there is no manual_review step with the given key, or if the
                step references a manual_review summary that does not exist.

        Returns:
            db.Key of deleted manual_review step.
        """
        try:
            COUNTER_DELETE_REVIEWER_START.inc()
            key = cls._mark_manual_review_step_removed(manual_review_step_key)
            COUNTER_DELETE_REVIEWER_SUCCESS.inc()
            return key
        except Exception as e:
            nptel_utils.print_exception_with_line_number(e)
            COUNTER_DELETE_REVIEWER_FAILED.inc()
            raise e

    @classmethod
    @db.transactional(xg=True)
    def _mark_manual_review_step_removed(cls, manual_review_step_key):
        step = entities.get(manual_review_step_key)
        if not step:
            COUNTER_DELETE_REVIEWER_STEP_MISS.inc()
            raise KeyError(
                'No manual_review step found with key %s' % repr(manual_review_step_key))
        if step.removed:
            COUNTER_DELETE_REVIEWER_ALREADY_REMOVED.inc()
            raise RemovedError(
                'Cannot remove step %s' % repr(manual_review_step_key), step.removed)
        summary = entities.get(step.manual_evaluation_summary_key)

        if not summary:
            COUNTER_DELETE_REVIEWER_SUMMARY_MISS.inc()
            raise KeyError(
                'No manual_review summary found with key %s' % repr(
                    step.manual_evaluation_summary_key))

        # Decrement the evaluator num_assigned
        cls._decrement_evaluator_num_assigned_in_txn(step.evaluator)
        step.removed = True
        summary.decrement_count(step.state)
        return entities.put([step, summary])[0]

    @classmethod
    def expire_manual_review(cls, manual_review_step_key):
        """Puts a manual_review step in state REVIEW_STATE_EXPIRED.

        Args:
            manual_review_step_key: db.Key of models.student_work.ManualEvaluationStep. The
                manual_review step to expire.

        Raises:
            RemovedError: if called on a step that is removed.
            staff.TransitionError: if called on a manual_review step that cannot be
                transitioned to REVIEW_STATE_EXPIRED (that is, it is already in
                REVIEW_STATE_COMPLETED or REVIEW_STATE_EXPIRED).
            KeyError: if there is no manual_review with the given key, or the step
                references a manual_review summary that does not exist.

        Returns:
            db.Key of the expired manual_review step.
        """
        try:
            COUNTER_EXPIRE_REVIEW_START.inc()
            key = cls._transition_state_to_expired(manual_review_step_key)
            COUNTER_EXPIRE_REVIEW_SUCCESS.inc()
            return key
        except Exception as e:
            nptel_utils.print_exception_with_line_number(e)
            COUNTER_EXPIRE_REVIEW_FAILED.inc()
            raise e

    @classmethod
    @db.transactional(xg=True)
    def _transition_state_to_expired(cls, manual_review_step_key):
        step = entities.get(manual_review_step_key)

        if not step:
            COUNTER_EXPIRE_REVIEW_STEP_MISS.inc()
            raise KeyError(
                'No manual_review step found with key %s' % repr(manual_review_step_key))

        if step.removed:
            COUNTER_EXPIRE_REVIEW_CANNOT_TRANSITION.inc()
            raise RemovedError(
                'Cannot transition step %s' % repr(manual_review_step_key),
                step.removed)

        if step.state in (
                staff.REVIEW_STATE_COMPLETED, staff.REVIEW_STATE_EXPIRED):
            COUNTER_EXPIRE_REVIEW_CANNOT_TRANSITION.inc()
            raise staff.TransitionError(
                'Cannot transition step %s' % repr(manual_review_step_key),
                step.state, staff.REVIEW_STATE_EXPIRED)

        summary = entities.get(step.manual_evaluation_summary_key)

        if not summary:
            COUNTER_EXPIRE_REVIEW_SUMMARY_MISS.inc()
            raise KeyError(
                'No manual_review summary found with key %s' % repr(
                    step.manual_evaluation_summary_key))

        summary.decrement_count(step.state)
        step.state = staff.REVIEW_STATE_EXPIRED
        summary.increment_count(step.state)
        return entities.put([step, summary])[0]

    @classmethod
    def expire_old_manual_reviews_for_unit(cls, manual_review_window_mins, unit_id):
        """Finds and expires all old manual_review steps for a single unit.

        Args:
            manual_review_window_mins: int. Number of minutes before we expire manual_reviews
                assigned by staff.ASSIGNER_KIND_AUTO.
            unit_id: string. Id of the unit to restrict the query to.

        Returns:
            2-tuple of list of db.Key of staff.ManualEvaluationStep. 0th element is keys
            that were written successfully; 1st element is keys that we failed
            to update.
        """
        query = cls.get_expiry_query(manual_review_window_mins, unit_id)
        mapper = utils.QueryMapper(
            query, counter=COUNTER_EXPIRY_QUERY_KEYS_RETURNED, report_every=100)
        expired_keys = []
        exception_keys = []

        def map_fn(manual_review_step_key, expired_keys, exception_keys):
            try:
                expired_keys.append(cls.expire_manual_review(manual_review_step_key))
            except:  # All errors are the same. pylint: disable-msg=bare-except
                # Skip. Either the entity was updated between the query and
                # the update, meaning we don't need to expire it; or we ran into
                # a transient datastore error, meaning we'll expire it next
                # time.
                COUNTER_EXPIRE_OLD_REVIEWS_FOR_UNIT_SKIP.inc()
                exception_keys.append(manual_review_step_key)

        COUNTER_EXPIRE_OLD_REVIEWS_FOR_UNIT_START.inc()

        mapper.run(map_fn, expired_keys, exception_keys)
        COUNTER_EXPIRE_OLD_REVIEWS_FOR_UNIT_EXPIRE.inc(
            increment=len(expired_keys))
        COUNTER_EXPIRE_OLD_REVIEWS_FOR_UNIT_SUCCESS.inc()
        return expired_keys, exception_keys

    @classmethod
    def get_assignment_candidates_query(cls, unit_id):
        """Gets query that returns candidates for new manual_review assignment.

        New assignment candidates are scoped to a unit. We prefer first items
        that have the smallest number of completed manual_reviews, then those that have
        the smallest number of assigned manual_reviews, then those that were created
        most recently.

        The results of the query are user-independent.

        Args:
            unit_id: string. Id of the unit to restrict the query to.

        Returns:
            db.Query that will return [staff.ManualEvaluationSummary].
        """
        return staff.ManualEvaluationSummary.all(
        ).filter(
            staff.ManualEvaluationSummary.unit_id.name, unit_id
        ).order(
            staff.ManualEvaluationSummary.completed_count.name
        ).order(
            staff.ManualEvaluationSummary.assigned_count.name
        ).order(
            staff.ManualEvaluationSummary.create_date.name)

    @classmethod
    def get_expiry_query(
        cls, manual_review_window_mins, unit_id, now_fn=datetime.datetime.utcnow):
        """Gets a db.Query that returns manual_review steps to mark expired.

        Results are items that were assigned by machine, are currently assigned,
        are not removed, were last updated more than manual_review_window_mins ago,
        and are ordered by change date ascending.

        Args:
            manual_review_window_mins: int. Number of minutes before we expire manual_reviews
                assigned by staff.ASSIGNER_KIND_AUTO.
            unit_id: string. Id of the unit to restrict the query to.
            now_fn: function that returns the current UTC datetime. Injectable
                for tests only.

        Returns:
            db.Query.
        """
        get_before = now_fn() - datetime.timedelta(
            minutes=manual_review_window_mins)
        return staff.ManualEvaluationStep.all(keys_only=True).filter(
            staff.ManualEvaluationStep.unit_id.name, unit_id,
        ).filter(
            staff.ManualEvaluationStep.assigner_kind.name, staff.ASSIGNER_KIND_AUTO
        ).filter(
            staff.ManualEvaluationStep.state.name, staff.REVIEW_STATE_ASSIGNED
        ).filter(
            staff.ManualEvaluationStep.removed.name, False
        ).filter(
            '%s <=' % staff.ManualEvaluationStep.change_date.name, get_before
        ).order(
            staff.ManualEvaluationStep.change_date.name)

    @classmethod
    def get_new_manual_review(
        cls, unit_id, evaluator, candidate_count=20, max_retries=5):
        """Attempts to assign a manual_review to a manual_evaluator.

        We prioritize possible manual_reviews by querying manual_review summary objects,
        finding those that best satisfy cls.get_assignment_candidates_query.

        To minimize write contention, we nontransactionally grab candidate_count
        candidates from the head of the query results. Post-query we filter out
        any candidates that are for the prospective manual_evaluator's own work.

        Then we randomly select one. We transactionally attempt to assign that
        manual_review. If assignment fails because the candidate is updated between
        selection and assignment or the assignment is for a submission the
        manual_evaluator already has or has already done, we remove the candidate from
        the list. We then retry assignment up to max_retries times. If we run
        out of retries or candidates, we raise staff.NotAssignableError.

        This is a naive implementation because it scales only to relatively low
        new manual_review assignments per second and because it can raise
        staff.NotAssignableError when there are in fact assignable manual_reviews.

        Args:
            unit_id: string. The unit to assign work from.
            evaluator: db.Key of models.models.Student. The manual_evaluator to
                attempt to assign the manual_review to.
            candidate_count: int. The number of candidate keys to fetch and
                attempt to assign from. Increasing this decreases the chance
                that we will have write contention on manual_reviews, but it costs 1 +
                num_results datastore reads and can get expensive for large
                courses.
            max_retries: int. Number of times to retry failed assignment
                attempts. Careful not to set this too high as a) datastore
                throughput is slow and latency from this method is user-facing,
                and b) if you encounter a few failures it is likely that all
                candidates are now failures, so each retry past the first few is
                of questionable value.

        Raises:
            staff.NotAssignableError: if no manual_review can currently be assigned
                for the given unit_id.

        Returns:
            db.Key of staff.ManualEvaluationStep. The newly created assigned manual_review step.
        """
        try:
            COUNTER_GET_NEW_REVIEW_START.inc()
            # Filter out candidates that are for submissions by the manual_evaluator.
            raw_candidates = cls.get_assignment_candidates_query(unit_id).fetch(
                candidate_count)
            COUNTER_ASSIGNMENT_CANDIDATES_QUERY_RESULTS_RETURNED.inc(
                increment=len(raw_candidates))
            candidates = [
                candidate for candidate in raw_candidates
                if candidate.reviewee_key != evaluator]

            retries = 0
            while True:
                if not candidates or retries >= max_retries:
                    COUNTER_GET_NEW_REVIEW_NOT_ASSIGNABLE.inc()
                    raise staff.NotAssignableError(
                        'No manual_reviews assignable for unit %s and manual_evaluator %s' % (
                            unit_id, repr(evaluator)))
                candidate = cls._choose_assignment_candidate(candidates)
                candidates.remove(candidate)
                assigned_key = cls._attempt_manual_review_assignment(
                    candidate.key(), evaluator, candidate.change_date)

                if not assigned_key:
                    retries += 1
                else:
                    COUNTER_GET_NEW_REVIEW_SUCCESS.inc()
                    return assigned_key

        except Exception, e:
            COUNTER_GET_NEW_REVIEW_FAILED.inc()
            raise e

    @classmethod
    def _choose_assignment_candidate(cls, candidates):
        """Seam that allows different choice functions in tests."""
        return random.choice(candidates)

    @classmethod
    @db.transactional(xg=True)
    def _attempt_manual_review_assignment(
        cls, manual_evaluation_summary_key, evaluator, last_change_date):
        COUNTER_GET_NEW_REVIEW_ASSIGNMENT_ATTEMPTED.inc()
        summary = entities.get(manual_evaluation_summary_key)
        if not summary:
            raise KeyError('No manual_review summary found with key %s' % repr(
                manual_evaluation_summary_key))
        if summary.change_date != last_change_date:
            # The summary has changed since we queried it. We cannot know for
            # sure what the edit was, but let's skip to the next one because it
            # was probably a manual_review assignment.
            COUNTER_GET_NEW_REVIEW_SUMMARY_CHANGED.inc()
            return

        step = staff.ManualEvaluationStep.get_by_key_name(
            staff.ManualEvaluationStep.key_name(summary.submission_key, evaluator))

        if not step:
            step = staff.ManualEvaluationStep(
                assigner_kind=staff.ASSIGNER_KIND_AUTO,
                manual_evaluation_summary_key=summary.key(),
                reviewee_key=summary.reviewee_key, evaluator=evaluator,
                state=staff.REVIEW_STATE_ASSIGNED,
                submission_key=summary.submission_key, unit_id=summary.unit_id)
        else:
            if step.state == staff.REVIEW_STATE_COMPLETED:
                # Reviewer has previously done this manual_review and the manual_review
                # has been deleted. Skip to the next one.
                COUNTER_GET_NEW_REVIEW_CANNOT_UNREMOVE_COMPLETED.inc()
                return

            if step.removed:
                # We can reassign the existing manual_review step.
                COUNTER_GET_NEW_REVIEW_REASSIGN_EXISTING.inc()
                step.removed = False
                step.assigner_kind = staff.ASSIGNER_KIND_AUTO
                step.state = staff.REVIEW_STATE_ASSIGNED
            else:
                # Reviewee has already manual_reviewed or is already assigned to manual_review
                # this submission, so we cannot reassign the step.
                COUNTER_GET_NEW_REVIEW_ALREADY_ASSIGNED.inc()
                return

        summary.increment_count(staff.REVIEW_STATE_ASSIGNED)
        return entities.put([step, summary])[0]

    @classmethod
    def get_manual_review_step_keys_by(cls, unit_id, evaluator):
        """Gets the keys of all manual_review steps in a unit for a manual_evaluator.

        Note that keys for manual_review steps marked removed are included in the
        result set.

        Args:
            unit_id: string. Id of the unit to restrict the query to.
            evaluator: db.Key of models.models.Student. The author of the
                requested manual_reviews.

        Returns:
            [db.Key of staff.ManualEvaluationStep].
        """
        COUNTER_GET_REVIEW_STEP_KEYS_BY_START.inc()

        try:
            query = staff.ManualEvaluationStep.all(keys_only=True).filter(
                staff.ManualEvaluationStep.evaluator.name, evaluator
            ).filter(
                staff.ManualEvaluationStep.unit_id.name, unit_id
            ).order(
                staff.ManualEvaluationStep.create_date.name,
            )

            keys = [key for key in query.fetch(_REVIEW_STEP_QUERY_LIMIT)]

        except Exception as e:
            nptel_utils.print_exception_with_line_number(e)
            COUNTER_GET_REVIEW_STEP_KEYS_BY_FAILED.inc()
            raise e

        COUNTER_GET_REVIEW_STEP_KEYS_BY_SUCCESS.inc()
        COUNTER_GET_REVIEW_STEP_KEYS_BY_KEYS_RETURNED.inc(increment=len(keys))
        return keys

    @classmethod
    def get_manual_review_steps_by_keys(cls, keys):
        """Gets manual_review steps by their keys.

        Args:
            keys: [db.Key of staff.ManualEvaluationStep]. Keys to fetch.

        Returns:
            [staff.ManualEvaluationStep or None]. Missed keys return None in place in
            result list.
        """
        return [
            cls._make_domain_manual_review_step(model) for model in entities.get(keys)]

    @classmethod
    def _make_domain_manual_review_step(cls, model):
        if model is None:
            return

        return staff.ManualEvaluationStep(
            assigner_kind=model.assigner_kind, change_date=model.change_date,
            create_date=model.create_date, key=model.key(),
            removed=model.removed, manual_review_key=model.manual_review_key,
            manual_evaluation_summary_key=model.manual_evaluation_summary_key,
            reviewee_key=model.reviewee_key, evaluator=model.evaluator,
            state=model.state, submission_key=model.submission_key,
            unit_id=model.unit_id
        )

    @classmethod
    def get_manual_reviews_by_keys(cls, keys):
        """Gets manual_reviews by their keys.

        Args:
            keys: [db.Key of manual_review.Review]. Keys to fetch.

        Returns:
            [staff.Review or None]. Missed keys return None in place in result
            list.
        """
        return [cls._make_domain_manual_review(model) for model in entities.get(keys)]

    @classmethod
    def _make_domain_manual_review(cls, model):
        if model is None:
            return

        return staff.Review(contents=model.contents, key=model.key())

    @classmethod
    def get_submission_and_manual_review_step_keys(cls, unit_id, reviewee_key):
        """Gets the submission key/manual_review step keys for the given pair.

        Note that keys for manual_review steps marked removed are included in the
        result set.

        Args:
            unit_id: string. Id of the unit to restrict the query to.
            reviewee_key: db.Key of models.models.Student. The student who
                authored the submission.

        Raises:
            staff.ConstraintError: if multiple manual_review summary keys were found
                for the given unit_id, reviewee_key pair.
            KeyError: if there is no manual_review summary for the given unit_id,
                manual_reviewee pair.

        Returns:
            (db.Key of Submission, [db.Key of staff.ManualEvaluationStep]) if submission
            found for given unit_id, reviewee_key pair; None otherwise.
        """
        COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_START.inc()

        try:
            submission_key = db.Key.from_path(
                student_work.Submission.kind(),
                student_work.Submission.key_name(unit_id, reviewee_key))
            submission = entities.get(submission_key)
            if not submission:
                COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_SUBMISSION_MISS.inc(
                    )
                return

            step_keys_query = staff.ManualEvaluationStep.all(
                keys_only=True
            ).filter(
                staff.ManualEvaluationStep.submission_key.name, submission_key
            )

            step_keys = step_keys_query.fetch(_REVIEW_STEP_QUERY_LIMIT)
            results = (submission_key, step_keys)

        except Exception as e:
            nptel_utils.print_exception_with_line_number(e)
            COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_FAILED.inc()
            raise e

        COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_SUCCESS.inc()
        COUNTER_GET_SUBMISSION_AND_REVIEW_STEP_KEYS_RETURNED.inc(
            increment=len(step_keys))
        return results

    @classmethod
    def get_submissions_by_keys(cls, keys):
        """Gets submissions by their keys.

        Args:
            keys: [db.Key of manual_review.Submission]. Keys to fetch.

        Returns:
            [staff.Submission or None]. Missed keys return None in place in
            result list.
        """
        return [
            cls._make_domain_submission(model) for model in entities.get(keys)]

    @classmethod
    def _make_domain_submission(cls, model):
        if model is None:
            return

        return staff.Submission(contents=model.contents, key=model.key())

    @classmethod
    def start_manual_review_process_for(cls, unit_id, submission_key, reviewee_key):
        """Registers a new submission with the manual_review subsystem.

        Once registered, manual_reviews can be assigned against a given submission,
        either by humans or by machine. No manual_reviews are assigned during
        registration -- this method merely makes them assignable.

        Args:
            unit_id: string. Unique identifier for a unit.
            submission_key: db.Key of models.student_work.Submission. The
                submission being registered.
            reviewee_key: db.Key of models.models.Student. The student who
                authored the submission.

        Raises:
            db.BadValueError: if passed args are invalid.
            staff.ReviewProcessAlreadyStartedError: if the manual_review process has
                already been started for this student's submission.

        Returns:
            db.Key of created ReviewSummary.
        """
        try:
            COUNTER_START_REVIEW_PROCESS_FOR_START.inc()
            key = cls._create_manual_review_summary(
                reviewee_key, submission_key, unit_id)
            COUNTER_START_REVIEW_PROCESS_FOR_SUCCESS.inc()
            return key
        except Exception as e:
            nptel_utils.print_exception_with_line_number(e)
            COUNTER_START_REVIEW_PROCESS_FOR_FAILED.inc()
            raise e

    @classmethod
    @db.transactional(xg=True)
    def _create_manual_review_summary(cls, reviewee_key, submission_key, unit_id):
        collision = staff.ManualEvaluationSummary.get_by_key_name(
            staff.ManualEvaluationSummary.key_name(submission_key))

        if collision:
            COUNTER_START_REVIEW_PROCESS_FOR_ALREADY_STARTED.inc()
            raise staff.ReviewProcessAlreadyStartedError()

        return staff.ManualEvaluationSummary(
            reviewee_key=reviewee_key, submission_key=submission_key,
            unit_id=unit_id,
        ).put()

    @classmethod
    def write_manual_review(
            cls, manual_review_step, comments, score, course,
            mark_completed=False):
        """Writes a manual_review, updating associated internal state.

        If the passed step already has a manual_review, that manual_review will be updated. If
        it does not have a manual_review, a new one will be created with the passed
        payload.

        Args:
            manual_review_step_key: db.Key of staff.ManualEvaluationStep. The key of the manual_review
                step to update.
            manual_review_payload: string. New contents of the manual_review.
            mark_completed: boolean. If True, set the state of the manual_review to
                staff.REVIEW_STATE_COMPLETED. If False, leave the state as it
                was.

        Raises:
            staff.ConstraintError: if no manual_review found for the manual_review step.
            RemovedError: if the step for the manual_review is removed.
            KeyError: if no manual_review step was found with manual_review_step_key.

        Returns:
            db.Key of staff.ManualEvaluationStep: key of the written manual_review step.
        """
        COUNTER_WRITE_REVIEW_START.inc()
        try:
            cls._update_manual_review_contents_and_change_state(
                manual_review_step.key(), comments, score, mark_completed)

            # Update the final score for the student
            unit = course.find_unit_by_id(manual_review_step.unit_id)

            assigned_count = staff.ManualEvaluationStep.all(
            ).filter('state =', staff.REVIEW_STATE_ASSIGNED
            ).filter('removed =', False
            ).filter('submission_key =', manual_review_step.submission_key
            ).count()

            in_progress_count = staff.ManualEvaluationStep.all(
            ).filter('state =', staff.REVIEW_STATE_IN_PROGRESS
            ).filter('removed =', False
            ).filter('submission_key =', manual_review_step.submission_key
            ).count()

            if in_progress_count + assigned_count == 0:
                completed_reviews = staff.ManualEvaluationStep.all(
                ).filter('state =', staff.REVIEW_STATE_COMPLETED
                ).filter('removed =', False
                ).filter('submission_key =', manual_review_step.submission_key
                ).fetch(None)
                cls._update_final_score(
                    completed_reviews, course, unit,
                    manual_review_step.reviewee_key)
        except Exception as e:
            nptel_utils.print_exception_with_line_number(e)
            COUNTER_WRITE_REVIEW_FAILED.inc()
            raise e
        COUNTER_WRITE_REVIEW_SUCCESS.inc()

    @classmethod
    @db.transactional(xg=True)
    def _update_final_score(cls, steps, course, unit, reviewee_key):
        """Computes and updates the final score for a unit"""

        content = question.SubjectiveAssignmentRESTHandler.get_content(
            course, unit)
        method = content.get('scoring_method')
        final_score = cls.calculate_final_score(steps, method)
        if final_score is not None:
            cls._set_score_in_txn(final_score, reviewee_key, unit.unit_id)

    @classmethod
    @db.transactional()
    def _set_score_in_txn(cls, score, reviewee_key, unit_id):
        """Sets the score for a student/unit"""
        student = entities.get([reviewee_key])[0]
        if student:
            utils.set_score(student, str(unit_id), score)
            entities.put([student])
        else:
            logging.error('Student not found %s', reviewee_key)

    @classmethod
    @db.transactional(xg=True)
    def _update_manual_review_contents_and_change_state(
        cls, manual_review_step_key, comment, score, mark_completed):
        should_increment_assigned_to_completed = False
        should_increment_expired_to_completed = False

        step = entities.get(manual_review_step_key)
        if not step:
            COUNTER_WRITE_REVIEW_STEP_MISS.inc()
            raise KeyError(
                'No manual_review step found with key %s' % repr(manual_review_step_key))
        elif step.removed:
            raise RemovedError(
                'Unable to process step %s' % repr(step.key()), step.removed)

        step.comments = comment
        if score is not None:
            step.score = score
        if not mark_completed and not step.state == staff.REVIEW_STATE_COMPLETED:
            step.state = staff.REVIEW_STATE_IN_PROGRESS
            step.put()
            return

        if step.state == staff.REVIEW_STATE_COMPLETED:
            # Reevaluation
            entities.put([step])
            return

        summary = entities.get(step.manual_evaluation_summary_key)
        if not summary:
            COUNTER_WRITE_REVIEW_SUMMARY_MISS.inc()
            raise staff.ConstraintError(
                'No manual_review summary found with key %s' % repr(
                    step.manual_evaluation_summary_key))

        if step.state == staff.REVIEW_STATE_ASSIGNED:
            should_increment_assigned_to_completed = True
        elif step.state == staff.REVIEW_STATE_EXPIRED:
            should_increment_expired_to_completed = True

        summary.decrement_count(step.state)
        step.state = staff.REVIEW_STATE_COMPLETED
        summary.increment_count(step.state)

        cs = course_staff.CourseStaff.get_by_key_name(step.evaluator)
        if cs.num_graded:
            cs.num_graded += 1
        else:
            cs.num_graded = 1
        entities.put([step, summary, cs])

        if should_increment_assigned_to_completed:
            COUNTER_WRITE_REVIEW_COMPLETED_ASSIGNED_STEP.inc()
        elif should_increment_expired_to_completed:
            COUNTER_WRITE_REVIEW_COMPLETED_EXPIRED_STEP.inc()
