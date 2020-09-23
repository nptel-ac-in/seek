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

"""Classes and methods to create and manage Programming assignment related cron
jobs and analytics dashboards."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


import ast

from common import schema_fields
from controllers import sites
from controllers.utils import BaseHandler
from models import courses
from models import data_sources
from models import jobs
from models import transforms
from modules.programming_assignments import prog_models
from modules.programming_assignments import base


class ComputeProgrammingStats(jobs.MapReduceJob):
    """A job that computes student programming assignment stats."""

    @staticmethod
    def get_description():
        return 'programming stats earned'

    @staticmethod
    def entity_class():
        return prog_models.ProgrammingTestCasesEntity

    @staticmethod
    def update_stats(test_stats, unit_dict):
        for index, stat in test_stats.items():
            if index not in unit_dict:
                unit_dict[index] = {
                    'passed': 0, 'failed': 0, 'failed_reason': dict()}

            t_dict = unit_dict[index]
            if stat[0]:
                t_dict['passed'] += 1
            else:
                t_dict['failed'] += 1
                if stat[1] not in t_dict['failed_reason']:
                    t_dict['failed_reason'][stat[1]] = 1
                else:
                    t_dict['failed_reason'][stat[1]] += 1

    @staticmethod
    def map(entity):
        name = entity.key().name()
        unit_id = name.split('-')[1]
        data = {'public': dict(), 'private': dict()}

        if entity.public_test_case_data:
            test_stats = transforms.loads(entity.public_test_case_data)
            ComputeProgrammingStats.update_stats(test_stats, data['public'])
        if entity.private_test_case_data:
            test_stats = transforms.loads(entity.private_test_case_data)
            ComputeProgrammingStats.update_stats(test_stats, data['private'])
        yield (str(unit_id), data)

    @staticmethod
    def update_unit_stats(test_case_stats, unit_dict):
        for index, data in test_case_stats.items():
            if index not in unit_dict:
                unit_dict[index] = {
                    'passed': 0, 'failed': 0, 'failed_reason': dict()}
            t_dict = unit_dict[index]
            t_dict['passed'] += data['passed']
            t_dict['failed'] += data['failed']
            for reason, count in data['failed_reason'].items():
                if reason not in t_dict['failed_reason']:
                    t_dict['failed_reason'][reason] = 0
                t_dict['failed_reason'][reason] += count

    @staticmethod
    def reduce(key, data_list):
        unit_id = int(key)
        unit_dict = {'public': dict(), 'private': dict()}

        for packed_data in data_list:
            data = ast.literal_eval(packed_data)
            ComputeProgrammingStats.update_unit_stats(
                data['public'], unit_dict['public'])
            ComputeProgrammingStats.update_unit_stats(
                data['private'], unit_dict['private'])

        yield({'unit_id': str(unit_id), 'stats': unit_dict})


class ProgrammingStatsDataSource(data_sources.SynchronousQuery):
    @staticmethod
    def required_generators():
        return [ComputeProgrammingStats]

    @classmethod
    def get_name(cls):
        return 'programming_assignment_stats'

    @classmethod
    def get_title(cls):
        return 'Programming Assignments'

    @classmethod
    def get_schema(cls, unused_app_context, unused_catch_and_log):
        reg = schema_fields.FieldRegistry(
            'Programming Assignments Stats',
            description='')
        reg.add_property(schema_fields.SchemaField(
            'test_stats', 'Test Stats', 'str',
            description=''))
        reg.add_property(schema_fields.SchemaField(
            'unit_title', 'Unit Title', 'str',
            description=''))
        reg.add_property(schema_fields.SchemaField(
            'stats_calculated', 'Stats Calculated', 'str',
            description=''))
        return reg.get_json_schema_dict()['properties']

    @staticmethod
    def fill_values(app_context, template_values, job):
        """Returns Jinja markup for question stats analytics."""
        stats_calculated = False
        stats = None
        course = courses.Course(None, app_context=app_context)
        unit_id_to_title = dict()
        for unit in course.get_units():
            if not unit.is_custom_unit():
                continue
            if unit.custom_unit_type != base.ProgAssignment.UNIT_TYPE_ID:
                continue
            unit_id_to_title[str(unit.unit_id)] = '%s (%d)' % (
                unit.title, unit.unit_id)

        def ordering(a1, a2):
            return cmp(a1['unit_id'], a2['unit_id'])

        if job and job.status_code == jobs.STATUS_CODE_COMPLETED:
            o = jobs.MapReduceJob.get_results(job)
            if o:
                stats = list(o)
                stats.sort(ordering)
                stats_calculated = True
        template_values.update({
            'test_stats': transforms.dumps(stats),
            'unit_title': transforms.dumps(unit_id_to_title),
            'stats_calculated': stats_calculated,
            })


class ComputeProgrammingStatsHandler(BaseHandler):
    """Iterates through each course and run job to calcalute average score for
    each unit."""

    def get(self):
        namespaces = self.request.get_all('namespace')
        for context in sites.get_all_courses():
            if (namespaces and len(namespaces) > 0 and
                context.get_namespace_name() not in namespaces):
                continue
            job = ComputeProgrammingStats(context)
            job.submit()
        self.response.write('OK\n')
