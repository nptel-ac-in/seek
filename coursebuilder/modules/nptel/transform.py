# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Classes and methods to create and manage analytics dashboards."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import logging

from controllers import sites
from controllers.utils import ApplicationHandler
from controllers.utils import BaseHandler
from models import courses
from models import jobs
from models import transforms
from models import utils
from modules.programming_assignments import base as pa_base

import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
from  lxml import etree
import yaml


def get_testcase_from_xml(node):
    testcase = dict()
    for child in node.getchildren():
        if child.tag == 'weight':
          testcase[child.tag] = float(child.text)
        else:
          testcase[child.tag] = child.text
    return testcase


def get_testcases(node):
    test_cases = []
    if node is None:
        return test_cases
    for child in node.getchildren():
        test_cases.append(get_testcase_from_xml(child))
    return test_cases

def string_xml_node_to_dict_entry(
    pdom, tag, content, default_value=unicode('')):
    tag_node = pdom.find(tag)
    if (tag_node is not None and
        tag_node.text != ''):
        content[tag] = tag_node.text
    else:
        content[tag] = default_value

def boolean_xml_node_to_dict_entry(pdom, tag, content, default_value=False):
    content[tag] = default_value
    tag_node = pdom.find(tag)
    if tag_node is not None and tag_node.text != '':
        txt = tag_node.text
        content[tag] = True if txt == unicode(True) else False

def contentxml_to_dict(contentXmlString):
    """Assemble a dict with the unit data fields."""
    content = {}
    if contentXmlString:
        pdom = etree.fromstring(contentXmlString)
        content['question'] = pdom.find('question').text

        public_testcase = pdom.find('public_testcase')
        if public_testcase is not None:
            testcases = public_testcase.find('testcases')
            content['public_testcase'] = get_testcases(testcases)
        else:
            content['public_testcase'] = []

        private_testcase = pdom.find('private_testcase')
        if private_testcase is not None:
            testcases = private_testcase.find('testcases')
            content['private_testcase'] = get_testcases(testcases)
        else:
            content['private_testcase'] = []
        boolean_xml_node_to_dict_entry(pdom, 'show_sample_solution', content)
        boolean_xml_node_to_dict_entry(pdom, 'ignore_presentation_errors', content)

        lang_dict = dict()
        string_xml_node_to_dict_entry(pdom, 'language', lang_dict,
                                      default_value=unicode('c'))
        string_xml_node_to_dict_entry(pdom, 'code_template', lang_dict)
        string_xml_node_to_dict_entry(pdom, 'uneditable_code', lang_dict)
        string_xml_node_to_dict_entry(pdom, 'prefixed_code', lang_dict)
        string_xml_node_to_dict_entry(pdom, 'sample_solution', lang_dict)
        content['allowed_languages'] = [lang_dict]
    return content


class ReFormatProgrammingAssignments(jobs.DurableJob):
    """A job that computes student statistics."""

    def __init__(self, app_context):
        super(ReFormatProgrammingAssignments, self).__init__(app_context)
        self.course = courses.Course(None, app_context=app_context)

    def run(self):
        """Computes student statistics."""

        for unit in self.course.get_units():
            unit_id = str(unit.unit_id)
            logging.info('in unit : ' + unit_id)
            if not unit.is_custom_unit():
                logging.info('not a custom unit : ' + unit_id)
                continue
            if unit.custom_unit_type != pa_base.ProgAssignment.UNIT_TYPE_ID:
                logging.info('not programming assignment : ' + unit_id)
                continue
            content_file = 'assets/js/prog-assignment-%s.js' % unit.unit_id
            content = self.course.get_file_content(content_file)
            if not content:
                logging.info('contennt not found : ' + unit_id)
                continue
            if not content.startswith("<content"):
                logging.info('not xml : ' + unit_id)
                continue
            logging.info("Have to reformat : " + unit_id)
            content_dict = contentxml_to_dict(content)
            pa_base.ProgAssignment.set_content(self.course, unit, content_dict)
            self.course.update_unit(unit)
            logging.info("Updated unit : " + str(unit.unit_id))
        self.course.save()

class ReFormatProgrammingAssignmentsHandler(BaseHandler):
    """ Download students list and store it on drive."""

    def get(self):
        namespaces = self.request.get_all('namespace')
        for context in sites.get_all_courses():
            if (namespaces and len(namespaces) > 0 and
                context.get_namespace_name() not in namespaces):
                continue
            job = ReFormatProgrammingAssignments(context)
            job.submit()
        self.response.write('OK\n')
