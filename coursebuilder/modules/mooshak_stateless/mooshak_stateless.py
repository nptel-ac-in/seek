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

"""Classes and methods to evaluate Programming Assignments using Mooshak Stateless."""

__author__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Ambika Agarwal (ambikaagarwal@google.com)',
    'Thejesh GN (tgn@google.com)']

import collections
from cStringIO import StringIO
from httplib import HTTPException
import itertools
import logging
import urllib2
import json

from common.schema_fields import SchemaField
from models import config
from models import courses
from models import custom_modules
from modules.programming_assignments import base
from modules.programming_assignments import evaluator
from modules.programming_assignments import result
from modules.programming_assignments import settings
from modules.mooshak import mooshak


MOOSHAK_STATELESS_TARGET = config.ConfigProperty(
    'mooshak_stateless_target', str,
    'The Mooshak stateless target to send code to evaluate. ex: mooshak.example.com or'
    ' 127.0.0.0', '')


MOOSHAK_STATELESS_SERVER = 'mooshak_stateless_server'


class MooshakStatelessEvaluator(mooshak.MooshakEvaluator):
    @classmethod
    def send_request(cls, mooshak_ip, code, program_name, pa_id, filename,tests,
        lang, lang_settings, num_attempts=3):
        mooshak_server = mooshak_ip if mooshak_ip else MOOSHAK_STATELESS_TARGET.value
        # Create the form with simple fields
        # We will always use proto_service - so that is hardcoded
        request_url = ('http://%s/~mooshak2/cgi-bin/evaluate/proto_service.%s' % (
            mooshak_server, lang))

        form = mooshak.MultiPartForm()
        form.add_field('id', 'B') #we will always use only one, so hardcoded
        form.add_field('validate', '0')
        form.add_field('submit', 'Execute')
        for test in tests:
            test['mark']='1' #default value, we dont use this marks
            test['context']='' #default value
            test['args']='' #default value
            test['show']='yes' #default value
            test['feedback']='Test Case Feedback' #Should we ask for testcase feedback while creating PA?

        compile_args = ""
        execute_args = ""
        if lang_settings and lang_settings.has_key("build"):
            compile_args = lang_settings['build']
        if lang_settings and lang_settings.has_key("exec"):
            execute_args = lang_settings['exec']

        program_parameters =  {
            "language": lang,
            "extension": "." + lang,
            "compile_args": compile_args,
            "execute_args": execute_args,
            "tests": tests
            }

        form.add_field('program_parameters', json.dumps(program_parameters))
        form.add_field('request', request_url)
        form.add_file('program', filename, StringIO(code.encode('utf-8')))

        # Build the request
        request = urllib2.Request(request_url)
        body = str(form)
        request.add_header('Content-type', form.get_content_type())
        request.add_header('Content-length', len(body))
        request.add_data(body)

        for attempt_number in range(num_attempts):
            try:
                timeout = 2
                if 1 == attempt_number:
                    timeout = 6
                elif 2 == attempt_number:
                    timeout = 12
                return  urllib2.urlopen(request, timeout=timeout).read()
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
    def evalute_code(cls, course, course_settings, unit, full_code, program_name,
                     test_id, filename, tests, ignore_presentation_errors, lang):
        course_language_settings = None
        if course_settings.has_key("allowed_languages"):
            for language_settings in course_settings.get("allowed_languages"):
                if language_settings['language'] == lang:
                    course_language_settings = language_settings
                    break

        response = cls.send_request(
            course_settings.get(MOOSHAK_STATELESS_SERVER), full_code, program_name,
            test_id, filename, tests, lang, course_language_settings)
        return cls.parse_test_results(
            course, unit, tests, response, ignore_presentation_errors, filename)


custom_module = None


def register_module():
    """Registers this module in the registry."""
    evaluator.ProgramEvaluatorRegistory.register_evaluator(
        'mooshak_stateless', MooshakStatelessEvaluator)

    mooshak_server = SchemaField(
        settings.programming_assignment_key(MOOSHAK_STATELESS_SERVER),
        'URL/IP of mooshak stateless server', 'string', '', optional=True)
    mooshak_settings_fields = set()
    mooshak_settings_fields.add(lambda c: mooshak_server)
    courses.Course.OPTIONS_SCHEMA_PROVIDERS[
        base.ProgAssignment.SETTINGS_SECTION] += mooshak_settings_fields

    global custom_module  # pylint: disable=global-statement
    custom_module = custom_modules.Module(
        'Programming Assignment Mooshak Stateless Evaluator',
        'A set pages to manage programming assignments.',
        [], [])
    return custom_module
