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

"""Classes and methods to evaluate Programming Assignments."""

__author__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Ambika Agarwal (ambikaagarwal@google.com)']


from cStringIO import StringIO
from httplib import HTTPException
from unicodedata import category
import itertools
import logging
import mimetools
import mimetypes
import urllib2

from common.schema_fields import SchemaField
from models import config
from models import courses
from models import custom_modules
from modules.programming_assignments import base
from modules.programming_assignments import evaluator
from modules.programming_assignments import result
from modules.programming_assignments import settings

from xml.dom import minidom
from xml.parsers.expat import ExpatError


MOOSHAK_TARGET = config.ConfigProperty(
    'mooshak_target', str,
    'The Mooshak target to send code to evaluate. ex: mooshak.example.com or'
    ' 127.0.0.0', '')


MOOSHAK_SERVER = 'mooshak_server'

class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name.encode('utf-8'), value.encode('utf-8')))
        return

    def add_file(self, fieldname, filename, file_handle, mimetype=None):
        """Add a file to be uploaded."""
        body = file_handle.read()
        if mimetype is None:
            mimetype = (mimetypes.guess_type(filename)[0] or
                        'application/octet-stream')
        self.files.append((fieldname.encode('utf-8'), filename.encode('utf-8'),
                           mimetype.encode('utf-8'), body))
        return

    def __str__(self):
        """Returns a string representing the form data, including attached files
        """
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.
        parts = []
        part_boundary = u'--' + self.boundary.encode('utf-8')

        # Add the form fields
        parts.extend(
            [part_boundary,
             u'Content-Disposition: form-data; name="%s"' % name,
             u'',
             value] for name, value in self.form_fields)

        # Add the files to upload
        parts.extend(
            [part_boundary,
             (u'Content-Disposition: file; name="%s"; filename="%s"' %
              (field_name, filename)),
             u'Content-Type: %s' % content_type,
             u'',
             body] for field_name, filename, content_type, body in self.files)

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append(u'--' + self.boundary + u'--')
        flattened.append(u'')
        return b'\r\n'.join(str(item) for item in flattened)


