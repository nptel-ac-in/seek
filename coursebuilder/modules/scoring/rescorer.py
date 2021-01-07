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

__author__ = 'Thejesh GN (tgn@google.com)'

import logging

from mapreduce import context

from controllers import sites
from models import courses
from models import jobs
from models import models
from models import student_work
from models import utils
from modules.scoring import base
from modules.scoring import scorer
from tools import verify

class RescorerSubmission(jobs.MapReduceJob, base.ScoringBase):
    """A job that submits request for rescoring."""

    def __init__(self, app_context, unit_id, ignore_order=False):
        super(RescorerSubmission, self).__init__(app_context)
        self._unit_id = unit_id
        self._ignore_order = ignore_order
        self._job_name = 'job-%s-%s-%s' % (
            self.__class__.__name__, self._namespace, self._unit_id)

    @staticmethod
    def get_description():
        return 'Rescore Objective Assessments'

    @staticmethod
    def entity_class():
        return models.Student

    @staticmethod
    def map(entity):
        try:
            mapper_params = context.get().mapreduce_spec.mapper.params
            namespace = mapper_params['course']
            unit_id = mapper_params['unit_id']
            ignore_order = mapper_params['ignore_order']

            app_context = sites.get_app_context_for_namespace(namespace)
            course = courses.Course(None, app_context=app_context)
            unit = course.find_unit_by_id(str(unit_id))

            if verify.UNIT_TYPE_ASSESSMENT == unit.type:
                grader = unit.workflow.get_grader()
                if grader == courses.AUTO_GRADER:
                    pass
                else:
                    return
            else:
                return
            enable_negative_marking = unit.enable_negative_marking

            submission = student_work.Submission.get_contents(
                    unit.unit_id, entity.get_key())

            if not submission:
                return

            old_score = course.get_score(entity, unit.unit_id)
            new_score = scorer.score_assessment(submission, unit.html_content, enable_negative_marking, ignore_order=ignore_order)
            utils.set_score(entity, unit.unit_id, new_score)
            entity.put()
            yield (str(old_score), new_score)
        except Exception as e:
            from modules.nptel import utils as nptel_utils
            logging.error('Error while running Rescore Objective Assessments:')
            nptel_utils.print_exception_with_line_number(e)
            raise e

    def build_additional_mapper_params(self, app_context):
        course = courses.Course(None, app_context=app_context)
        unit = course.find_unit_by_id(str(self._unit_id))
        return {
            'course': app_context.get_namespace_name(),
            'unit_id': self._unit_id,
            'ignore_order':self._ignore_order,
            }

    @staticmethod
    def reduce(key, data_list):
        pass
