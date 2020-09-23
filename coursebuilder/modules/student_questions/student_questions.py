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

"""Module for handling video-tagging requests."""

__author__ = 'Vishrut Patel (vishrut@google.com@google.com)'


import json
import time
from controllers.utils import BaseHandler
from controllers.utils import ReflectiveRequestHandler
from models import custom_modules
from models import notify
from models.entities import BaseEntity
from modules.notifications import notifications

from google.appengine.ext import db

custom_module = None
DEFAULT_RETRIEVAL_LIMIT = 10
DEFAULT_TIMEFRAME_WINDOW = 30
FORUM_QUESTION_INTENT = 'courseforumquestion'
class StudentQuestionEntity(BaseEntity):
    """Holds the questions asked by the students."""
    user_id = db.StringProperty(indexed=False, required=True)
    resource_id = db.StringProperty(indexed=True, required=True)
    click_count = db.IntegerProperty(indexed=True, required=False)
    creation_time = db.DateTimeProperty(indexed=False, auto_now_add=True)
    question_data = db.TextProperty()


class StudentQuestionsHandler(BaseHandler, ReflectiveRequestHandler):
    """Handler for requests for video-tagging."""

    # Requests to these handlers automatically go through an XSRF token check
    # that is implemented in ReflectiveRequestHandler.
    default_action = ''
    get_actions = ['relevant_questions', 'all_questions']
    post_actions = ['submit_question', 'inc_count']

    def get_relevant_questions(self):
        """Return the requested student question entities as a json package."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return
        timeframe_window = DEFAULT_TIMEFRAME_WINDOW
        argument_list = self.request.arguments()

        if 'limit' not in argument_list:
            student_question_limit = DEFAULT_RETRIEVAL_LIMIT
        else:
            student_question_limit = min(int(self.request.get('limit')),
                                         DEFAULT_RETRIEVAL_LIMIT)

        if 'video_timestamp' not in argument_list:
            video_timestamp = None
            timeframe_window = None
        else:
            ts = self.request.get('video_timestamp')
            video_timestamp = int(ts) if len(ts) > 0 else 0

        results = self.filter_questions(str(self.request.get('resource_id')),
                                        video_timestamp,
                                        timeframe_window,
                                        student_question_limit)

        relevant_questions_json = self.prepare_json(results,
                                                    self.request.get('type'))
        self.response.out.write(relevant_questions_json)

    def filter_questions(self, resource_id, timestamp, window, limit):
        """Returns student questions after applying the given restrictions.

        Args:
            lesson_id: int. The id of the lesson to which the
                question should belong.
            unit_id: int. The id of the unit to which the
                question should belong.
            resource_id: string. YouTube ID, in case of videos.
            timestamp: int. Unit - seconds. The time of the video, in seconds,
                around which the questions should be located.
            window: int. Unit - seconds. The questions lying in the range
                (timestamp - window, timestamp + window).
            limit: int. Maximum number of questions to be
                retrieved.

        Returns:
            A list of student questions which pass the above filters.
        """
        results = []
        sq_entities = StudentQuestionEntity.all()
        sq_entities = sq_entities.filter('resource_id =', resource_id)
        sq_entities = sq_entities.order('-click_count')
        for sq_entity in sq_entities:
            question_data = json.loads(sq_entity.question_data)
            if timestamp is not None:
                sq_timestamp = int(question_data['timestamp']) if question_data['timestamp'] else 0
                if (sq_timestamp <= (timestamp + window) and
                    sq_timestamp >= (timestamp - window)):
                    results.append(sq_entity)
            else:
                results.append(sq_entity)
            if limit is not None:
                if limit > 0:
                    limit -= 1
                else:
                    break
        return results

    def prepare_json(self, student_questions, json_type):
        """Returns the student_questions packaged as asingle JSON object."""
        questions = []
        for student_question in student_questions:
            question_data = json.loads(student_question.question_data)
            timestamp = (
                int(question_data['timestamp']) if question_data['timestamp']
                else 0)
            timestamp_string = time.strftime('%H:%M:%S', time.gmtime(timestamp))
            ques = None
            if 'summary' in question_data.keys():
                ques = question_data['summary']
            if not ques:
                ques = question_data['question']

            question_info = {'key': str(student_question.key()),
                             'question': ques,
                             'time': timestamp_string,
                             'click_count': student_question.click_count}
            questions.append(question_info)
        json_dict = {'type': json_type,
                     'questions': questions}
        json_out = json.dumps(json_dict, sort_keys=True)
        return json_out

    def post_submit_question(self):
        """Submit a question."""
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return
        user_id = str(student.user_id)
        video_timestamp = self.request.get('video_timestamp')
        if not video_timestamp:
            video_timestamp = '0'
        question = (self.request.get('question').strip() if
                    self.request.get('question') else
                    '')
        short_description = (self.request.get('short_description').strip() if
                    self.request.get('short_description') else
                    '')
        if not question and not short_description:
            return
        question_data_json = {'resource_type': 'video',
                              'timestamp': video_timestamp,
                              'question': question,
                              'summary': short_description}
        s = StudentQuestionEntity(user_id=user_id,
                                  resource_id=self.request.get('resource_id'),
                                  click_count=0,
                                  question_data=json.dumps(question_data_json,
                                                           sort_keys=True))
        s.put()
        self.email_to_forum(s)

    def email_to_forum(self, question):
        """Post the student question to the Group."""
        question_data = json.loads(question.question_data)
        receiver = self.get_course().get_course_forum_email()
        if receiver is None:
            return

        timestamp = (
            int(question_data['timestamp']) if question_data['timestamp'] else 0
            )
        timestamp_string = time.strftime('%H:%M:%S', time.gmtime(timestamp))
        subject = '%s' % (question_data['summary'])
        if not subject:
          subject = '%s' % (question_data['question'])
        if len(subject) > 50:
            subject = '%s ...' % subject[:46]

        body = """
        Hi,<br/><br/>
        I have a question about what is happening in this video at %s -
        <br/><br/>

            http://www.youtube.com/watch?v=%s#t=%ss. <br/><br/>

        %s.<br/><br/>

        Thanks!<br/><br/>
        <hr/><br/>

        Reference Key - %s""" % (timestamp_string,
                                 question.resource_id,
                                 question_data['timestamp'],
                                 question_data['question'],
                                 question.key())

        email_manager = notify.EmailManager(self.get_course())
        email_manager.send_mail_sync(subject, body, receiver)

    @db.transactional()
    def increment_count(self):
        question = StudentQuestionEntity.get(self.request.get('key'))
        question.click_count += 1
        question.put()

    def post_inc_count(self):
        student = self.personalize_page_and_get_enrolled()
        if not student:
            return
        self.increment_count()

def register_module():
    """Registers this module in the registry."""

    student_questions_handlers = [('/student_questions',
                                   StudentQuestionsHandler)]

    global custom_module
    custom_module = custom_modules.Module(
        'Student Questions module',
        'A set of handlers for video-tagging.',
        [], student_questions_handlers)
    return custom_module
