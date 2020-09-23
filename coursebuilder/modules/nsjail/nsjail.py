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

"""
Classes and methods to evaluate Programming Assignments using nsjail
programming server.
"""

__author__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Ambika Agarwal (ambikaagarwal@google.com)',
    'Thejesh GN (tgn@google.com)',
    'Rishav Thakker(rthakker@google.com)']

from httplib import HTTPException
import logging
import urllib2
import json

from google import protobuf

from common.schema_fields import SchemaField
from models import config
from models import courses
from models import custom_modules
from modules.nsjail.proto import request_pb2
from modules.programming_assignments import base
from modules.programming_assignments import evaluator
from modules.programming_assignments import result
from modules.programming_assignments import settings


NSJAIL_TARGET = config.ConfigProperty(
    'nsjail_target', str,
    'The Nsjail target to send code to evaluate. ex: nsjail.example.com or'
    ' 127.0.0.0', '')


NSJAIL_SERVER = 'nsjail_server'

ERROR_LIST = {
    request_pb2.CodeReply.MEMORY_LIMIT_EXCEEDED: 'Memory Limit Exceeded',
    request_pb2.CodeReply.TIME_LIMIT_EXCEEDED: 'Time Limit Exceeded',
    request_pb2.CodeReply.RUNTIME_ERROR: 'Runtime Error',
    request_pb2.CodeReply.WRONG_ANSWER: 'Wrong Answer',
    request_pb2.CodeReply.PRESENTATION_ERROR: 'Presentation Error',
    request_pb2.CodeReply.COMPILATION_ERROR: 'Compilation Error'
}