class MooshakEvaluator(evaluator.ProgramEvaluator):
    @classmethod
    def format_data(cls, out):
        if out is None:
            return None
        return out.replace('\n', '\\n\n')

    @classmethod
    def get_xml_data(cls, element_array):
        if len(element_array) == 0:
            return None

        if element_array[0].firstChild is None:
            return None
        return cls.format_data(element_array[0].firstChild.data)

    @classmethod
    def parse_test_results(cls, course, unit, tests, response,
                           ignore_presentation_errors, filename):
        evaluation_result = result.ProgramEvaluationResult()
        if response == '':
            evaluation_result.set_status(result.Status.BACKEND_ERROR)
            return evaluation_result
        try:
            response_xml = minidom.parseString(response)
        except ExpatError as e:
            if response.startswith('<?xml'):
                try:
                    r = response.decode('utf-8')
                    ns = cls.remove_control_chars_from_unicode_string(r)
                    response_xml = minidom.parseString(ns.encode('utf-8'))
                except UnicodeDecodeError as e:
                    ns = cls.remove_control_chars_from_ascii_string(response)
                    response_xml = minidom.parseString(ns)
                except ExpatError as e:
                    evaluation_result.set_status(
                        result.Status.OTHER,
                        'You are printing special characters like \\b in the '
                        'output. We do not support such special characters. '
                        'This could also happen due to segmentation fault '
                        'etc..')
                    logging.error(
                        'Expat error ('+ str(e.code) + ') while parsing : ' +
                        ns + ' in line ' + str(e.lineno) + ' at offset ' +
                        str(e.offset))
                    return evaluation_result
            else:
                evaluation_result.set_status(result.Status.BACKEND_ERROR)
                logging.error(
                    'Expat error ('+ str(e.code) + ') while parsing : ' +
                    response + ' in line ' + str(e.lineno) + ' at offset ' +
                    str(e.offset))
                return evaluation_result

        compile_err_array = response_xml.getElementsByTagName(
            'compilationErrors')
        if (len(compile_err_array) > 0 and
            compile_err_array[0].firstChild is not None):
            compile_err = compile_err_array[0].firstChild.nodeValue
            err_list = [
              x for x in [x.strip() for x in compile_err.split(filename)] if x]

            evaluation_result.set_status(result.Status.COMPILATION_ERROR)
            evaluation_result.compilation_errors = err_list
            return evaluation_result

        test_array = response_xml.getElementsByTagName('test')
        test_length = len(test_array)
        evaluation_result.num_test_evaluated = test_length

        if test_length != len(tests):
            logging.error(
                'Back-end and cb differ in #input tests for assignment ' +
                unit.title + '(' + str(unit.unit_id) + ') in course ' +
                course.app_context.get_namespace_name())
        for i in range(0, test_length):
            entry = result.TestCaseStatus()
            output_array = test_array[i].getElementsByTagName('obtainedOutput')
            entry.output = cls.get_xml_data(output_array)

            expected_array = test_array[i].getElementsByTagName(
                'expectedOutput')
            expected_output = cls.get_xml_data(expected_array)
            entry.expected_output = expected_output

            if len(tests) > i:
                appengine_output = tests[i]['output'].replace('\n', '\\n\n')
                if appengine_output != expected_output:
                    logging.error(
                        'Output in backend is different then output in cb for '
                        'assignment ' + unit.title + '(' + str(unit.unit_id) +
                        ') in course ' +
                        course.app_context.get_namespace_name() + ' at index ' +
                        str(i) + ' Mooshak output :\n' + expected_output +
                        '\nAppEngine Output :\n' + appengine_output +
                        '\nPlease Check')

            classify_array = test_array[i].getElementsByTagName('classify')
            if len(classify_array) > 0:
                if classify_array[0].firstChild is None:
                    entry.passed = True
                    evaluation_result.num_test_passed += 1
                else:
                    entry.reason = classify_array[0].firstChild.nodeValue
                    if (ignore_presentation_errors and
                        entry.reason == 'Presentation Error'):
                        entry.passed = True
                        evaluation_result.num_test_passed += 1
            evaluation_result.test_case_results.append(entry)
        summary_array = response_xml.getElementsByTagName('summary')
        if len(summary_array) == 0:
            return evaluation_result

        classify_array = summary_array[0].getElementsByTagName('classify')
        if len(classify_array) == 0:
            return evaluation_result
        prog_result = classify_array[0].firstChild.nodeValue
        if prog_result == 'Accepted':
            prog_result = 'All Cases Passed'
        evaluation_result.summary = prog_result
        return evaluation_result

    @classmethod
    def remove_control_chars_from_unicode_string(cls, response):
        ns = u''
        for char in response:
            if category(char)[0] == 'C' and (char != u'\n'):
                ns += u'<SpecialCharacter>'
            else:
                ns += char
        return ns

    @classmethod
    def remove_control_chars_from_ascii_string(cls, response):
        ns = ''
        for char in response:
            if (ord(char) < 32 or ord(char) > 126) and char != '\n':
                ns += '<SpecialCharacter>'
            else:
                ns += char
        return ns

    @classmethod
    def send_request(cls, mooshak_ip, code, program_name, pa_id, filename,
                     num_attempts=3):
        mooshak_server = mooshak_ip if mooshak_ip else MOOSHAK_TARGET.value
        # Create the form with simple fields
        request_url = ('http://%s/~mooshak/cgi-bin/evaluate/%s' % (
            mooshak_server, program_name))

        form = MultiPartForm()
        form.add_field('id', pa_id)
        form.add_field('validate', '0')
        form.add_field('submit', 'Execute')
        form.add_field('request', request_url)
        # Add a fake file
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
        response = cls.send_request(
            course_settings.get(MOOSHAK_SERVER), full_code, program_name,
            test_id, filename)
        return cls.parse_test_results(
            course, unit, tests, response, ignore_presentation_errors, filename)


custom_module = None


def register_module():
    """Registers this module in the registry."""
    evaluator.ProgramEvaluatorRegistory.register_evaluator(
        'mooshak', MooshakEvaluator)

    mooshak_server = SchemaField(
        settings.programming_assignment_key(MOOSHAK_SERVER),
        'URL/IP of mooshak server', 'string', '', optional=True)
    mooshak_settings_fields = set()
    mooshak_settings_fields.add(lambda c: mooshak_server)
    courses.Course.OPTIONS_SCHEMA_PROVIDERS[
        base.ProgAssignment.SETTINGS_SECTION] += mooshak_settings_fields

    global custom_module  # pylint: disable=global-statement
    custom_module = custom_modules.Module(
        'Programming Assignment Mooshak Evaluator',
        'A set pages to manage programming assignments.',
        [], [])
    return custom_module
