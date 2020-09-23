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

from mapreduce import context

from controllers import sites
from controllers.utils import BaseHandler
from models import courses
from models import jobs
from models import models
from models import student_work
from models import transforms
from modules.programming_assignments import base
from modules.programming_assignments import evaluator


class ReevaluateSubmission(jobs.MapReduceJob, base.ProgAssignment):
    """A job that submits request for reevaluation."""

    def __init__(self, app_context, unit_id):
        super(ReevaluateSubmission, self).__init__(app_context)
        self._unit_id = unit_id
        self._job_name = 'job-%s-%s-%s' % (
            self.__class__.__name__, self._namespace, self._unit_id)

    @staticmethod
    def get_description():
        return 'Programming Assignments'

    @staticmethod
    def entity_class():
        return models.Student

    @staticmethod
    def map(entity):
        mapper_params = context.get().mapreduce_spec.mapper.params
        namespace = mapper_params['course']
        unit_id = mapper_params['unit_id']
        content = mapper_params['content']
        settings = mapper_params['settings']

        app_context = sites.get_app_context_for_namespace(namespace)
        course = courses.Course(None, app_context=app_context)
        unit = course.find_unit_by_id(str(unit_id))

        submitted_contents = student_work.Submission.get_contents(
                unit.unit_id, entity.get_key())
        if not submitted_contents:
            return
        submission = transforms.loads(submitted_contents)
        if not submission:
            return
        lang = submission.keys()[0]
        code = submission[lang]['code']
        filename = submission[lang]['filename']

        evaluator_id = content.get('evaluator', 'mooshak')
        evaluator_class = evaluator.ProgramEvaluatorRegistory.get(evaluator_id)
        if not evaluator_class:
            return

        old_score = course.get_score(entity, unit.unit_id)
        prog_evaluator = evaluator_class(course, settings, unit, content)
        prog_evaluator.evaluate(entity, False, lang, filename, code)
        new_score = course.get_score(entity, unit.unit_id)
        yield (str(old_score), new_score)


    def build_additional_mapper_params(self, app_context):
        course = courses.Course(None, app_context=app_context)
        unit = course.find_unit_by_id(str(self._unit_id))
        content = self.get_content(course, unit)
        settings = self.get_course_settings(course)
        return {
            'course': app_context.get_namespace_name(),
            'unit_id': self._unit_id,
            'content': content,
            'settings': settings
            }

    @staticmethod
    def reduce(key, data_list):
        score_dict = dict()
        for new_score in data_list:
            if new_score not in score_dict:
                score_dict[new_score] = 1
            else:
                score_dict[new_score] += 1
        yield (key, score_dict)


class ReevaulateSubmissionHandler(BaseHandler):
    """Iterates through each course and run job to calcalute average score for
    each unit."""

    def get(self):
        namespace = self.request.get('namespace')
        unit_id = self.request.get('unit')
        if namespace and unit_id:
            app_context = sites.get_app_context_for_namespace(namespace)
            if app_context:
                course = courses.Course(None, app_context=app_context)
                if course:
                    unit = course.find_unit_by_id(str(unit_id))
                    if unit:
                        job = ReevaluateSubmission(app_context, unit_id)
                        job.submit()
                        self.response.write('OK\n')
                        return
        self.response.write('Failed\n')
