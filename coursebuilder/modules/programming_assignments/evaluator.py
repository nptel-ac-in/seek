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


import logging

from models import utils
from models import transforms
import base
from prog_models import ProgrammingAnswersEntity
from prog_models import ProgrammingSumissionEntity
from prog_models import ProgrammingTestCasesEntity

from google.appengine.ext import db

import result


class ProgramEvaluator(object):
    def __init__(self, course, course_settings, unit, content):
        self._course = course
        self._course_settings = course_settings
        self._unit = unit
        self._content = content

    @classmethod
    @db.transactional()
    def update_test_case_stats(cls, student, unit, is_public, stats):
        out = dict()
        for index, stat in enumerate(stats):
            out[index] = (stat.passed, stat.reason)

        entity = ProgrammingTestCasesEntity.get(student, unit.unit_id)
        if entity is None:
            entity = ProgrammingTestCasesEntity.create(student, unit.unit_id)
        if is_public:
            entity.public_test_case_data = transforms.dumps(out)
        else:
            entity.private_test_case_data = transforms.dumps(out)
        entity.put()

    @classmethod
    def check_for_large_responses(cls, response):
        valid_output_length = 500000
        if not response.test_case_results:
            return response

        test_length = len(response.test_case_results)
        valid_output_length = int(valid_output_length/ test_length)

        for test_case in response.test_case_results:
            if test_case.output and len(test_case.output) > valid_output_length:
                test_case.output = '%s...(%s) more chars' % (
                    test_case.output[0:valid_output_length],
                    len(test_case.output) - valid_output_length)
        return response

    @classmethod
    def get_full_code(cls, content, answer):
        full_code = content.get('prefixed_code')
        if not full_code:
            full_code = u''
        elif not full_code.endswith('\n'):
            full_code += '\n'
        if answer:
            full_code += answer
        uneditable_code = content.get('uneditable_code')
        if uneditable_code:
            if not full_code.endswith('\n'):
                full_code += '\n'
            full_code += uneditable_code
        suffixed_invisible_code = content.get('suffixed_invisible_code')
        if suffixed_invisible_code:
            if not full_code.endswith('\n'):
                full_code += '\n'
            full_code += suffixed_invisible_code
        return full_code

    def get_lang_specifc_data(self, lang):
        for lang_details in self._content['allowed_languages']:
            if lang == lang_details['language']:
                return lang_details
        return dict()

    @classmethod
    def store_server_response(cls, student, unit_id, response):
        answer_entity = ProgrammingAnswersEntity.get(student, unit_id)
        if not answer_entity:
            answer_entity = ProgrammingAnswersEntity.create(student, unit_id)
        response = cls.check_for_large_responses(response)
        answer_entity.data = response.serialize()
        answer_entity.put()

    @classmethod
    def store_submission_response(cls, student, unit_id, response):
        answer_entity = ProgrammingSumissionEntity.get(student, unit_id)
        if not answer_entity:
            answer_entity = ProgrammingSumissionEntity.create(student, unit_id)
        response = cls.check_for_large_responses(response)
        answer_entity.data = response.serialize()
        answer_entity.put()


    @classmethod
    def evalute_code(cls, course, course_settings, unit, full_code,
                        program_name, test_id, filename, tests, ignore_presentation_errors,
                        lang):
        raise NotImplementedError

    def evaluate(self, student, is_public, lang, filename, answer):
        lang_data = self.get_lang_specifc_data(lang)
        full_code = self.get_full_code(lang_data, answer)
        pa_id = self._unit.properties.get(base.ProgAssignment.PA_ID_KEY)

        if not is_public:
            # The default id stored in the unit properties is for public test
            # case. If the submission is for private test cases we need to get
            # id for private test cases.
            pa_id = pa_id[:-1] + chr(ord(pa_id[-1:]) - 1)

        program_name = (
            self._course.app_context.get_namespace_name().replace(' ', '_') +
            '.' + lang)

        ignore_presentation_errors = self._content['ignore_presentation_errors']
        if is_public:
            tests = self._content['public_testcase']
        else:
            tests = self._content['private_testcase']

        evaluation_result = self.evalute_code(
            self._course, self._course_settings, self._unit, full_code,
            program_name, pa_id, filename, tests, ignore_presentation_errors, lang)

        if (result.Status.BACKEND_ERROR == evaluation_result.status
            or result.Status.OTHER == evaluation_result.status):
            return evaluation_result

        self.update_test_case_stats(
            student, self._unit, is_public, evaluation_result.test_case_results)

        if is_public:
            self.store_server_response(
                student, self._unit.unit_id, evaluation_result)
            return evaluation_result

        score = 0.0
        pwt = 0
        nwt = 0
        for index, stat in enumerate(evaluation_result.test_case_results):
            if len(tests) <= int(index):
                weight = 1
            else:
                test = tests[int(index)]
                weight = test['weight']

            if stat.passed:
                pwt += weight
            else:
                nwt += weight

        if (pwt+nwt) > 0:
            score = (100 * pwt) / (pwt+nwt)

        evaluation_result.score = score
        utils.set_score(student, self._unit.unit_id, score)
        self.store_submission_response(
            student, self._unit.unit_id, evaluation_result)
        student.put()
        return evaluation_result


class ProgramEvaluatorRegistory(object):
    """A registry that holds all programming evaluators."""

    registered_evaluators = {}

    @classmethod
    def register_evaluator(cls, evaluator_id, evaluator):
        if evaluator_id in cls.registered_evaluators:
            logging.fatal(evaluator_id + ' already registered')
            return
        cls.registered_evaluators[evaluator_id] = evaluator

    @classmethod
    def get(cls, evaluator_id):
        if evaluator_id == 'mooshak_stateless':
            if 'nsjail' in cls.registered_evaluators:
                evaluator_id = 'nsjail'
        return cls.registered_evaluators.get(evaluator_id)

    @classmethod
    def has(cls, evaluator_id):
        return evaluator_id in cls.registered_evaluators

    @classmethod
    def list_ids(cls):
        return cls.registered_evaluators.keys()
