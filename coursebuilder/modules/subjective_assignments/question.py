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

"""Classes and methods to creating subjective assignment."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import cgi
import urllib
from google.appengine.api import namespace_manager
# from common import safe_dom
from common import tags
from common import utils
from common.schema_fields import FieldRegistry
from common.schema_fields import SchemaField
from controllers.utils import BaseRESTHandler
from controllers.utils import XsrfTokenManager
from models import courses
from models import roles
from models import transforms
from models import course_list
from models import vfs
from modules.subjective_assignments import drive_service
from modules.oeditor import oeditor
from models import messages
from tools import verify

import yaml


DRAFT_TEXT = 'Private'
PUBLISHED_TEXT = 'Public'
ESSAY_TEXT = "Essay"
BLOB_TEXT = "Drive Link"
STATUS_ANNOTATION = oeditor.create_bool_select_annotation(
    ['properties', 'is_draft'], 'Status', DRAFT_TEXT,
    PUBLISHED_TEXT, class_name='split-from-main-group')


def workflow_key(key):
    return 'workflow:%s' % key


def content_key(key):
    return 'content:%s' % key


def blob_key(key):
    return content_key('blob:%s' % key)


class SubjectiveAssignmentBaseHandler(object):
    UNIT_TYPE_ID = 'in.ac.nptel.onlinecourses.subjective'
    UNIT_URL = '/subjective'
    NAME = 'Subjective Assignment'
    DESCRIPTION = 'Subjective Assignments'
    OPT_QUESTION_TYPE = "type"
    ESSAY = 'essay'
    BLOB = 'blob'
    OPT_DRIVE_DIR_ID = "drive_folder"
    OPT_MAX_FILE_LIMIT = "max_file_limit"
    OPT_NUM_REVIEWERS = "num_reviewers"
    OPT_SCORING_METHOD = "scoring_method"

    @classmethod
    def get_content_filename(cls, unit):
        assert unit
        assert unit.custom_unit_type == cls.UNIT_TYPE_ID
        return 'essay/question-%s.js' % unit.unit_id

    @classmethod
    def get_content(cls, course, unit):
        """Returns programming assignment content."""
        filename = cls.get_content_filename(unit)
        content = course.get_file_content(filename)
        return transforms.loads(content) if content else dict()

    @classmethod
    def set_content(cls, course, unit, content):
        filename = cls.get_content_filename(unit)
        course.set_file_content(
            filename, vfs.string_to_stream(unicode(transforms.dumps(content))))

    @classmethod
    def delete_file(cls, course, unit):
        filename = cls.get_content_filename(unit)
        return course.delete_file(filename)

    @classmethod
    def get_public_url(cls, unit):
        args = {}
        args['name'] = unit.unit_id
        return '%s?%s' % (cls.UNIT_URL, urllib.urlencode(args))


def create_assignment_registry():
    """Create the registry for course properties."""

    reg = FieldRegistry(
        'Subjective Assignment Entity',
        description=SubjectiveAssignmentBaseHandler.DESCRIPTION)

    # Course level settings.
    reg.add_property(SchemaField(
        'key', 'ID', 'string', editable=False,
        extra_schema_dict_values={'className': 'inputEx-Field keyHolder'}))
    reg.add_property(
        SchemaField('type', 'Type', 'string', editable=False))
    reg.add_property(
        SchemaField('title', 'Title', 'string', optional=False))
    reg.add_property(
        SchemaField('weight', 'Weight', 'number', optional=False))
    reg.add_property(SchemaField('parent_unit', 'Parent Unit', 'string', editable=False, select_data=[]))
    reg.add_property(SchemaField(
        content_key(SubjectiveAssignmentBaseHandler.OPT_QUESTION_TYPE),
        'Assignment Type', 'string',
        select_data=[(SubjectiveAssignmentBaseHandler.ESSAY, ESSAY_TEXT),
                     (SubjectiveAssignmentBaseHandler.BLOB, BLOB_TEXT)]))

    reg.add_property(SchemaField(
        content_key('question'), 'Problem Statement', 'html', optional=False,
        description=('Problem Statement and description of program, visible' +
                     ' to student.'),
        extra_schema_dict_values={
            'supportCustomTags': tags.CAN_USE_DYNAMIC_TAGS.value,
            'className': 'inputEx-Field content'}))

    reg.add_property(
        SchemaField(workflow_key(courses.SUBMISSION_DUE_DATE_KEY),
                    'Submission Due Date', 'datetime', optional=False,
                    description=messages.ASSESSMENT_DUE_DATE_FORMAT_DESCRIPTION,
                    extra_schema_dict_values={'_type': 'datetime'}))
    reg.add_property(
        SchemaField(workflow_key(courses.SUBMIT_ONLY_ONCE),
                    'Number of Submissions', 'boolean',
                    select_data=[(False, 'Allow Multiple Submissions'), (True, 'Submit Only Once') ]))

    manual_review_reg = reg.add_sub_registry('manual_review_reg', 'Options for Manual Review')
    manual_review_reg.add_property(
        SchemaField(content_key(SubjectiveAssignmentBaseHandler.OPT_NUM_REVIEWERS),
                    'Number of reviewers', 'integer', optional=False,
                    description='Number of course staff that will review each submission',
                    extra_schema_dict_values={'value': 1}))

    manual_review_reg.add_property(
        SchemaField(content_key(SubjectiveAssignmentBaseHandler.OPT_SCORING_METHOD),
                    'Scoring method', 'string', optional=False,
                    select_data=[('average', 'Average of all scores'),
                                 ('min', 'Minimum of all scores'),
                                 ('max', 'Maximum of all scores')],
                    description='Method to evaluate a final score for each submission',
                    extra_schema_dict_values={'value': 'average'}))

    drive_reg = reg.add_sub_registry('drive_reg', 'Options For ' + BLOB_TEXT + ' Assignment')
    drive_reg.add_property(
        SchemaField(blob_key(SubjectiveAssignmentBaseHandler.OPT_DRIVE_DIR_ID),
                    'Google Drive Folder Id', 'string', optional=True,
                    description="""Id of Google Drive folder where all
                    assignments will be stored. Please use a different id for
                    each assignment"""))
    drive_reg.add_property(
        SchemaField(blob_key(SubjectiveAssignmentBaseHandler.OPT_MAX_FILE_LIMIT),
                    'Maximum number of files in a submission', 'integer', optional=True,
                    description="""Maximum number of files allowed in a single
                    submission""", extra_schema_dict_values={'value': 1}))

    reg.add_property(
        SchemaField('is_draft', 'Status', 'boolean',
                    select_data=[(True, DRAFT_TEXT), (False, PUBLISHED_TEXT)],
                    extra_schema_dict_values={
                        'className': 'split-from-main-group'}))
    return reg

class CourseOutlineRights(object):
    """Manages view/edit rights for course outline."""

    @classmethod
    def can_view(cls, handler):
        return cls.can_edit(handler)

    @classmethod
    def can_edit(cls, handler):
        return roles.Roles.is_course_admin(handler.app_context)

    @classmethod
    def can_delete(cls, handler):
        return cls.can_edit(handler)

    @classmethod
    def can_add(cls, handler):
        return cls.can_edit(handler)



class SubjectiveAssignmentRESTHandler(BaseRESTHandler, SubjectiveAssignmentBaseHandler):
    """Provides REST API to prog assignment."""

    URI = '/rest/course/essay'

    REG = create_assignment_registry()

    SCHEMA_JSON = REG.get_json_schema()

    SCHEMA_DICT = REG.get_json_schema_dict()

    REQUIRED_MODULES = [
        'gcb-rte', 'inputex-select', 'inputex-string', 'inputex-textarea',
        'inputex-uneditable', 'inputex-integer', 'inputex-hidden',
        'inputex-checkbox', 'inputex-list', 'inputex-number']

    @classmethod
    def get_schema(cls, course):
        unit_list = []
        for unit in course.get_units():
            if unit.type == 'U':
                unit_list.append(
                    (unit.unit_id,
                     cgi.escape('Unit %s - %s' % (unit.index, unit.title))))
        extra_select_options = dict()
        extra_select_options['parent_unit'] = unit_list
        cls.REG.get_schema_dict(
            extra_select_options=extra_select_options)
        return cls.REG



    def unit_to_dict(self, course, unit):
        """Assemble a dict with the unit data fields."""
        assert verify.UNIT_TYPE_CUSTOM == unit.type
        assert self.UNIT_TYPE_ID == unit.custom_unit_type

        content = self.get_content(course, unit)

        workflow = unit.workflow

        if workflow.get_submission_due_date():
            submission_due_date = workflow.get_submission_due_date()
        else:
            submission_due_date = None

        workflow_dict = dict()
        workflow_dict[courses.SUBMISSION_DUE_DATE_KEY] = submission_due_date
        workflow_dict[courses.GRADER_KEY] = workflow.get_grader()
        workflow_dict[courses.SUBMIT_ONLY_ONCE] = workflow.submit_only_once()

        entity = {
                'key': unit.unit_id,
                'type': self.UNIT_TYPE_ID,
                'title': unit.title,
                'weight': str(unit.weight if hasattr(unit, 'weight') else 0),
                'parent_unit': unit.parent_unit if unit.parent_unit else 0,
                'is_draft': not unit.now_available,
                'workflow' : workflow_dict,
                'content': content,
                }
        json_entity = dict()
        self.REG.convert_entity_to_json_entity(entity, json_entity)
        return json_entity

    @classmethod
    def validate_drive_folder(cls, content_dict, errors):
        blob_dict = content_dict[cls.BLOB]
        drive_folder_id = blob_dict[cls.OPT_DRIVE_DIR_ID]
        if not drive_folder_id:
            errors.append('Google Drive Folder Id is required for' +
                          BLOB_TEXT + ' assignment')
            return
        if not drive_service.DriveManager.is_drive_folder_accessible(
            drive_folder_id, errors):
            return

    @classmethod
    def share_with_course_admins(cls, content_dict, errors):
        blob_dict = content_dict[cls.BLOB]
        drive_folder_id = blob_dict[cls.OPT_DRIVE_DIR_ID]
        namespace = namespace_manager.get_namespace()
        cl = course_list.CourseListDAO.get_course_for_namespace(namespace)
        course_admin_emails = cl.course_admin_email

        for email in course_admin_emails:
            email = email.strip()
            permission_body = {
                'role': 'reader',
                'type': 'user',
                'value': email
            }
            if not drive_service.DriveManager.share_drive_file(
                    drive_folder_id, permission_body, errors):
                errors.append('Could not share drive folder with ' + email)

    def apply_updates(self, course, unit, updated_unit_dict, errors):
        """Store the updated prog assignment."""

        entity_dict = {}
        self.REG.convert_json_to_entity(
            updated_unit_dict, entity_dict)
        unit.title = entity_dict.get('title')
        unit.parent_unit = int(entity_dict.get('parent_unit'))
        if unit.parent_unit < 1:
            unit.parent_unit = None
        try:
            unit.weight = int(entity_dict.get('weight'))
            if unit.weight < 0:
                errors.append('The weight must be a non-negative integer.')
        except ValueError:
            errors.append('The weight must be an integer.')

        unit.now_available = not entity_dict.get('is_draft')

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
        if  (self.BLOB == content_dict[self.OPT_QUESTION_TYPE]):
            # self.validate_drive_folder(content_dict, errors)
            self.share_with_course_admins(content_dict, errors)

        if not errors:
            self.set_content(course, unit, content_dict)

    def get(self):
        """A GET REST method shared by all unit types."""
        key = self.request.get('key')

        if not CourseOutlineRights.can_view(self):
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

        if not CourseOutlineRights.can_edit(self):
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
            transforms.loads(payload), self.SCHEMA_DICT)

        errors = []
        self.apply_updates(course, unit, updated_unit_dict, errors)
        if not errors:
            assert course.update_unit(unit)
            course.save()
            transforms.send_json_response(self, 200, 'Saved.')
        else:
            transforms.send_json_response(self, 412, '\n'.join(errors))

    def delete(self):
        """Handles REST DELETE verb with JSON payload."""
        key = self.request.get('key')

        if not self.assert_xsrf_token_or_fail(
                self.request, 'delete-unit', {'key': key}):
            return

        if not CourseOutlineRights.can_delete(self):
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
