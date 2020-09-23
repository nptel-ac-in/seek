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

"""Base class for scoring module."""

__author__ = 'Thejesh GN (tgn@google.com)'


class ScoringBase(object):
    NAME = 'Reevaluate'
    DASHBOARD_NAV = 'reevaluate'
    DASHBOARD_RESCORING_TAB = 'rescore'
    RESCORE_OBJ_ASSESSMENT_ACTION = 'rescore_obj_assessment_scoring'
    RESCORE_OBJ_ASSESSMENT_CONFIRMED_ACTION = 'rescore_obj_assessment_scoring_confirmed'

    @classmethod
    def _get_content(cls, course, filename):
        """Returns programming assignment content."""
        content = course.get_file_content(filename)
        return transforms.loads(content) if content else dict()

    @classmethod
    def get_content(cls, course, unit):
        """Returns programming assignment content."""
        filename = cls.get_content_filename(unit)
        return cls._get_content(course, filename)