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

"""Mapping from schema to backend properties."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

from datetime import datetime
from datetime import tzinfo
from datetime import timedelta

class Zone(tzinfo):
  def __init__(self, offset_hours, offset_minutes, isdst, name):
      self.offset_hours = offset_hours
      self.offset_minutes = offset_minutes
      self.isdst = isdst
      self.name = name

  def utcoffset(self, dt):
      return timedelta(hours=self.offset_hours, minutes=self.offset_minutes) + self.dst(dt)

  def dst(self, dt):
      return timedelta(hours=1) if self.isdst else timedelta(0)

  def tzname(self, dt):
      return self.name


UTC = Zone(0, 0, False, 'UTC')
IST = Zone(5, 30, False, 'IST')

