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

"""Utility to add youtube video watchtime records."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import json
import logging

from controllers.utils import BaseHandler
from controllers.utils import ReflectiveRequestHandler
from models import models
from models import transforms

from google.appengine.ext import db


class RecordWatchTime(BaseHandler, ReflectiveRequestHandler):
    default_action = ''
    post_actions = ['record_video_watchtime']
    PROPERTY_NAME = 'video_watch_time'
    KEY_NAME_DURATION = 'duration'
    KEY_NAME_WATCHED = 'watched'

    def merge_times(self, time_tuples):
        sorted_tuples = sorted(time_tuples, key=lambda x: x[0])
        merged_time_stamps = []
        s = None
        e = None
        for start_val, end_val in sorted_tuples:
            if s is not None and e is not None and (start_val - e > 1):
                merged_time_stamps.append((s, e))
                s = start_val
            if s is None:
                s = start_val
            if end_val > e:
                e = end_val
        if s is not None and e is not None:
            merged_time_stamps.append((s, e))
        return merged_time_stamps

    @db.transactional()
    def update_watchtime(self, student, resource_id, merged_time_tuples, duration):
        entity = models.StudentPropertyEntity.get(student, self.PROPERTY_NAME)
        if entity:
            value_dict = transforms.loads(entity.value)
        else:
            entity = models.StudentPropertyEntity.create(student, self.PROPERTY_NAME)
            value_dict = dict()
        value = []
        if resource_id in value_dict:
            if self.KEY_NAME_WATCHED in value_dict[resource_id]:
                value = value_dict[resource_id][self.KEY_NAME_WATCHED]
        final_value = self.merge_times(value + merged_time_tuples)
        value_dict[resource_id] = dict()
        try:
            value_dict[resource_id][self.KEY_NAME_DURATION] = int(
                float(duration))
        except ValueError:
            logging.error('Failed to save duration: %s', duration)
            pass
        value_dict[resource_id][self.KEY_NAME_WATCHED] = final_value
        if merged_time_tuples:
            entity.value = transforms.dumps(value_dict)
            entity.put()

    def post_record_video_watchtime(self):
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return
        user_id = str(student.user_id)
        resource_id = self.request.get('resource_id')
        if not resource_id:
            return
        start = self.request.get_all('start[]')
        end = self.request.get_all('end[]')
        duration = self.request.get('duration')

        merged_time_tuples = []
        for i, start_val in enumerate(start):
            if len(end) > i:
                end_val = end[i]
                merged_time_tuples.append((int(start_val), int(end_val)))
        self.update_watchtime(student, resource_id, merged_time_tuples, duration)
