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

"""Methods to register Watch Time module.."""

__author__ = 'Thejesh GN (tgn@google.com)'


from models import analytics
from models import data_sources
from models import custom_modules
from modules.dashboard import tabs
from modules.watch_time import record_watchtime
from modules.watch_time import analytics as panalytics

MODULE_NAME = 'Watch Time'

# Module registration
custom_module = None

def register_module():
    """Registers this module in the registry."""

    data_sources.Registry.register(
        panalytics.WatchTimeStatsDataSource)

    tab_name = 'watch_time_stats'
    stats = analytics.Visualization(
        tab_name, MODULE_NAME,
        'templates/watch_time_stats.html',
        data_source_classes=[panalytics.WatchTimeStatsDataSource])
    tabs.Registry.register(
        'analytics', tab_name, MODULE_NAME, [stats])

    global_routes = []
    watch_time_routes = [
        ('/modules/watch_time/video_watchtime', record_watchtime.RecordWatchTime),
        ('/modules/nptel/video_watchtime', record_watchtime.RecordWatchTime)
    ]

    global custom_module
    custom_module = custom_modules.Module(
        MODULE_NAME, 'Provides library to register video watch time related assets/code',
        global_routes, watch_time_routes)
    return custom_module
