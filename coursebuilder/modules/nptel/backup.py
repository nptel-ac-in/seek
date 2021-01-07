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

__author__ = 'Rishav Thakker (rthakker@google.com)'

import logging

from controllers import sites
from controllers import utils
from models import courses
from google.appengine.api import namespace_manager
from google.appengine.api import taskqueue
import json
import copy
from urllib import urlencode
import appengine_config


DUMP_URL = "/_ah/datastore_admin/backup.create"

COURSE_NAMESPACES_STUDENT_ENTITIES = [
    'FileDataEntity',
    'FileMetadataEntity',
    'ProgrammingAnswersEntity',
    'ProgrammingTestCasesEntity',
    'QuestionAnswersEntity',
    'SavedProgrammingCodeEntity',
    'Student',
    'StudentAnswersEntity',
    'StudentPreferencesEntity',
    'StudentPropertyEntity',
    'Submission'
]

DEFAULT_NAMESPACE_STUDENT_ENTITIES = [
    'PersonalProfile',
] + COURSE_NAMESPACES_STUDENT_ENTITIES

COURSE_NAMESPACES_ENTITIES = [
    'ClusterEntity',
    'ConfigPropertyEntity',
    'EventEntity',
    'Notification',
    'Payload',
    'LabelEntity',
    'AnnouncementEntity',
    'DurableJobEntity',
    'CourseStaff',
    'ManualEvaluationStep',
    'ManualEvaluationSummary',
    'MenteeData',
    'QuestionEntity',
    'QuestionGroupEntity',
    'Review',
    'ReviewStep',
    'ReviewSummary',
    'RoleEntity',
    'StudentEnrollmentEventEntity',
    'StudentFormEntity',
    'StudentQuestionEntity',
    'SubscriptionStateEntity',
] + COURSE_NAMESPACES_STUDENT_ENTITIES

DEFAULT_NAMESPACE_ENTITIES = [
    'CourseCategory',
    'CourseList',
    'ExplorerLayout',
] + DEFAULT_NAMESPACE_STUDENT_ENTITIES + COURSE_NAMESPACES_STUDENT_ENTITIES

URL_PARAMS = {
    'filesystem': 'gs',
    'gs_bucket_name': 'nptelmoocdatadump',
    'namespace': '{namespace}',
    'name': '{name}',
}

FULL_BACKUP_NAME = 'FullBackup'
STUDENT_BACKUP_NAME = 'StudentDataBackup'

class BackupScheduler(object):
    """Class for running backups"""

    def __init__(self, url, params):
        self.url = url
        self.params = params

    def queue_backup_job(self, urlencode_doseq=True):
        encoded_params = urlencode(self.params, doseq=urlencode_doseq)
        url = '%s?%s' % (self.url, encoded_params)
        taskqueue.add(
            url=url,
            target='ah-builtin-python-bundle',
            method='GET',
            queue_name='daily-backup'
        )

class OpenCoursesBackupHandler(utils.BaseHandler, utils.ReflectiveRequestHandler):
    """Triggers datastore backups for open courses."""

    STUDENT_BACKUP_GET_ACTION = 'student_backup'
    FULL_BACKUP_GET_ACTION = 'full_backup'
    default_action = FULL_BACKUP_GET_ACTION
    get_actions = [FULL_BACKUP_GET_ACTION, STUDENT_BACKUP_GET_ACTION]

    @classmethod
    def perform_backup(cls, default_namespace_entities,
                       course_namespace_entities, backup_name):
        open_courses = sites.get_all_courses(include_closed=False)

        response = {
            'entites': {
                'default_namespace': default_namespace_entities,
                'course_namespaces': course_namespace_entities
            },
            'result': {}
        }
        urls = []

        # Make local copies to make this code thread safe
        dump_url = copy.deepcopy(DUMP_URL)
        url_params = copy.deepcopy(URL_PARAMS)
        url_params['name'] = FULL_BACKUP_NAME

        # Queue a job for the default namespace
        namespace = appengine_config.DEFAULT_NAMESPACE_NAME
        url_params['namespace'] = namespace
        url_params['kind'] = default_namespace_entities
        scheduler = BackupScheduler(dump_url, url_params)
        scheduler.queue_backup_job()
        response['result']['DEFAULT_NAMESPACE'] = 'added_to_queue'

        # Queue a job each for the course namespaces
        url_params['kind'] = course_namespace_entities
        for course in open_courses:
            namespace = course.namespace
            url_params['namespace'] = namespace
            scheduler = BackupScheduler(dump_url, url_params)
            scheduler.queue_backup_job()
            response['result'][namespace] = 'added to queue'

        return response


    def get_full_backup(self):
        """Runs the full backup operation once for open courses."""
        self.response.headers['Content-Type'] = 'text/plain'
        responses = self.perform_backup(
            default_namespace_entities=DEFAULT_NAMESPACE_ENTITIES,
            course_namespace_entities=COURSE_NAMESPACES_ENTITIES,
            backup_name=FULL_BACKUP_NAME
        )
        self.response.write(json.dumps(responses, indent=4))

    def get_student_backup(self):
        """
        Runs the backup operation for Student submitted objects once for open
        courses.
        """
        self.response.headers['Content-Type'] = 'text/plain'
        responses = self.perform_backup(
            default_namespace_entities=DEFAULT_NAMESPACE_STUDENT_ENTITIES,
            course_namespace_entities=COURSE_NAMESPACES_STUDENT_ENTITIES,
            backup_name=STUDENT_BACKUP_NAME
        )
        self.response.write(json.dumps(responses, indent=4))
