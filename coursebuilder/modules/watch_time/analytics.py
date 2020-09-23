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

"""Classes and methods to create and manage watch time related analytics dashboard."""

__author__ = 'Thejesh GN (tgn@google.com)'

import ast
import collections
import json

from common import schema_fields
from models import courses
from models import data_sources
from models import jobs
from models import transforms
from models import models

from modules.watch_time import record_watchtime

class WatchTimeStats(jobs.MapReduceJob):
    """A job that computes video watch time stats."""

    @staticmethod
    def get_description():
        return 'Watch time'

    @staticmethod
    def entity_class():
        return models.StudentPropertyEntity

    @staticmethod
    def map(entity):
        data = []
        if entity.name == record_watchtime.RecordWatchTime.PROPERTY_NAME:
            video_timing_details = transforms.loads(entity.value)
            for video_id, timings in video_timing_details.iteritems():
                if not isinstance(timings, dict):
                    continue
                if record_watchtime.RecordWatchTime.KEY_NAME_WATCHED not in timings.keys():
                    continue
                watchtime = timings[record_watchtime.RecordWatchTime.KEY_NAME_WATCHED]
                if not watchtime:
                    continue
                for timing_range in watchtime:
                    for key in range(timing_range[0], timing_range[1]+1):
                        data.append(key)
                yield (str(video_id), data)

    @staticmethod
    def reduce(key, data_list):
        video_timings = {}
        for timings in data_list:
            for time in json.loads(timings):
                if video_timings.has_key(time):
                    video_timings[time] = video_timings[time]+1
                else:
                    video_timings[time] = 1
        yield({'video_id': str(key), 'stats': video_timings })


class WatchTimeStatsDataSource(data_sources.SynchronousQuery):
    @staticmethod
    def required_generators():
        return [WatchTimeStats]

    @classmethod
    def get_name(cls):
        return 'watch_time_stats'

    @classmethod
    def get_title(cls):
        return 'Watch Time'

    @classmethod
    def get_schema(cls, unused_app_context, unused_catch_and_log):
        reg.add_property(schema_fields.SchemaField(
            'watch_time', 'Watch Time', 'dict',
            description=''))
        reg.add_property(schema_fields.SchemaField(
            'stats_calculated', 'Stats Calculated', 'str',
            description=''))
        return reg.get_json_schema_dict()['properties']

    @staticmethod
    def fill_values(app_context, template_values, job):
        """Returns Jinja markup for watch video stats analytics."""
        stats_calculated = False
        stats = []
        video_params = {}
        if job and job.status_code == jobs.STATUS_CODE_COMPLETED:
            o = jobs.MapReduceJob.get_results(job)
            if o:
                course = courses.Course(None, app_context=app_context)
                for lesson in course.get_lessons_for_all_units():
                    if lesson.video and lesson.video != "":
                        video = {}
                        video["title"] = lesson.title
                        video["unit_id"] = lesson.unit_id
                        video["unit_title"] = course.find_unit_by_id(lesson.unit_id).title
                        video_params[lesson.video] = video


                stats   = list(o)
                for video_stat in stats:
                    video_id = video_stat["video_id"]
                    video = video_params[video_id]
                    video_stat['title'] = video['title']
                    video_stat['unit_id'] = video['unit_id']
                    video_stat['unit_title'] = video['unit_title']

                stats_calculated = True
            template_values.update({
                'stats': transforms.dumps(stats),
                'stats_calculated': stats_calculated,
                })