class NsjailEvaluator(evaluator.ProgramEvaluator):
    @classmethod
    def parse_test_results(cls, course, unit, tests, response,
                           ignore_presentation_errors, filename):
        evaluation_result = result.ProgramEvaluationResult()
        if response == '':
            evaluation_result.set_status(result.Status.BACKEND_ERROR)
            return evaluation_result

        # Merge response
        response_proto = protobuf.text_format.Merge(
            response['message'], request_pb2.CodeReply())

        # Check for compilation errors
        if (response_proto.compilation_result.status ==
                request_pb2.CodeReply.COMPILATION_ERROR):
            err_list = [response_proto.compilation_result.output,
                        response_proto.compilation_result.error]
            evaluation_result.set_status(result.Status.COMPILATION_ERROR)
            evaluation_result.compilation_errors = err_list
            evaluation_result.summary = ERROR_LIST[
                request_pb2.CodeReply.COMPILATION_ERROR]
            return evaluation_result

        test_array = response_proto.test_case_results
        test_length = len(test_array)
        evaluation_result.num_test_evaluated = test_length

        if test_length != len(tests):
            logging.error(
                'Back-end and cb differ in #input tests for assignment ' +
                unit.title + '(' + str(unit.unit_id) + ') in course ' +
                course.app_context.get_namespace_name())

        for i in range(0, test_length):
            entry = result.TestCaseStatus()
            entry.output = test_array[i].actual_output.replace('\n', '\\n\n')

            # TODO(rthakker) send expected output as well
            # entry.expected_output = tests[i]['output'].replace('\n', '\\n\n')

            if len(tests) > i:
                appengine_output = tests[i]['output'].replace('\n', '\\n\n')
                entry.expected_output = appengine_output

            if test_array[i].status == request_pb2.CodeReply.OK:
                entry.passed = True
                evaluation_result.num_test_passed += 1
            elif (test_array[i].status ==
                  request_pb2.CodeReply.PRESENTATION_ERROR):
                entry.reason = ERROR_LIST[
                    request_pb2.CodeReply.PRESENTATION_ERROR]
                if ignore_presentation_errors:
                    entry.passed = True
                    evaluation_result.num_test_passed += 1
                else:
                    entry.passed = False
                    evaluation_result.summary = entry.reason
            else:
                if (test_array[i].status ==
                        request_pb2.CodeReply.RUNTIME_ERROR):
                    entry.output += test_array[i].error.replace('\n', '\\n\n')
                entry.reason = ERROR_LIST[test_array[i].status]
                evaluation_result.summary = entry.reason
                entry.passed = False
            evaluation_result.test_case_results.append(entry)

        if evaluation_result.num_test_passed == len(tests):
            evaluation_result.summary = 'All Cases Passed'
        return evaluation_result

    @classmethod
    def send_request(cls, nsjail_ip, code, program_name, pa_id, filename, tests,
        lang, lang_settings, num_attempts=3):
        server_ip = nsjail_ip if nsjail_ip else NSJAIL_TARGET.value
        request_url = 'http://%s' % server_ip

        settings_dict = {
            'time_limit': None,
            'memory_limit': None,
            'process_limit': None,
            'compilation_time_limit': None,
            'compilation_memory_limit': None,
            'compilation_process_limit': None
        }
        if lang_settings:
            for key, val in lang_settings.iteritems():
                if val:
                    settings_dict[key] = val

        request_proto = request_pb2.CodeRequest()
        request_proto.code.full_code = code
        request_proto.code.filename = filename
        request_proto.code.binary_filename = '.'.join(filename.split('.')[:-1])
        request_proto.language = lang
        if settings_dict['compilation_time_limit']:
            request_proto.compilation_options.resource_limits.time_limit = (
                settings_dict['compilation_time_limit'])
        if settings_dict['compilation_memory_limit']:
            request_proto.compilation_options.resource_limits.memory_limit = (
                settings_dict['compilation_memory_limit'])
        if settings_dict['compilation_process_limit']:
            request_proto.compilation_options.resource_limits.process_limit = (
                settings_dict['compilation_process_limit'])

        if settings_dict['time_limit']:
            request_proto.runtime_options.resource_limits.time_limit = (
                settings_dict['time_limit'])
        if settings_dict['memory_limit']:
            request_proto.runtime_options.resource_limits.memory_limit = (
                settings_dict['memory_limit'])
        if settings_dict['process_limit']:
            request_proto.runtime_options.resource_limits.process_limit = (
                settings_dict['process_limit'])

        for test in tests:
            testcase = request_proto.testcases.add()
            testcase.input = test['input']
            testcase.output = test['output']

        exec_args = settings_dict.get('exec')
        compile_args = settings_dict.get('build')
        if exec_args:
            request_proto.runtime_options.extra_args.extend(exec_args.split())
        if compile_args:
            request_proto.compilation_options.extra_args.extend(
                compile_args.split())

        # Build the request
        request = urllib2.Request(request_url)
        body = json.dumps({
            'message': protobuf.text_format.MessageToString(request_proto)
        })
        request.add_header('Content-type', 'application/json')
        request.add_header('Content-length', len(body))
        request.add_data(body)

        max_time_limit = max(
            settings_dict['time_limit'],
            settings_dict['compilation_time_limit'])

        if max_time_limit:
            min_timeout = max_time_limit + 1
        else:
            min_timeout = 10

        for attempt_number in range(num_attempts):
            try:
                timeout = min_timeout
                if 1 == attempt_number:
                    timeout = min_timeout * 2
                elif 2 == attempt_number:
                    timeout = min_timeout * 3
                response = urllib2.urlopen(request, timeout=timeout).read()
                return json.loads(response)
            except urllib2.HTTPError, e:
                logging.error(str(e))
                break
            except urllib2.URLError, e:
                logging.error(str(e))
                break
            except HTTPException, e:
                err = str(e)
                if not err.startswith(
                    'Deadline exceeded while waiting for HTTP response'):
                    break
                if 2 == attempt_number:
                    logging.error(
                        '3 retries done, all failed with deadline exceeded.')
                else:
                    logging.info('deadline exceeded .. retrying')
        return ''


    @classmethod
    def evalute_code(cls, course, course_settings, unit, full_code,
                     program_name, test_id, filename, tests,
                     ignore_presentation_errors, lang):
        course_language_settings = None
        if course_settings.has_key("allowed_languages"):
            for language_settings in course_settings.get("allowed_languages"):
                if language_settings['language'] == lang:
                    course_language_settings = language_settings
                    break

        response = cls.send_request(
            course_settings.get(NSJAIL_SERVER), full_code, program_name,
            test_id, filename, tests, lang, course_language_settings)
        return cls.parse_test_results(
            course, unit, tests, response, ignore_presentation_errors, filename)


custom_module = None


def register_module():
    """Registers this module in the registry."""
    evaluator.ProgramEvaluatorRegistory.register_evaluator(
        'nsjail', NsjailEvaluator)

    nsjail_server = SchemaField(
        settings.programming_assignment_key(NSJAIL_SERVER),
        'URL/IP of nsjail stateless server', 'string', '', optional=True)
    nsjail_settings_fields = set()
    nsjail_settings_fields.add(lambda c: nsjail_server)
    courses.Course.OPTIONS_SCHEMA_PROVIDERS[
        base.ProgAssignment.SETTINGS_SECTION] += nsjail_settings_fields

    global custom_module  # pylint: disable=global-statement
    custom_module = custom_modules.Module(
        'Programming Assignment Nsjail Evaluator',
        'A set pages to manage programming assignments.',
        [], [])
    return custom_module
