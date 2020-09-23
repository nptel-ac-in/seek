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
# Wrapper script for modules.py that sets up paths correctly. Usage from your
# coursebuilder/ folder:
#
#   sh scripts/modules.sh [args]

set -e

. "$(dirname "$0")/common.sh"


python "$COURSEBUILDER_HOME/scripts/modules.py" "$@"
