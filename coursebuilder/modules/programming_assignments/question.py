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

"""Classes and methods to create and manage Programming Assignments."""

__author__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Ambika Agarwal (ambikaagarwal@google.com)']


import yaml
import cgi

from common import tags
from common.schema_fields import FieldArray
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from controllers.utils import BaseRESTHandler
from controllers.utils import XsrfTokenManager
from models import courses
from models import roles
from models import transforms
from models import messages
from modules.oeditor import oeditor
from modules.programming_assignments import base
from modules.programming_assignments import evaluator
from modules.programming_assignments import test_run
from tools import verify


DRAFT_TEXT = 'Private'
PUBLISHED_TEXT = 'Public'
PROG_ASSIGNMENT_FILES_PROPERTY_KEY = 'files'
STATUS_ANNOTATION = oeditor.create_bool_select_annotation(
    ['properties', 'is_draft'], 'Status', DRAFT_TEXT,
    PUBLISHED_TEXT, class_name='split-from-main-group')


def workflow_key(key):
    return 'workflow:%s' % key


def content_key(key):
    return 'content:%s' % key


def create_prog_assignment_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Prog Assignment Entity', description='Prog Assignment',
        extra_schema_dict_values={
            'className': 'inputEx-Group new-form-layout'})

    # Course level settings.
    course_opts = reg.add_sub_registry('prog_assignment', 'Assignment Config')
    course_opts.add_property(SchemaField(
        'key', 'ID', 'string', editable=False,
        extra_schema_dict_values={'className': 'inputEx-Field keyHolder'},
        description='Unique Id of the Assignment'))
    course_opts.add_property(SchemaField(
        'pa_id', 'PA_ID', 'string', editable=False,
        extra_schema_dict_values={'className': 'inputEx-Field keyHolder'},
        description='Unique id of the test cases in this assignment.'))
    course_opts.add_property(SchemaField('parent_unit', 'Parent Unit', 'string', editable=False, select_data=[]))
    course_opts.add_property(
        SchemaField('type', 'Type', 'string', editable=False))
    course_opts.add_property(
        SchemaField('title', 'Title', 'string', optional=False))
    course_opts.add_property(
        SchemaField('weight', 'Weight', 'number', optional=False))

    course_opts.add_property(SchemaField(
        content_key('question'), 'Problem Statement', 'html', optional=False,
        description=('Problem Statement and description of program, visible'
                     ' to student.'),
        extra_schema_dict_values={
            'supportCustomTags': tags.CAN_USE_DYNAMIC_TAGS.value,
            'className': 'inputEx-Field content'}))
    course_opts.add_property(SchemaField(
        'html_check_answers', 'Allow "Compile & Run"', 'boolean',
        optional=True,
        extra_schema_dict_values={
            'className': 'inputEx-Field assessment-editor-check-answers'}))

    course_opts.add_property(SchemaField(
        content_key('evaluator'), 'Program Evaluator', 'string', optional=True,
        select_data=[
            (eid, eid)
            for eid in evaluator.ProgramEvaluatorRegistory.list_ids()]))

    course_opts.add_property(SchemaField(
        content_key('ignore_presentation_errors'), 'Ignore Presentation Errors',
        'boolean', optional=True,
        extra_schema_dict_values={
            'className': 'inputEx-Field assessment-editor-check-answers'}))

    course_opts.add_property(
        SchemaField(workflow_key(courses.SUBMISSION_DUE_DATE_KEY),
                    'Submission Due Date', 'datetime', optional=False,
                    description=messages.ASSESSMENT_DUE_DATE_FORMAT_DESCRIPTION,
                    extra_schema_dict_values={'_type': 'datetime'}))
    course_opts.add_property(SchemaField(
        content_key('show_sample_solution'),
        'Show sample solution after deadline', 'boolean', optional=True,
        extra_schema_dict_values={
            'className': 'inputEx-Field assessment-editor-check-answers'}))

    test_case_opts = FieldRegistry('', '')
    test_case_opts.add_property(SchemaField(
        'input', 'Input', 'text', optional=True,
        extra_schema_dict_values={}))

    test_case_opts.add_property(SchemaField(
        'output', 'Output', 'text', optional=True,
        extra_schema_dict_values={'className': 'inputEx-Field content'}))

    test_case_opts.add_property(SchemaField(
        'weight', 'Weight', 'number', optional=False,
        extra_schema_dict_values={'className': 'inputEx-Field content','value':1}))

    public_test_cases = FieldArray(
        content_key('public_testcase'), '', item_type=test_case_opts,
        extra_schema_dict_values={
            'sortable': False,
            'listAddLabel': 'Add Public Test Case',
            'listRemoveLabel': 'Delete'})
    public_tests_reg = course_opts.add_sub_registry(
        'public_testcase', title='Public Test Cases')
    public_tests_reg.add_property(public_test_cases)

    private_test_cases = FieldArray(
        content_key('private_testcase'), '', item_type=test_case_opts,
        extra_schema_dict_values={
            'sortable': False,
            'listAddLabel': 'Add Private Test Case',
            'listRemoveLabel': 'Delete'})
    private_tests_reg = course_opts.add_sub_registry(
        'private_testcase', title='Private Test Cases')
    private_tests_reg.add_property(private_test_cases)

    lang_reg = course_opts.add_sub_registry(
        'allowed_languages', title='Allowed Programming Languages')
    language_opts = FieldRegistry('', '')
    language_opts.add_property(
        SchemaField(
            'language', 'Programming Language', 'string',
            select_data=base.ProgAssignment.PROG_LANG_FILE_MAP.items()))
    language_opts.add_property(SchemaField(
        'prefixed_code', 'Prefixed Fixed Code', 'text', optional=True,
        description=('The uneditable code for the assignment. '
                     'This will be prepended at the start of user code'),
        extra_schema_dict_values={'className': 'inputEx-Field content'}))
    language_opts.add_property(SchemaField(
        'code_template', 'Template Code', 'text', optional=True,
        description=('The default code that is populated on opening ' +
                     'an assignment.'),
        extra_schema_dict_values={'className': 'inputEx-Field content'}))
    language_opts.add_property(SchemaField(
        'uneditable_code', 'Suffixed Fixed Code', 'text', optional=True,
        description=('The uneditable code for the assignment. '
                     'This will be appended at the end of user code'),
        extra_schema_dict_values={'className': 'inputEx-Field content'}))
    language_opts.add_property(SchemaField(
        'suffixed_invisible_code', 'Invisible Code', 'text', optional=True,
        description=('This code will not be visible to the student and will be'
                     ' appended at the very end.'),
        extra_schema_dict_values={'className': 'inputEx-Field content'}))
    language_opts.add_property(SchemaField(
        'sample_solution', 'Sample Solution', 'text',
        optional=True,
        extra_schema_dict_values={'className': 'inputEx-Field'}))
    language_opts.add_property(SchemaField(
        'filename', 'Sample Solution Filename', 'string',
        optional=True,
        extra_schema_dict_values={'className': 'inputEx-Field'}))
    allowed_languages = FieldArray(
        content_key('allowed_languages'), '',
        item_type=language_opts,
        extra_schema_dict_values={
            'sortable': False,
            'listAddLabel': 'Add Language',
            'listRemoveLabel': 'Delete',
            'minItems': 1})
    lang_reg.add_property(allowed_languages)

    course_opts.add_property(
        SchemaField('is_draft', 'Status', 'boolean',
                    select_data=[(True, DRAFT_TEXT), (False, PUBLISHED_TEXT)],
                    extra_schema_dict_values={
                        'className': 'split-from-main-group'}))
    return reg


