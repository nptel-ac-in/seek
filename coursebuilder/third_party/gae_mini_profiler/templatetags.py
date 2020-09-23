# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

import profiler


def profiler_includes_request_id(request_id, show_immediately=False):
    if not request_id:
        return ""

    js_path = "/gae_mini_profiler/static/js/profiler.js"
    css_path = "/gae_mini_profiler/static/css/profiler.css"

    return """
<link rel="stylesheet" type="text/css" href="%s" />
<script type="text/javascript" src="%s"></script>
<script type="text/javascript">GaeMiniProfiler.init("%s", %s)</script>
    """ % (css_path, js_path, request_id, json.dumps(show_immediately))


def profiler_includes():
    return profiler_includes_request_id(profiler.CurrentRequestId.get())
