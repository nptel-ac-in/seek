# Copyright 2018 Google Inc. All Rights Reserved.
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

"""Contains Code related to Push notifications for mobile devices"""

__author__ = 'Rishav Thakker (rthakker@google.com)'

import logging
from models import transforms
from models import models

import firebase_admin
from firebase_admin import messaging
from firebase_admin import credentials

class PushNotificationBase(object):
    """Base class for Push notifications"""

    @classmethod
    def get_topic_name_for_namespace(cls, namespace):
        return 'nptel-push-notifications-%s' % namespace

    @classmethod
    def _initialize_firebase_app(cls):
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": "nptelmooc2013",
            "private_key_id": "90846c200dac5482c4d3e577501cf049f3a1fe56",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDT6VpFRev3ucE9\n+3jM3Q/eevisgqKAtDQLOfRnqUALLWjKHMvfQEGPpYYKuyWHmw6cZsj9n1E3MTKZ\nm4w5oEzmtSvUbNE78TtZubx1OaP8qf7z2+C0WuhLdtRk4n3NCcMfV8KK0krchKD5\npeqmpd7HVCh/BCSZmZWCQM7jD5IHp6PQHhbogHT7qjn6CLo4nQvRN361+gsCjCR3\nFRveHpVGF+wJ1/r5WGAtpVAUV7mj2YCm5ehsgNHEJVe6sqe9Unp6Q10renxl9N3s\n4xmF5cOa9gYs+8P87l3BOB125G3W9hwPDtvqma5pv3MCj2AdnynNqO2ituT/h/1U\nmmRnx1NZAgMBAAECggEARgaIGnkbGz7qUQme5w+r1UiMkTEP8vjZc9ZAYdrne2oT\nhSpT4l+w6n93lmc2ZSPDhcJfa5Pweg0LXAAvK8HBd8FpjOYylBzIkINUd+ZGvtEM\nG1hO3jpmJb3MPNQtXwp5TIurEUWhkFJRgX2m10/bmMHCKgrb71f1tFenJhg4mMde\nX7pilJeZndEaJyH0V7UWjHY03jYGbbNgVNQOeAVSBOna1cc6cIvEAx1BE0TmcVnP\njNHoM1MD7ayc8xVAtLbByxmi850gL7fHGUnTvrqrTz2pYXFDgNKY3T5uCrAA7QoX\nGvdboQfizjanKK/AZG27hMA5F7R0Oqrr8NdjgX4o0wKBgQDtXuJw032HAoXdmDI2\nWt+5b6pRAWJiYtH99CIRGWt9jNw2mqRyYUAL+gUvR64euZ6Ut5svMnjZJ9k1jcSl\n1ZahspWHwVlnJl2XS/Msq0pz7TkC+6QgReEEI/ZBsSkHb1b4plGFOC4pSya35geq\nFH7GsM4mOSV0qfqXY/wPDk48owKBgQDkivVMesyiMjR6pBfO7VsWOsslV9W3iIru\nbLiwwETrzljPFY/7hRcob6Mg3r+zrUXEvCexJPOtceUteVf/FJU0PwMdeli9Acqg\n0NAXTuJg03QO42lA2wco2tW9qcBYgj3/g6N5LIw6/sTsynJWgK6Ta00l+AcLyK42\nOj9G9XvT0wKBgAq2s6XABfRoCr67tdh6NYrbHWbWlyg1qaC6uibnbNCX4QCd7joz\nZX6k5EMECznbyuqPdvOkZYv3nngqU+vgPhJCSzl7YpujQaoohWtIt+2PkXku/nNu\nc/+J1/2TD3UEc3p5l0haBstaVv8J5OKqViaFqGhVP/mKCoN2wdO0I5fdAoGBAKmu\niiV4XwploBUWVB7sl15P1JgrOKAFnrEaw51ng0RYdhN6fOZPkDwTdthmyYoLses5\nj3a0ar9x+qfimfTnQUgDKLrwJYZfGCSCJJ3JkcY1+Ms9CN6AQDaTE3K33/lW6dUV\n1X+YFZ2PnoH4ZR/YdsU5O5RfLEwReVcFtAlpJcDFAoGBAN2djEmE2nGcfHKwnFMi\nu8PAK7ZiFRy4jTfSY53CwUIy7h5uHmjVsjtoaKeoLDLLjifDogoIAOQ9/dB/E5Dz\nK9SE+074c1FDLJT+OM4B6jRoOBPcNQP15s5IkzXAYfSjD3Y5EfsFpguhwCOaKs3P\n7tDqkhufCf3XGkp3/7mUJLJe\n-----END PRIVATE KEY-----\n",
            "client_email": "nptelmooc2013@appspot.gserviceaccount.com",
            "client_id": "110105681200702212596",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/nptelmooc2013%40appspot.gserviceaccount.com"
        })
        try:
            firebase_admin.initialize_app(cred)
        except ValueError as e:
            logging.error(
                "PUSH_NOTIFICATION_FAILURE: Failed to initialize firebase app")

    @classmethod
    def _add_tokens_to_topic(cls, tokens, topic):
        if not (tokens and topic):
            return
        cls._initialize_firebase_app()
        response = messaging.subscribe_to_topic(tokens, topic)
        if response.success_count != len(tokens):
            logging.error('PUSH_NOTIFICATION_FAILURE: Failed to add tokens to '
                          'topic: %s out of %s succeeded',
                          response.success_count, len(tokens))
            raise Exception("wew")
            return

    @classmethod
    def add_tokens_for_namespace(cls, tokens, namespace):
        cls._add_tokens_to_topic(
            tokens, cls.get_topic_name_for_namespace(namespace))

    @classmethod
    def _send_message_to_topic(cls, title, body, topic):
        cls._initialize_firebase_app()
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            # android=messaging.AndroidConfig(
            #     ttl=datetime.timedelta(seconds=3600),
            #     priority='normal',
            #     # restrictedPackageName =
            #     notification=messaging.AndroidNotification(
            #         title=title,
            #         body=body,
            #         icon='stock_ticker_update', # TODO(sagarkothari) Update this
            #         color='#f45342', # TODO(sagarkothari) Update this
            #         # clickAction= #TODO(sagarkothari) Update this to open Notifications for nptel pwa
            #     ),
            # ),
            # apns=messaging.APNSConfig(
            #     headers={'apns-priority': '10'},
            #     payload=messaging.APNSPayload(
            #         aps=messaging.Aps(
            #             alert=messaging.ApsAlert(
            #                 title=title
            #                 body=body,
            #             ),
            #             badge=42,
            #         ),
            #     ),
            #     # TODO(rthakker) I'm not sure if iOS supports push notifications
            #     # with browsers yet. Research.
            # ),
            # webpush=messaging.WebpushConfig(
            #     notification=messaging.WebpushNotification(
            #         title=title,
            #         body=body,
            #         # icon='https://my-server/icon.png',
            #     ),
            # ),
            topic=topic,
        )
        response = messaging.send(message)

    @classmethod
    def send_message_for_namespace(cls, title, body, namespace):
        cls._send_message_to_topic(
            title, body, cls.get_topic_name_for_namespace(namespace))

    @classmethod
    def register_token(cls, token, profile):
        """
        Adds the token in profile object and saves to database.
        Returns the token if successful.
        """
        if not (token and profile):
            return
        if token not in profile.push_tokens_as_list:
            profile.push_tokens_as_list.append(token)
            if len(profile.push_tokens_as_list) > 5:
                profile.push_tokens_as_list.pop(0)
            models.StudentProfileDAO.update(
                user_id=profile.user_id,
                email=profile.email,
                push_tokens_as_list=profile.push_tokens_as_list,
                profile_only=True,
            )

            # Add token to user's registered course topics
            from controllers import sites
            enrollment_dict = transforms.loads(profile.enrollment_info)
            open_courses = [obj.namespace for obj in sites.get_all_courses()]
            for ns, is_enrolled in enrollment_dict.iteritems():
                if ns in open_courses and is_enrolled:
                    cls.add_tokens_for_namespace([token], ns)
        return token
