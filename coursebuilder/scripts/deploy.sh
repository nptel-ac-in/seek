#!/bin/bash

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

# Copyright 2014 Google Inc. All Rights Reserved.
#
# Usage:
#
# Run this script from the Course Builder folder. It can be run with the
# following arguments:
#
# Deploy Course Builder to the App Engine app named in app.yaml:
#     sh ./scripts/deploy.sh
#
# Deploy Course Builder to the given App Engine app:
#     sh ./scripts/deploy.sh my_app_name
#
# Deploy Course Builder with optional arguments passed to appcfg.py:
#     sh ./scripts/deploy.sh <optional_args>
# E.g.,
#   Authenticate on App Engine with OAuth2:
#     sh ./scripts/deploy.sh --oauth2
# See the documentation for appcfg.py for more details:
#   https://developers.google.com/appengine/docs/python/tools/uploadinganapp

set -e

. "$(dirname "$0")/common.sh"

if [[ $# == 1 && $1 != -* ]]; then
  application="--application=$1"
  shift
fi

python "$GOOGLE_APP_ENGINE_HOME/appcfg.py" \
  $application \
  "$@" update \
  "$SOURCE_DIR"
