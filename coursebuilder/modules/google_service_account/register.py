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

"""Methods to register Service Account module."""

__author__ = 'Rishav Thakker (rthakker@google.com)'

from models import custom_modules
from modules.dashboard import dashboard
from modules.google_service_account import base
from modules.google_service_account import settings
from modules.google_service_account import google_service_account

# Module registration
custom_module = None

def register_module():
    """Registers this module in the registry"""
    global_routes = [
        (
            settings.GoogleServiceAccountRESTHandler.URI,
            settings.GoogleServiceAccountRESTHandler
        ),
    ]

    global custom_module
    custom_module = custom_modules.Module(
        base.GoogleServiceAccountBase.NAME,
        base.GoogleServiceAccountBase.DESCRIPTION,
        global_routes, [])

    # Initialize the module
    google_service_account.GoogleServiceManager.initialize_credentials()

    return custom_module
