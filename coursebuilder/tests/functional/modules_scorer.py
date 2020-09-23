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

"""Analytics for extracting facts based on StudentAnswerEntity entries."""

__author__ = 'Rahul Telgote (rtelgote@google.com)'

import collections
from modules.scoring import scorer
from common import crypto
from common import utils as common_utils
from models import courses
from models import models
from models import transforms
from models.data_sources import utils as data_sources_utils
from tests.functional import actions
from common import tags

from google.appengine.ext import db

COURSE_NAME = 'test_course'
COURSE_TITLE = 'Test Course'
ADMIN_EMAIL = 'admin@test.com'
QUID1 = 4785074604081152
QUID2 = 5066549580791808
AssessmentDef = collections.namedtuple('AssessmentDef',
                                       ['unit_id', 'title', 'html_content'])
EntityDef = collections.namedtuple('EntityDef',
                                   ['entity_class', 'entity_id',
                                    'entity_key_name', 'data'])

ASSESSMENTS = [
    AssessmentDef(
        1, 'Sub Question',
        '<question quid="4785074604081152" weight="1" '
        'instanceid="8TvGgbrrbZ49"></question><br>'),

    AssessmentDef(
        2, 'One Question',
        '<question quid="5066549580791808" weight="1" '
        'instanceid="zsgZ8dUMvJjz"></question><br>'),

]

ENTITIES = [
    # Questions -----------------------------------------------------------
    EntityDef(
        models.QuestionEntity, QUID1, None,
        '{"question": "To produce maximum generosity, what should be the '
        'overall shape of the final protrusion?", "rows": 1, "columns": 1'
        '00, "defaultFeedback": "", "graders": [{"matcher": "case_insensi'
        'tive", "feedback": "", "score": "0.7", "response": "oblong"}, {"'
        'matcher": "case_insensitive", "feedback": "", "score": "0.3", "r'
        'esponse": "extended"}, {"matcher": "case_insensitive", "feedback":'
        ' "", "score": "-3.3", "response": "test_negative"}], "type": 1, '
        '"description": "Maximum generosity protrusion shape", "version":'
        ' "1.5", "hint": ""}'),

    EntityDef(
        models.QuestionEntity, QUID2, None,
        '{"question": "Describe the shape of a standard trepanning hammer'
        '", "multiple_selections": false, "choices": [{"feedback": "", "s'
        'core": 1.0, "text": "Round"}, {"feedback": "", "score": -0.5, "te'
        'xt": "Square"}, {"feedback": "", "score": 1.0, "text": "Diamond"'
        '}, {"feedback": "", "score": -3.0, "text": "Pyramid"}], "type": 0'
        ', "description": "Trepanning hammer shape", "version": "1.5"}')
]

EXPECTED_COURSE_UNITS = [
    {
        'title': 'One Question',
        'unit_id': '2',
        'now_available': True,
        'type': 'A',
    },

    {
        'title': 'Sub Question',
        'unit_id': '1',
        'now_available': True,
        'type': 'A',
    }
]

EXPECTED_QUESTIONS = [
    {
        'question_id': str(QUID1),
        'description': 'Maximum generosity protrusion shape',
        'graders': ['oblong', 'extended']
    },

    {
        'question_id': str(QUID2),
        'description': 'Trepanning hammer shape',
        'choices': ['Round', 'Square', 'Diamond', 'Pyramid']
    },

]

EXPECTED_ANSWERS = [
    {'unit_id': '1', 'sequence': 0, 'count': 1, 'is_valid': True,
     'answer': 'oblong', 'question_id': str(QUID1)},
    {'unit_id': '1', 'sequence': 0, 'count': 1, 'is_valid': False,
     'answer': 'spalpeen', 'question_id': str(QUID1)},
    {'unit_id': '2', 'sequence': 0, 'count': 1, 'is_valid': True,
     'answer': '1', 'question_id': str(QUID2)},
    {'unit_id': '2', 'sequence': 0, 'count': 1, 'is_valid': True,
     'answer': '3', 'question_id': str(QUID2)},
]


