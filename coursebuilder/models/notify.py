# Copyright 2012 Google Inc. All Rights Reserved.
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

"""Utility for Sending notifications."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import appengine_config
import bs4
from common import users
from modules.notifications import notifications

from google.appengine.api import mail
from google.appengine.api import namespace_manager

from modules.pwa import notifications as push_notif


class EmailManager(object):
    """Notification Manager. Sends emails out."""

    def __init__(self, course):
        self._course = course
        self._user = users.get_current_user()

    def send_mail(self, subject, body, reciever, sender=None, intent='default'):
        """send email."""
        if sender is None:
            sender = self._user.email()

        notifications.Manager.send_async(
            reciever, sender, intent, body, subject,
            )
        return True

    def send_mail_sync(self, subject, body, reciever, sender=None,
            intent='default', html=None):
        """send email synchronously"""
        if sender is None:
            sender = self._user.email()

        notifications.Manager.send_sync(reciever, sender, intent, body, subject,
                                        html=html)

    def send_announcement(self, subject, body, intent):
        """Send an announcement to course announcement list."""
        announce_email = self._course.get_course_announcement_list_email()
        if announce_email:
            self.send_mail(subject, body, announce_email,
                           appengine_config.ANNOUNCEMENT_SENDER_EMAIL, intent)
        body = bs4.BeautifulSoup(body).get_text()
        push_notif.PushNotificationBase.send_message_for_namespace(
            subject, body, namespace_manager.get_namespace())
        return False
