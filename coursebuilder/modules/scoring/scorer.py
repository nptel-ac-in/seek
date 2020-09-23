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

"""Module for scoring assessments."""

__author__ = 'abhinavk@google.com (Abhinav Khandelwal)'

import logging
import re

from common import tags
from models import models as m_models
from modules.assessment_tags import questions as q_tags


def check_case_insensitive(user_response, correct_answer):
    return user_response.lower() == correct_answer.lower()

def check_regex(user_response, correct_answer):
    regex_group = re.match('/(.*)/([gim]*)/', correct_answer)
    if regex_group is not None:
        regexp = regex_group.groups()[0]
        flags_str = regex_group.groups()[1]
        flags = 0
        for flag in flags_str:
            if flag == 'i':
                flags = flags | re.I
            elif flag == 'm':
                flags = flags | re.M
    else:
        regexp = correct_answer
        flags = 0
    res = re.match(regexp, user_response, flags=flags)
    return res is not None

def check_numeric(user_response, correct_answer):
    try:
        return float(user_response) == float(correct_answer)
    except Exception:
        return False

def check_range(user_response, correct_answer):
    answer_range = correct_answer.split('-');
    val1 = float(answer_range[0])
    val2 = float(answer_range[1])
    if val1 >= val2:
        low_range = val2
        high_range = val1
    else:
        low_range = val1
        high_range = val2
    try:
        r = float(user_response)
        return r >= low_range and r <= high_range
    except Exception:
        return False


def get_question(quid):
    """Returns Question Object.
    Args:
      quid: String. The question id.
    """
    try:
        question_dto = m_models.QuestionDAO.load(quid)
    except Exception:  # pylint: disable-msg=broad-except
        return None
    if not question_dto:
        return None
    return question_dto


def get_question_object(node):
    quid = node.attrib.get('quid')
    question = get_question(quid)
    if not question:
        return None
    instanceid = node.attrib.get('instanceid')
    weight = node.attrib.get('weight')
    return {'q' : question, 'weight': weight}

def get_question_group_object(node):
    group_instanceid = node.attrib.get('instanceid')
    qgid = node.attrib.get('qgid')
    question_group_dto = m_models.QuestionGroupDAO.load(qgid)
    if not question_group_dto:
        return None

    questions = dict()
    for ind, item in enumerate(question_group_dto.dict['items']):
        quid = item['question']
        question = get_question(quid)
        if question:
            question_instanceid = '%s.%s.%s' % (group_instanceid, ind, quid)
            questions[question_instanceid] = {
                'q' : question, 'weight': item['weight'] }
    return questions

def get_assement_objects(html_string):
    """Get assessment objects."""

    if not html_string:
        return None
    node_list = dict()

    def _process_object_tree(elt, used_instance_ids):
        if elt.tag == q_tags.QuestionTag.binding_name:
            return get_question_object(elt)
        elif elt.tag == q_tags.QuestionGroupTag.binding_name:
            return get_question_group_object(elt)
        return None

    def _parse_html_node(elt, used_instance_ids, node_list):
       for child in elt:
           _parse_html_node(child, used_instance_ids, node_list)

       if 'instanceid' not in elt.attrib:
           return
       instance_id = elt.attrib['instanceid']
       if instance_id in used_instance_ids:
           return
       used_instance_ids.add(instance_id)
       node = _process_object_tree(elt, used_instance_ids)
       if node:
           node_list[instance_id] = node

    root = tags.html_string_to_element_tree(html_string)
    used_instance_ids = set([])
    for elt in root:
        _parse_html_node(elt, used_instance_ids, node_list)
    return node_list

def score_mc_question(response, question, negative_marking):
    choices = question.dict['choices']
    score = 0
    for index in range(len(response)):
        res = response[index]
        if res:
            choice = choices[index]
            if negative_marking is True:
                score += float(choice['score'])
            else:
                if float(choice['score']) < 0.0:
                    return 0.0
                score += float(choice['score'])
    return score

def score_sa_question(response, question):
    score = 0
    graders = question.dict['graders']
    user_response = response['response'].strip()
    for grader in graders:
        matcher = grader['matcher']
        correct_answer = grader['response'].strip()
        matched = False
        if matcher == 'case_insensitive':
            matched = check_case_insensitive(user_response, correct_answer)
        elif matcher == 'regex':
            matched = check_regex(user_response, correct_answer)
        elif matcher == 'numeric':
            matched = check_numeric(user_response, correct_answer)
        elif matcher == 'range_match':
            matched = check_range(user_response, correct_answer)
        if matched:
            score += float(grader['score'])
    return max(score, 0)

def get_question_for_give_key_ignore_order(questions, key_with_order):
    key_with_order_parts = key_with_order.split(".")
    if len(key_with_order_parts) != 3:
        return None
    qg_id = key_with_order_parts[0]
    q_id = key_with_order_parts[2]
    for key, value in questions.items():
        key_parts =  key.split(".")
        if qg_id == key_parts[0] and q_id == key_parts[2]:
            return value
    return None


def score_question_group(responses, questions, negative_marking, individual_scores=None, ignore_order=False):
    top_level = (individual_scores is None)
    if top_level:
        individual_scores = dict()
    full_score = 0
    full_weight = 0
    for key, response in responses.items():
        if key not in questions:
            if ignore_order == True:
                question_container = get_question_for_give_key_ignore_order(questions, key)
                if question_container is None:
                    continue
            else:
                continue
        else:
                question_container = questions[key]

        if 'q' not in question_container:
            score, weight = score_question_group(
                response, question_container, negative_marking, individual_scores,ignore_order=ignore_order)
        else:
            question = question_container['q']
            if 'type' not in question.dict:
                logging.error("don't know the type of the question")
                continue
            question_type = question.dict['type']
            score = 0
            weight = 0
            if question_type == 0:
                score = score_mc_question(response, question, negative_marking)
            elif question_type == 1:
                score = score_sa_question(response, question)
            weight = float(question_container['weight'])
            score *= weight
            if top_level:
                individual_scores[key] = score
            else:
                key_parts = key.split('.')
                top_level_key = key_parts[0]
                key_index = int(key_parts[1])
                if top_level_key not in individual_scores:
                    l = []
                else:
                    l = individual_scores[top_level_key]
                while len(l) <= key_index:
                    l.append(0)
                l[key_index] = score
                individual_scores[top_level_key] = l
        full_score += score
        full_weight += weight
    if top_level:
        responses['individualScores'] = individual_scores
    return full_score, full_weight

def score_assessment(answers, questions_html, negative_marking,ignore_order=False):
    questions = get_assement_objects(questions_html)
    score, weight = score_question_group(answers, questions, negative_marking, ignore_order=ignore_order)
    return round((score * 100 ) / weight) if weight else 0
