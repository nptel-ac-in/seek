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

__author__ = 'Rishav Thakker (rthakker@google.com)'

import logging

from modules.programming_assignments import assignment
from modules.programming_assignments import result
from modules.programming_assignments import prog_models
from models import transforms

class ProgrammingAssignmentTestRun(object):
    """
    Class containing functions related to programming assignment test runs
    """

    @classmethod
    def save_test_run_details(cls, unit, data):
        return (
            prog_models.ProgrammingAssignmentTestRunEntity
            .save_evaluation_result(unit.unit_id, transforms.dumps(
                data)))

    @classmethod
    def test_run(cls, course, unit, entity_dict, errors):
        content_dict = entity_dict['content']
        # Set flag to see if at least one solution runs properly
        one_test_run_complete = False
        evaluation_results_dict = {}
        student = course.get_or_create_bot_student()
        all_passed = True
        for lang_dict in content_dict['allowed_languages']:
            lang = lang_dict['language']
            answer = lang_dict['sample_solution']
            filename = lang_dict['filename'].strip()
            is_public = True
            if not answer.strip():
                continue
            evaluation_results_dict[lang] = {}
            for visibility in 'public', 'private':
                is_public = visibility == 'public'
                evaluation_result = (
                    assignment.ProgAssignmentHandler.get_evaluation_result(
                        course=course, unit=unit, content=content_dict,
                        student=student, is_public=is_public,
                        lang=lang, filename=filename, answer=answer))
                evaluation_results_dict[lang][visibility] = (
                    transforms.loads(evaluation_result.serialize()))
                if (evaluation_result.status != result.Status.OK
                        or evaluation_result.summary !=
                        'All Cases Passed'):
                    errors.append('Lang: %s Summary: %s' % (
                        lang, evaluation_result.summary))
                    error_dict = {
                        'lang': lang,
                        'code': answer,
                        'result': evaluation_result.serialize()
                    }
                    logging.info('Failed compile/run attempt: %s',
                                 transforms.dumps(error_dict))
                    all_passed = False

            one_test_run_complete = True
        if not one_test_run_complete:
            errors.append("Please provide one sample solution to test run")
            return False
        cls.save_test_run_details(unit, evaluation_results_dict)
        return all_passed

    @classmethod
    def get_assignment_template_value(cls, evaluation_result, content_dict):
        """
        Parses the evaluation result and returns dict to be used in template
        for test_response.html
        """
        template_value = {
            'sample_tests': (content_dict['public_testcase']
                             + content_dict['private_testcase']),
            'check_answers': 'True',
            'response': evaluation_result,
        }
        evaluation_result['compilation_errors'] = transforms.loads(
            evaluation_result['compilation_errors'])
        if evaluation_result['compilation_errors']:
            template_value['ierr'] = ' '.join(
                evaluation_result['compilation_errors'])
        return template_value
