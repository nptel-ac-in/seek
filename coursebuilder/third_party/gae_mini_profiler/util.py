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

import os

# Assume if SERVER_SOFTWARE is not present in the environment at import time
# that we are in some kind of testing or development environment.
dev_server = os.environ.get("SERVER_SOFTWARE", "Devel").startswith("Devel")

def seconds_fmt(f, n=0):
    return milliseconds_fmt(f * 1000, n)

def milliseconds_fmt(f, n=0):
    return decimal_fmt(f, n)

def decimal_fmt(f, n=0):
    format = "%." + str(n) + "f"
    return format % f

def short_method_fmt(s):
    return s[s.rfind("/") + 1:]

def short_rpc_file_fmt(s):
    if not s:
        return ""
    return s[s.find("/"):]
