# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Classes and methods to for Google Drive related stuff."""

__author__ = [
    'Abhinav Khandelwal (abhinavk@google.com)',
    'Rishav Thakker (rthakker@google.com)'
]

import logging
import httplib2
from apiclient import errors as http_errors
from apiclient.discovery import build

from modules.google_service_account import google_service_account


class DriveManager(object):
    """Wrapper to handle drive related operations"""

    REQUIRED_SCOPES = [
        'https://www.googleapis.com/auth/drive'
    ]

    @classmethod
    def get_drive_service(cls):
        """Returns the drive service"""
        return (google_service_account.
                GoogleServiceManager.
                get_service('drive', 'v2'))

    @classmethod
    def is_drive_file_accessible(cls, file_id, errors):
        """Checks if a drive file is accessible"""

        if not file_id.strip():
            errors.append('Drive id is empty')
            return False

        drive_service = cls.get_drive_service()
        if not drive_service:
            errors.append('Drive service not defined')
            return False
        drive = drive_service.files()
        try:
            f = drive.get(fileId=file_id).execute()
            return True
        except http_errors.HttpError, error:
            errors.append(str(error))
            return False

    @classmethod
    def is_drive_folder_accessible(cls, folder_id, errors):
        if not folder_id.strip():
            errors.append('Drive folder id is empty')
            return False

        drive_service = cls.get_drive_service()
        if not drive_service:
            errors.append('Drive service not defined')
            return False
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

    @classmethod
    def get_drive_folder_by_name(cls, parent_folder_id, folder_name, errors):
        """Gets the details of a drive folder by searching via name"""
        if not folder_name.strip():
            errors.append('Folder name is empty')
            return

        try:
            drive_service = cls.get_drive_service()
            if not drive_service:
                errors.append('Drive service not defined')
                return
            children_response = (drive_service.children()
                .list(q="title='%s'" % folder_name,
                      folderId=parent_folder_id,
                      fields='items(id)')
                .execute())
            if not children_response['items']:
                errors.append('Folder not found')
                return
            return children_response['items'][0]
        except http_errors.HttpError, error:
            errors.append(str(error))
            return

    @classmethod
    def share_drive_file(cls, file_id, permission_body, errors):
        """
        Shares a drive file (or folder) with an email address.
        Does not work recursively for its children.
        """

        try:
            drive_service = cls.get_drive_service()
            if not drive_service:
                errors.append('Drive service not defined')
                return
            share_response = (drive_service.permissions()
                .insert(fileId=file_id, body=permission_body).execute())

            return share_response
        except http_errors.HttpError, error:
            errors.append(str(error))
            return

    @classmethod
    def remove_permission_by_id(cls, file_id, permission_id, errors):
        """
        Removes a permission via its ID.
        Does not work recursively for its children.
        """
        if not permission_id.strip():
            errors.append('Permission ID is empty')

        try:
            drive_service = cls.get_drive_service()
            if not drive_service:
                errors.append('Drive service not defined')
                return
            remove_permission_response = (drive_service.permissions()
                .delete(fileId=file_id, permissionId=permission_id).execute())
        except http_errors.HttpError, error:
            errors.append(str(error))


    @classmethod
    def unshare_drive_file_by_email(cls, file_id, email, errors):
        """
        Revokes any view/edit permissions of a file for an email.
        Does not work recursively for its children.
        """
        if not email.strip():
            errors.append('Email is empty')

        # First get the permission ID for the email address. This does not
        # depend on any other parameters
        permission_id = None
        try:
            drive_service = cls.get_drive_service()
            if not drive_service:
                errors.append('Drive service not defined')
                return
            id_response = drive_service.permissions().getIdForEmail(
                email=email).execute()

            if not (id_response and id_response['id']):
                errors.append('Could not get permission ID for email')
                return

            permission_id = id_response['id']
        except http_errors.HttpError, error:
            errors.append(str(error))

        return cls.remove_permission_by_id(file_id, permission_id, errors)


    @classmethod
    def add_parent_to_folder(cls, folder_id, parent_folder_id, errors):
        """Adds a parent to a folder"""
        if not folder_id.strip():
            errors.append('Folder id is empty')
            return
        if not parent_folder_id:
            errors.append('Parent Folder id is empty')
            return
        drive_service = cls.get_drive_service()
        if not drive_service:
            errors.append('Drive service not defined')
            return
        try:
            folder = drive_service.files().update(
                fileId=folder_id, addParents=parent_folder_id,
                fields='id, mimeType, parents').execute()
        except http_errors.HttpError, error:
            errors.append(str(error))
            return
        return folder

    @classmethod
    def create_drive_folder(cls, folder_name, errors):
        """Creates a drive folder"""
        if not folder_name.strip():
            errors.append('Folder name is empty')
            return

        drive_service = cls.get_drive_service()
        if not drive_service:
            errors.append('Drive service not defined')
            return
        try:
            metadata = {
                'name': folder_name,
                'title': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_service.files().insert(
                body=metadata, fields='id, mimeType, parents').execute()
            if not folder:
                errors.append('Folder could not be created.')
                return
            return folder
        except http_errors.HttpError, error:
            errors.append(str(error))
            return
        return folder

    @classmethod
    def create_drive_folder_with_parent(cls, parent_folder_id, folder_name,
                                        errors):
        """Creates a drive folder and adds a parent to it"""
        if not cls.is_drive_folder_accessible(parent_folder_id, errors):
            return

        folder = cls.create_drive_folder(folder_name, errors)
        if not folder:
            return
        return cls.add_parent_to_folder(folder['id'], parent_folder_id, errors)

    @classmethod
    def get_or_create_drive_folder_with_parent(cls, parent_folder_id,
                                               folder_name, errors):
        """Gets or creates a drive folder"""
        folder = cls.get_drive_folder_by_name(
            parent_folder_id, folder_name, errors)
        if not folder:
            folder = cls.create_drive_folder_with_parent(
                parent_folder_id, folder_name, errors)
        return folder

    @classmethod
    def copy_file(cls, *args, **kwargs):
        """Calls the drive_service.files()'s copy() function"""
        drive_service = cls.get_drive_service()
        if not drive_service:
            return None
        files = drive_service.files()
        return files.copy(*args, **kwargs)