class ProgAssignmentRESTHandler(BaseRESTHandler, base.ProgAssignment):
    """Provides REST API to prog assignment."""

    URI = '/rest/course/progassignment'
    DESCRIPTION = 'Programming Assignments'
    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']
    SCHEMA_JSON = create_prog_assignment_registry().get_json_schema()

    @classmethod
    def get_schema(cls, unused_handler):
        return cls.registration()

    @classmethod
    def registration(cls):
        return create_prog_assignment_registry()

    @classmethod
    def get_schema_dict(cls):
        return cls.registration().get_json_schema_dict()

    @classmethod
    def get_schema_annotations_dict(cls, course):
        unit_list = []
        for unit in course.get_units():
            if unit.type == 'U':
                unit_list.append(
                    (unit.unit_id,
                     cgi.escape('Unit %s - %s' % (unit.index, unit.title))))
        extra_select_options = dict()
        extra_select_options['prog_assignment'] = dict()
        extra_select_options['prog_assignment']['parent_unit'] = unit_list
        return  cls.registration().get_schema_dict(extra_select_options=extra_select_options)

    def unit_to_dict(self, course, unit):
        """Assemble a dict with the unit data fields."""
        assert verify.UNIT_TYPE_CUSTOM == unit.type
        assert self.UNIT_TYPE_ID == unit.custom_unit_type

        content = self.get_content(course, unit)

        if 'allowed_languages' not in content.keys():
            course_settings = self.get_course_settings(course)
            content['allowed_languages'] = course_settings.get(
                'allowed_languages', [])

        workflow = unit.workflow

        if workflow.get_submission_due_date():
            submission_due_date = workflow.get_submission_due_date()
        else:
            submission_due_date = None

        workflow_dict = dict()
        workflow_dict[courses.SUBMISSION_DUE_DATE_KEY] = submission_due_date
        workflow_dict[courses.GRADER_KEY] = workflow.get_grader()

        entity = {
                'key': unit.unit_id,
                'type': self.UNIT_TYPE_ID,
                'title': unit.title,
                'pa_id': unit.properties.get(self.PA_ID_KEY),
                'parent_unit': unit.parent_unit if unit.parent_unit else 0,
                'weight': str(unit.weight if hasattr(unit, 'weight') else 0),
                'html_check_answers': unit.html_check_answers,
                'is_draft': not unit.now_available,
                'workflow' : workflow_dict,
                'content': content,
                }
        json_entity = dict()
        self.registration().convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    def apply_updates(self, course, unit, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        entity_dict = {}
        self.registration().convert_json_to_entity(
            updated_unit_dict, entity_dict)

        unit.title = entity_dict.get('title')
        unit.parent_unit = int(entity_dict.get('parent_unit'))
        if unit.parent_unit < 1:
            unit.parent_unit = None
        try:
            unit.weight = int(entity_dict.get('weight'))
            if unit.weight < 0:
                errors.append('The weight must be a non-negative integer.')
                return
        except ValueError:
            errors.append('The weight must be an integer.')
            return

        unit.now_available = not entity_dict.get('is_draft')
        unit.html_content = entity_dict.get('html_content')
        unit.html_check_answers = entity_dict.get('html_check_answers')

        workflow_dict = entity_dict.get('workflow')

        # Convert the due date
        # TODO(rthakker) since this code is being used in 3 places, move it
        # somewhere reusable.
        due_date = workflow_dict.get(courses.SUBMISSION_DUE_DATE_KEY)
        if due_date:
            workflow_dict[courses.SUBMISSION_DUE_DATE_KEY] = due_date.strftime(
                courses.ISO_8601_DATE_FORMAT)

        workflow_dict[courses.GRADER_KEY] = courses.AUTO_GRADER
        unit.workflow_yaml = yaml.safe_dump(workflow_dict)
        unit.workflow.validate(errors=errors)

        content_dict = entity_dict['content']
        self.set_content(course, unit, content_dict)

        assert course.update_unit(unit)
        course.save()

        # Compile and run the test cases once
        if not (test_run.ProgrammingAssignmentTestRun
                .test_run(course, unit, entity_dict, errors)):
            errors.append('Saved, but could not compile and run.\n'
                'For more details, go to /dashboard?action=test_run\n'
                'Please validate testcases and server settings')

    def get(self):
        """A GET REST method shared by all unit types."""
        key = self.request.get('key')

        if not roles.Roles.is_course_admin(self.app_context):
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        course = courses.Course(self)
        unit = course.find_unit_by_id(key)
        if not unit:
            transforms.send_json_response(
                self, 404, 'Object not found.', {'key': key})
            return

        message = ['Success.']
        if self.request.get('is_newly_created'):
            message.append(
                'New %s has been created and saved.' % self.NAME)

        transforms.send_json_response(
            self, 200, '\n'.join(message),
            payload_dict=self.unit_to_dict(course, unit),
            xsrf_token=XsrfTokenManager.create_xsrf_token('put-unit'))

    def put(self):
        """A PUT REST method shared by all unit types."""
        request = transforms.loads(self.request.get('request'))
        key = request.get('key')

        if not self.assert_xsrf_token_or_fail(
                request, 'put-unit', {'key': key}):
            return

        if not roles.Roles.is_course_admin(self.app_context):
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        course = courses.Course(self)
        unit = course.find_unit_by_id(key)
        if not unit:
            transforms.send_json_response(
                self, 404, 'Object not found.', {'key': key})
            return

        payload = request.get('payload')
        updated_unit_dict = transforms.json_to_dict(
            transforms.loads(payload), self.get_schema_dict())

        errors = []
        self.apply_updates(course, unit, updated_unit_dict, errors)
        if not errors:
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))

    def delete(self):
        """Handles REST DELETE verb with JSON payload."""
        key = self.request.get('key')

        if not self.assert_xsrf_token_or_fail(
                self.request, 'delete-unit', {'key': key}):
            return

        if not roles.Roles.is_course_admin(self.app_context):
            transforms.send_json_response(
                self, 401, 'Access denied.', {'key': key})
            return

        course = courses.Course(self)
        unit = course.find_unit_by_id(key)
        if not unit:
            transforms.send_json_response(
                self, 404, 'Object not found.', {'key': key})
            return
        course.delete_unit(unit)
        course.save()
        transforms.send_json_response(self, 200, 'Deleted.')


def get_test_case_id(num):
    remainder = (num) % 26
    letter = chr(int(remainder + ord('A')))
    num2 = num / 26
    if num2 > 0:
        return get_test_case_id(num2 - 1) + letter
    else:
        return letter


def create_assignment(course, unit):
    next_pa_id = base.ProgAssignment.get_next_test_suite_id(course)
    test_case_id = get_test_case_id(next_pa_id + 1)
    unit.properties[base.ProgAssignment.PA_ID_KEY] = test_case_id


def import_assignment(src_course, src_unit, dst_course, dst_unit):
     create_assignment(dst_course, dst_unit)
     content = base.ProgAssignment.get_content(src_course, src_unit)
     base.ProgAssignment.set_content(dst_course, dst_unit, content)
