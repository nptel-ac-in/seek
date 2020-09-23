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
# author: psimakov@google.com (Pavel Simakov)

#
# This script starts local developer Google AppEngine server and initializes it
# with the default data set.
#
# Run this script from the coursebuilder/ folder:
#     sh ./scripts/start.sh
#

usage () { echo "Options: -f don't clear datastore; -h show this message"; }

CLEAR_DATASTORE='true'
while getopts fh option
do
    case $option
    in
        f)  CLEAR_DATASTORE='false';;
        h)  usage; exit 0;;
        *)  usage; exit 1;;
    esac
done

# Force shell to fail on any errors.
set -e


. "$(dirname "$0")/common.sh"

echo "Starting GAE development server in a new shell"
cmd="python $GOOGLE_APP_ENGINE_HOME/dev_appserver.py \
    --host=0.0.0.0 --port=8080 \
    --clear_datastore=$CLEAR_DATASTORE \
    --datastore_consistency_policy=consistent \
    --max_module_instances=1 \
    --skip_sdk_update_check='true' \
    \"$SOURCE_DIR\""

if [[ $OSTYPE == linux* ]] ; then
  /usr/bin/xterm -e "$cmd" &
elif [[ $OSTYPE == darwin* ]] ; then
  run_script=$( mktemp /tmp/XXXXXXXX )
  echo "$cmd" > $run_script
  chmod 755 $run_script
  open -a Terminal.app $run_script
else
  echo "TODO: Support non-linux launch of CourseBuilder from new terminal"
  exit 1
fi

echo Waiting for server startup
sleep 10

echo "Opening browser windows pointing to an end user and an admin interface"
if [[ $OSTYPE == linux* ]] ; then
  /opt/google/chrome/chrome http://localhost:8080/ &
  /opt/google/chrome/chrome http://localhost:8000/ &
elif [[ $OSTYPE == darwin* ]] ; then
  open -a "Google Chrome".app http://localhost:8080/
  open -a "Google Chrome".app http://localhost:8000/
else
  echo "TODO: Support non-linux launch of CourseBuilder from new terminal"
  exit 1
fi

echo Done!
