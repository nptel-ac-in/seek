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

# Copyright 2012 Google Inc. All Rights Reserved.
#
# author: sll@google.com (Sean Lip)

# Run this script from the Course Builder folder as follows:
#     sh ./scripts/test.sh --test_class <dotted test name>
# E.g.,
#   Run all tests in a module:
#     sh ./scripts/test.sh tests.unit.common_safe_dom
#
#   Run all tests in a class:
#     sh ./scripts/test.sh tests.unit.common_safe_dom.EntityTests
#
#   Run a single test method:
#     sh ./scripts/test.sh tests.unit.common_safe_dom.NodeListTests.test_list
#
# Run this script and measure test coverage as follows:
#     install coverage:
#         pip install coverage
#     modify this script (python > coverage run + coverage report):
#         ...
#         coverage run tests/suite.py
#         coverage report
#         ...
#     run the script from coursebuilder/:
#         sh scripts/test.sh
#

usage () {
  echo
  echo "Usage: $0 <dotted_test_name>"
  echo "E.g.,"
  echo "  $0 tests.unit.common_safe_dom"
  echo
  echo
  echo "To set up tab completion for test names within bash, add the following"
  echo "command to your .bashrc file:"
  echo "export complete -o nospace -C scripts/test_completions.py test.sh"
  echo
}

# Force shell to fail on any errors.
set -e

if [ -z $1 ]; then
  usage
  exit 1
fi

# Reinstall AE runtime environment and CB-distributed libs if necessary.
. "$(dirname "$0")/common.sh"

export PYTHONPATH=\
$SOURCE_DIR:\
$GOOGLE_APP_ENGINE_HOME:\
$JINJA_PATH:\
$WEBAPP_PATH:\
$WEBOB_PATH:\
$BEAUTIFULSOUP_PATH:\
$SELENIUM_PATH:\
$YAML_PATH:\
$SIX_PATH:\
$WEBTEST_PATH
export PHANTOMJS_BIN=$RUNTIME_HOME/phantomjs/bin/phantomjs

CB_SERVER_START=$SCRIPTS_DIR/start_in_shell.sh

echo Running functional tests
python "$SOURCE_DIR/tests/suite.py" \
  --integration_server_start_cmd="$CB_SERVER_START" \
  --test_class_name $1

echo Done!
