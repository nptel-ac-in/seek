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

"""Common classes and methods for Manual Evaluation."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

from models import student_work
from models import models

from google.appengine.ext import db

# Identifier for manual-reviews that have been computer-assigned.
ASSIGNER_KIND_AUTO = 'AUTO'
# Identifier for manual-reviews that have been assigned by a human.
ASSIGNER_KIND_HUMAN = 'HUMAN'
ASSIGNER_KINDS = (
    ASSIGNER_KIND_AUTO,
    ASSIGNER_KIND_HUMAN,
)

# Maximum number of ReviewSteps with removed = False, in any REVIEW_STATE, that
# can exist in the backend at a given time.
MAX_UNREMOVED_REVIEW_STEPS = 100

# State of a manual-review that is currently assigned, either by a human or by machine.
REVIEW_STATE_ASSIGNED = 'ASSIGNED'
# State of a manual-review that is currently in progress.
REVIEW_STATE_IN_PROGRESS = 'IN_PROGRESS'
# State of a manual-review that is complete and may be shown to the manual-reviewee, provided
# the manual-reviewee is themself in a state to see their manual-reviews.
REVIEW_STATE_COMPLETED = 'COMPLETED'
# State of a manual-review that used to be assigned but the assignment has been
# expired. Only machine-assigned manual-reviews can be expired.
REVIEW_STATE_EXPIRED = 'EXPIRED'
REVIEW_STATES = (
    REVIEW_STATE_ASSIGNED,
    REVIEW_STATE_IN_PROGRESS,
    REVIEW_STATE_COMPLETED,
    REVIEW_STATE_EXPIRED,
)


class ManualEvaluationSummary(student_work.BaseEntity):
    """Object that tracks the aggregate state of reviews for a submission."""

    # UTC last modification timestamp.
    change_date = db.DateTimeProperty(auto_now=True, required=True)
    # UTC create date.
    create_date = db.DateTimeProperty(auto_now_add=True, required=True)

    # Strong counters. Callers should never manipulate these directly. Instead,
    # use decrement|increment_count.
    # Count of ManualEvaluationStep entities for this submission currently in state
    # STATE_ASSIGNED.
    assigned_count = db.IntegerProperty(default=0, required=True)
    # Count of ManualEvaluationStep entities for this submission currently in state
    # STATE_COMPLETED.
    completed_count = db.IntegerProperty(default=0, required=True)

    # Count of ManualEvaluationStep entities for this submission currently in state
    # STATE_EXPIRED.
    expired_count = db.IntegerProperty(default=0, required=True)

    # Key of the student who wrote the submission being reviewed.
    reviewee_key = student_work.KeyProperty(
        kind=models.Student.kind(), required=True)
    # Key of the submission being reviewed.
    submission_key = student_work.KeyProperty(
        kind=student_work.Submission.kind(), required=True)
    # Identifier of the unit this review is a part of.
    unit_id = db.StringProperty(required=True)

    def __init__(self, *args, **kwargs):
        """Constructs a new ManualEvaluationSummary."""
        assert not kwargs.get('key_name'), (
            'Setting key_name manually not supported')
        submission_key = kwargs.get('submission_key')
        assert submission_key, 'Missing required submission_key property'
        kwargs['key_name'] = self.key_name(submission_key)
        super(ManualEvaluationSummary, self).__init__(*args, **kwargs)

    @classmethod
    def key_name(cls, submission_key):
        """Creates a key_name string for datastore operations."""
        return '(manual_evaluation_summary:%s)' % submission_key.id_or_name()

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        _, _, unit_id, unsafe_reviewee_key_name = cls._split_key(db_key.name())
        unsafe_reviewee_key = db.Key.from_path(
            models.Student.kind(), unsafe_reviewee_key_name)
        unsafe_submission_key = student_work.Submission.get_key(
            unit_id, unsafe_reviewee_key)
        safe_submission_key = student_work.Submission.safe_key(
            unsafe_submission_key, transform_fn)
        return db.Key.from_path(cls.kind(), cls.key_name(safe_submission_key))

    def _check_count(self):
        count_sum = (
            self.assigned_count + self.completed_count + self.expired_count)
        if count_sum >= MAX_UNREMOVED_REVIEW_STEPS:
            COUNTER_INCREMENT_COUNT_COUNT_AGGREGATE_EXCEEDED_MAX.inc()
            raise db.BadValueError(
                'Unable to increment %s to %s; max is %s' % (
                    self.kind(), count_sum, MAX_UNREMOVED_REVIEW_STEPS))

    def decrement_count(self, state):
        """Decrements the count for the given state enum; does not save.

        Args:
            state: string. State indicating counter to decrement; must be one of
                REVIEW_STATES.

        Raises:
            ValueError: if state not in REVIEW_STATES.
        """
        if state == REVIEW_STATE_ASSIGNED or state == REVIEW_STATE_IN_PROGRESS:
            self.assigned_count -= 1
            if self.assigned_count < 0:
                self.assigned_count = 0
        elif state == REVIEW_STATE_COMPLETED:
            self.completed_count -= 1
            if self.completed_count < 0:
                self.completed_count = 0
        elif state == REVIEW_STATE_EXPIRED:
            self.expired_count -= 1
            if self.expired_count < 0:
                self.expired_count = 0
        else:
            raise ValueError('%s not in %s' % (state, REVIEW_STATES))

    def increment_count(self, state):
        """Increments the count for the given state enum; does not save.

        Args:
            state: string. State indicating counter to increment; must be one of
                REVIEW_STATES.

        Raises:
            db.BadValueError: if incrementing the counter would cause the sum of
               all *_counts to exceed MAX_UNREMOVED_REVIEW_STEPS.
            ValueError: if state not in REVIEW_STATES
        """
        if state not in REVIEW_STATES:
            raise ValueError('%s not in %s' % (state, REVIEW_STATES))

        self._check_count()

        if state == REVIEW_STATE_ASSIGNED:
            self.assigned_count += 1
        elif state == REVIEW_STATE_COMPLETED:
            self.completed_count += 1
        elif state == REVIEW_STATE_EXPIRED:
            self.expired_count += 1

    def for_export(self, transform_fn):
        model = super(ManualEvaluationSummary, self).for_export(transform_fn)
        model.reviewee_key = models.Student.safe_key(
            model.reviewee_key, transform_fn)
        model.submission_key = student_work.Submission.safe_key(
            model.submission_key, transform_fn)
        return model


class ManualEvaluationStep(student_work.BaseEntity):
    """Object that represents a single state of a review."""

    # Audit trail information.
    # Identifier for the kind of thing that did the assignment. Used to
    # distinguish between assignments done by humans and those done by the
    # review subsystem.
    assigner_kind = db.StringProperty(
        choices=ASSIGNER_KINDS, required=True)

    # UTC last modification timestamp.
    change_date = db.DateTimeProperty(auto_now=True, required=True)
    # UTC create date.
    create_date = db.DateTimeProperty(auto_now_add=True, required=True)

    # Repeated data to allow filtering/ordering in queries.
    # Key of the submission being reviewed.
    submission_key = student_work.KeyProperty(
        kind=student_work.Submission.kind(), required=True)

    # Unit this review step is part of.
    unit_id = db.StringProperty(required=True, indexed=True)

    # State information.
    # State of this review step.
    state = db.StringProperty(
        choices=REVIEW_STATES, required=True, indexed=True)

    # Whether or not the review has been removed. By default removed entities
    # are ignored for most queries.
    removed = db.BooleanProperty(default=False, indexed=True)

    # Pointers that tie the work and people involved together.

    # Key of the associated ManualEvaluationSummary.
    manual_evaluation_summary_key = student_work.KeyProperty(
        kind=ManualEvaluationSummary.kind())

    # Key of the Student being reviewed.
    reviewee_key = student_work.KeyProperty(
        kind=models.Student.kind(), indexed=False)

    # Key of the Evaluator doing this review.
    evaluator = db.StringProperty(indexed=True, required=True)

    # Evaluation data
    comments = db.TextProperty(indexed=False)
    score = db.FloatProperty(default=0.0, indexed=False)
    drive_permission_list = db.StringProperty(indexed=False)

    def __init__(self, *args, **kwargs):
        """Constructs a new ManualEvaluationStep."""
        assert not kwargs.get('key_name'), (
            'Setting key_name manually not supported')
        evaluator = kwargs.get('evaluator')
        submission_key = kwargs.get('submission_key')
        assert evaluator, 'Missing required evaluator property'
        assert submission_key, 'Missing required submission_key property'
        kwargs['key_name'] = self.key_name(submission_key, evaluator)
        super(ManualEvaluationStep, self).__init__(*args, **kwargs)

    @classmethod
    def key_name(cls, submission_key, evaluator):
        """Creates a key_name string for datastore operations."""
        return '(evaluation_step:%s:%s)' % (
            submission_key.id_or_name(), evaluator)

    @classmethod
    def safe_key(cls, db_key, transform_fn):
        """Constructs a version of the entitiy's key that is safe for export."""
        cls._split_key(db_key.name())
        name = db_key.name().strip('()')
        unsafe_submission_key_name, unsafe_evaluator = name.split(
            ':', 1)[1].rsplit(':', 1)
        safe_evaluator = transform_fn(unsafe_evaluator)

        # Treating as module-protected. pylint: disable-msg=protected-access
        _, unit_id, unsafe_reviewee_key_name = (
            student_work.Submission._split_key(unsafe_submission_key_name))
        unsafe_reviewee_key = db.Key.from_path(
            models.Student.kind(), unsafe_reviewee_key_name)
        unsafe_submission_key = student_work.Submission.get_key(
            unit_id, unsafe_reviewee_key)
        safe_submission_key = student_work.Submission.safe_key(
            unsafe_submission_key, transform_fn)
        return db.Key.from_path(
            cls.kind(), cls.key_name(safe_submission_key, safe_evaluator))

    def for_export(self, transform_fn):
        """Creates a version of the entity that is safe for export."""
        model = super(ManualEvaluationStep, self).for_export(transform_fn)
        model.review_key = student_work.Review.safe_key(
            model.review_key, transform_fn)
        model.manual_evaluation_summary_key = ManualEvaluationSummary.safe_key(
            model.manual_evaluation_summary_key, transform_fn)
        model.reviewee_key = models.Student.safe_key(
            model.reviewee_key, transform_fn)
        model.evaluator = transform_fn(model.evaluator)
        model.submission_key = student_work.Submission.safe_key(
            model.submission_key, transform_fn)
        return model
