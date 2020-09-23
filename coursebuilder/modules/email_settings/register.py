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

"""Methods to support email settings."""

__author__ = 'Thejesh GN (tgn@google.com)'

from controllers import sites
from controllers.utils import BaseHandler
from controllers.utils import ReflectiveRequestHandler
from controllers.utils import XsrfTokenManager
from models import custom_modules
from models import transforms
from models.models import Student
from modules.dashboard import dashboard
from modules.email_settings import base
from modules.email_settings import email_settings
from modules.dashboard import tabs
from models.config import ConfigProperty
from models.config import ConfigPropertyEntity
# Module registration
custom_module = None



def register_module():
    """Registers this module in the registry."""

    global_routes = [
        (email_settings.EmailSettingsRESTHandler.URI, email_settings.EmailSettingsRESTHandler),
        (email_settings.AddNewEmailSettingsRESTHandler.URI, email_settings.AddNewEmailSettingsRESTHandler),
        (email_settings.AddNewQueueSettingsRESTHandler.URI, email_settings.AddNewQueueSettingsRESTHandler),
        (email_settings.QueueSettingsRESTHandler.URI, email_settings.QueueSettingsRESTHandler),
    ]

    global custom_module
    custom_module = custom_modules.Module(
        base.EmailSettingsBase.NAME,
        'Provides External Email support',
        global_routes,  [])
    return custom_module
