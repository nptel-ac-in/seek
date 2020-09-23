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

"""Utility to enable oauth2 settings for NPTEL."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import logging
import os
import re
import sys

import httplib2

from models import config
from apiclient import errors as http_errors
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials

# In real life we'd check in a blank file and set up the code to error with a
# message pointing people to https://code.google.com/apis/console.
_SERVICE_SECRETS_PATH = os.path.join(
    os.path.dirname(__file__), 'service_secret.pem')

_OAUTH_USER = '539841117281-gpbgjooiikjrn9kbkrl79aatjsu1i6ms@developer.gserviceaccount.com'
_SUB_USER = 'onlinecourses@nptel.iitm.ac.in'
_SCOPE = 'https://www.googleapis.com/auth/admin.directory.group'
_DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive'
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]+$")

service = None
http = None
drive_service = None
drive_http = None

# In real life we'd want to make one decorator per service because we wouldn't
# want users to have to give so many permissions.
def InitializeCredentials():
    """Builds a decorator for using oauth2 with webapp2.RequestHandlers."""
    try:
        global service
        global drive_service
        global http
        global drive_http
        # Load the key in PKCS 12 format that you downloaded from the Google API
        # Console when you created your Service account.
        f = file(_SERVICE_SECRETS_PATH, 'rb')
        key = f.read()
        f.close()
        from oauth2client.client import SignedJwtAssertionCredentials
        credentials = SignedJwtAssertionCredentials(
            _OAUTH_USER, key, scope=[_SCOPE, _DRIVE_SCOPE], sub=_SUB_USER)
        http = httplib2.Http()
        http = credentials.authorize(http)
        service = build("admin", "directory_v1", http=http)

        drive_http = httplib2.Http()
        drive_http = credentials.authorize(drive_http)
        drive_service = build("drive", "v2", http=drive_http)


    # Deliberately catch everything. pylint: disable-msg=broad-except
    except Exception as e:
        logging.error('oauth2 module enabled, but unable to load secretes file %s' % e)


def is_drive_folder_accessible(folder_id, errors):
    if not folder_id.strip():
        errors.append('Drive folder id is empty')
        return False

    global drive_service
    drive = drive_service.files()
    try:
        f = drive.get(fileId=folder_id).execute()

        if 'application/vnd.google-apps.folder' != f['mimeType']:
            errors.append(folder_id + ' is not a valid drive folder')
            return False
        return True
    except http_errors.HttpError, error:
        errors.append(str(error))
        return False