class ScoringTest(actions.TestBase):
    QUESTION_ID = ''
    HTML_STRING = ''
    QUESTION_DTO = ''
    NODE_LIST = ''

    def setUp(self):
        super(ScoringTest, self).setUp()

        self.context = actions.simple_add_course(COURSE_NAME, ADMIN_EMAIL,
                                                 COURSE_TITLE)
        self.course = courses.Course(None, self.context)
        self.unit = self.course.add_unit()
        self.unit.title = 'Test Unit'
        self.unit.now_available = True

        for assessment in ASSESSMENTS:
            self._add_assessment(self.unit, self.course, assessment)
        self.course.save()

        for entity in ENTITIES:
            self._add_entity(self.context, entity)

    def _add_assessment(self, unit, course, assessment_def):
        assessment = course.add_assessment(unit)
        assessment.title = assessment_def.title
        assessment.now_available = True
        assessment.html_content = assessment_def.html_content
        course.update_unit(assessment)
        self.HTML_STRING = assessment.html_content
        course.save()

    def _add_entity(self, context, entity):
        with common_utils.Namespace(context.get_namespace_name()):
            if entity.entity_id:
                key = db.Key.from_path(entity.entity_class.__name__,
                                       entity.entity_id)
                to_store = entity.entity_class(data=entity.data, key=key, question_id=entity.entity_id)
            else:
                to_store = entity.entity_class(key_name=entity.entity_key_name,
                                               data=entity.data)
            to_store.put()
            to_store.save()

            self.QUESTION_DTO = scorer.get_question(entity.entity_id)
            self.NODE_LIST = scorer.get_assement_objects(self.HTML_STRING)

    def _get_data_source(self, source_name):
        xsrf_token = crypto.XsrfTokenManager.create_xsrf_token(
            data_sources_utils.DATA_SOURCE_ACCESS_XSRF_ACTION)
        url = ('/test_course/rest/data/%s/items?' % source_name +
               'data_source_token=%s&page_number=0' % xsrf_token)
        response = self.get(url)
        return transforms.loads(response.body)['data']

    # def test_get_question(self):
        self.assertEqual(str(type(self.QUESTION_DTO)), "<class 'models.models.QuestionDTO'>")

    def test_get_assement_objects(self):
        node_list_keys = [u'8TvGgbrrbZ49']
        self.assertEquals(self.NODE_LIST.keys(), node_list_keys)

    def test_get_question_object(self):
        quest_obj = {'q': self.QUESTION_DTO, 'weight': u'1'}
        self.assertEqual(str(type(quest_obj['q'])), "<class 'models.models.QuestionDTO'>")

    def test_score_sa_question(self):
        score = scorer.score_sa_question({u'response': u'oblong'}, self.QUESTION_DTO)
        self.assertEqual(score, 0.7)
        score = scorer.score_sa_question({u'response': u'test_negative'}, self.QUESTION_DTO)
        self.assertEqual(score, -3.3)

    def test_score_mc_question(self):
        score = scorer.score_mc_question([False, False, False, False], self.QUESTION_DTO, negative_marking=True)
        self.assertEqual(0.0, score)
        score = scorer.score_mc_question([False, True, False, True], self.QUESTION_DTO, negative_marking=True)
        self.assertEqual(-3.5, score)
        score = scorer.score_mc_question([True, True, True, True], self.QUESTION_DTO, negative_marking=True)
        self.assertEqual(-1.5, score)
        score = scorer.score_mc_question([False, True, True, False], self.QUESTION_DTO, negative_marking=True)
        self.assertEqual(0.5, score)
        score = scorer.score_mc_question([True, False, False, True], self.QUESTION_DTO, negative_marking=True)
        self.assertEqual(-2.0, score)

        # test case if negative marking is NOT ENABLE
        score = scorer.score_mc_question([False, False, False, False], self.QUESTION_DTO, negative_marking=False)
        self.assertEqual(0.0, score)
        score = scorer.score_mc_question([False, True, False, True], self.QUESTION_DTO, negative_marking=False)
        self.assertEqual(0.0, score)
        score = scorer.score_mc_question([True, True, True, True], self.QUESTION_DTO, negative_marking=False)
        self.assertEqual(0.0, score)
        score = scorer.score_mc_question([False, True, True, False], self.QUESTION_DTO, negative_marking=False)
        self.assertEqual(0.0, score)
        score = scorer.score_mc_question([True, False, False, True], self.QUESTION_DTO, negative_marking=False)
        self.assertEqual(0.0, score)
        score = scorer.score_mc_question([True, False, True, False], self.QUESTION_DTO, negative_marking=False)
        self.assertEqual(2.0, score)
        score = scorer.score_mc_question([True, True, True, False], self.QUESTION_DTO, negative_marking=False)
        self.assertEqual(0.0, score)

    def test_score_question_group(self):
        responses = {u'8TvGgbrrbZ49': {u'response': u'oblong'}, u'individualScores': {u'8TvGgbrrbZ49': 1},
                     u'version': u'1.5', u'containedTypes': {u'8TvGgbrrbZ49': u'SaQuestion'},
                     u'answers': {u'8TvGgbrrbZ49': u'oblong'}}
        questions = self.NODE_LIST
        group_score = scorer.score_question_group(responses, questions)
        self.assertEquals(group_score, (0.7, 1.0))

    def test_check_case_insensitive(self):
        user_response = 'pyTHOn'
        correct_answer = 'Python'
        self.assertTrue(scorer.check_case_insensitive(user_response, correct_answer))

    def test_check_regex(self):
        user_response = 'python'
        correct_answer = '/python/gim/ the best language'
        self.assertTrue(scorer.check_regex(user_response, correct_answer))

    def test_check_numeric(self):
        user_response = 5
        correct_answer = 5.0
        self.assertTrue(scorer.check_numeric(user_response, correct_answer))

    def test_check_range(self):
        user_response = 3.7
        correct_answer = '3.3-3.9'
        self.assertTrue(scorer.check_range(user_response, correct_answer))