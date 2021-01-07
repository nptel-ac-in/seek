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

"""Classes and methods to create and manage analytics dashboards."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'

import csv
import copy
import logging
import os
import json
import urlparse
import StringIO
import time

from apiclient import errors
from apiclient.http import MediaIoBaseUpload

from mapreduce import context

import appengine_config
from google.appengine.api import namespace_manager

from common import csv_unicode
from common import safe_dom
from controllers import sites
from controllers.utils import ApplicationHandler
from controllers.utils import BaseHandler
from controllers.utils import HUMAN_READABLE_TIME_FORMAT
from common.utils import Namespace
import jinja2
from models import courses
from models import jobs
from models import roles
from models import transforms
from models import utils
from models import data_sources
from models import analytics
from models import models
from models import course_list
from modules.google_service_account import google_service_account
from modules.mentor import mentor_model
from modules.nptel import settings

from models.models import PersonalProfile
from models.models import Student
from models.models import StudentProfileDAO
from models.models import PersonalProfileDTO

from models import course_list
from modules.spoc import base as spoc_base
from modules.local_chapter import local_chapter_model


# ID of directory where all the generated student file list are stored.
_PARENT_ID = "0B0CGOzyU-WMVNDM5R0dZNjBXREk"


def get_folder_id(course_info):
    if not course_info:
        return _PARENT_ID
    nptel_settings = course_info.get(settings.NPTEL_SECTION, dict())
    folder_id = nptel_settings.get(settings.DUMP_FOLDER_ID, _PARENT_ID)
    if folder_id.strip():
        return folder_id
    return _PARENT_ID


def insert_file(title, description, content, course_info):
    """Insert new file to gdrive."""
    body = {'title' : title, 'description': description}
    body['parents'] = [{'id': get_folder_id(course_info)}]
    media = MediaIoBaseUpload(content, mimetype='text/csv', resumable=True)
    try:
        drive_service = google_service_account.GoogleServiceManager.get_service(
            name='drive', version='v2')
        if not drive_service:
            logging.error('Drive service not defined')
            return None
        drive = drive_service.files()
        out = drive.insert(
            body=body,
            media_body=media).execute()
        return out
    except errors.HttpError, error:
        logging.error('An error occured: %s' % error)
        return None
    finally:
        logging.info('cleanup')


class ProfileDataDumpMapReduce(jobs.MapReduceJob):
    """A job that dumps the profile information per course"""

    def __init__(self, app_context):
        self._namespace = ''
        self._course = None
        self._settings = None
        self._course_namespace = ''
        self._app_context = None
	self._job_name = 'job-%s' % self.__class__.__name__
        self.dumpable_courses = []
        for course in sites.get_all_courses():
            if course and not course.closed:
                self.dumpable_courses.append(course.get_namespace_name())

    @staticmethod
    def get_description():
        return 'ProfileDataDumpMapReduce'

    @staticmethod
    def entity_class():
        return PersonalProfile

    def build_additional_mapper_params(self, unused_app_context):
        return { 'dumpable_courses' : self.dumpable_courses }


    @staticmethod
    def map(entity):
        mapper_params = context.get().mapreduce_spec.mapper.params
        dumpable_courses = mapper_params['dumpable_courses']

        enrollment_info = entity.enrollment_info
        if enrollment_info is not None and enrollment_info is not "":
            enrollment_info_dict = transforms.loads(enrollment_info)
            entity_dict = transforms.entity_to_dict(entity)
            entity_dict.update({'user_id': entity.user_id})
            entity_dump = transforms.dumps(entity_dict)
            for key, val in enrollment_info_dict.iteritems():
                if key and val and key in dumpable_courses:
                    yield (key, entity_dump)

    @staticmethod
    def reduce(key, data_list):
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(output, delimiter=',',
                quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['email', 'key', 'name','age_group',
                        'mobile_number','country', 'state', 'city',
                        'college','college_roll_no','local_chapter','college_id','employer_id',
                        'graduation year','profession','employer name', 'is_mentor', 'scholarship',
                        'qualification', 'degree','department','study_year','designation',
                        'motivation','exam_taker'])

        app_context = sites.get_course_index().get_app_context_for_namespace(key)
        with Namespace(app_context.namespace):
            mentor_list = mentor_model.Mentor.get_all_mentors()
            mentor_dict = dict((mentor.user_id, mentor) for mentor in mentor_list)

        for person in data_list:
            person_profile_dict = transforms.loads(person)
            row = []
            row.append(person_profile_dict['email'])
            row.append(person_profile_dict['key'])
            row.append(person_profile_dict['nick_name'])
            row.append(person_profile_dict['age_group'])
            row.append(person_profile_dict['mobile_number'])
            row.append(person_profile_dict['country_of_residence'])
            row.append(person_profile_dict['state_of_residence'])
            row.append(person_profile_dict['city_of_residence'])
            row.append(person_profile_dict['name_of_college'])
            row.append(person_profile_dict['college_roll_no'])
            row.append(person_profile_dict['local_chapter'])
            row.append(person_profile_dict['college_id'])
            row.append(person_profile_dict['employer_id'])
            row.append(person_profile_dict['graduation_year'])
            row.append(person_profile_dict['profession'])
            row.append(person_profile_dict['employer_name'])
            row.append(person_profile_dict['user_id'] in mentor_dict)
            row.append(bool(person_profile_dict['scholarship']))
            row.append(person_profile_dict['qualification'])
            row.append(person_profile_dict['degree'])
            row.append(person_profile_dict['department'])
            row.append(person_profile_dict['study_year'])
            row.append(person_profile_dict['designation'])
            row.append(person_profile_dict['motivation'])
            row.append(person_profile_dict['exam_taker'])
            writer.writerow(row)

        filename = 'profile_%s_%s.csv' % (key,time.strftime("%d-%m-%Y_%H-%M"))
        settings = None

        c = courses.Course(None, app_context=app_context)
        settings = c.get_environ(app_context)

        insert_file(filename, '', output, settings)
        output.close()

class VideoIDDumpMapReduce(jobs.MapReduceJob):
    """A job that dumps the profile information per course"""

    def __init__(self, app_context):
        self._namespace = ''
        self._course = None
        self._settings = None
        self._course_namespace = ''
        self._app_context = None
	self._job_name = 'job-%s' % self.__class__.__name__
        self.dumpable_courses = []
        for course in sites.get_all_courses():
            if course and not course.closed:
                self.dumpable_courses.append(course.get_namespace_name())

    @staticmethod
    def get_description():
        return 'ProfileDataDumpMapReduce'

    @staticmethod
    def entity_class():
        return course_list.CourseList

    def build_additional_mapper_params(self, unused_app_context):
        return { 'dumpable_courses' : self.dumpable_courses }


    @staticmethod
    def map(entity):
        mapper_params = context.get().mapreduce_spec.mapper.params
        dumpable_courses = mapper_params['dumpable_courses']
        for key in dumpable_courses:
            yield (key,key)

    @staticmethod
    def reduce(key,name):
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(output, delimiter=',',
                quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Course Namespace','Lesson Title'])
        toInclude = False
        app_context = sites.get_course_index().get_app_context_for_namespace(key)
        with Namespace(app_context.namespace):
            co = courses.Course(None, app_context=app_context)
            lessons = co._model._lessons
            row = []
            row.append(key)
            for lesson in lessons:
                if lesson.video is None or lesson.video == "":
                    toInclude = True;
                    row.append(lesson.title)
            if toInclude:
                writer.writerow(row)

        if toInclude:
            filename = 'courses_%s_%s.csv' % (key,time.strftime("%d-%m-%Y_%H-%M"))
            settings = None

            c = courses.Course(None, app_context=app_context)
            settings = c.get_environ(app_context)
            insert_file(filename, '', output, settings)
        output.close()


class MentorMenteeDumpMapReduce(ProfileDataDumpMapReduce):
    """A job that generates a mentor-mentee CSV"""

    def __init__(self, app_context, namespaces=None, include_closed=False):
        super(MentorMenteeDumpMapReduce, self).__init__(app_context)
        self._job_name = 'job-%s' % self.__class__.__name__
        self._namespace = ''
        self._course = None
        self._settings = None
        self._course_namespace = ''
        self._app_context = None
        self._job_name = 'job-%s' % self.__class__.__name__
        self.dumpable_courses = []
        if namespaces:
            all_courses = sites.get_all_courses(include_closed=True)
            for course in all_courses:
                if course and course.namespace in namespaces:
                    self.dumpable_courses.append(course.get_namespace_name())
        else:
            for course in sites.get_all_courses(include_closed=include_closed):
                if course:
                    self.dumpable_courses.append(course.get_namespace_name())

    @staticmethod
    def get_description():
        return 'MentorMenteeDumpMapReduce'

    @staticmethod
    def entity_class():
        return course_list.CourseList

    @staticmethod
    def map(entity):
        mapper_params = context.get().mapreduce_spec.mapper.params
        dumpable_courses = mapper_params['dumpable_courses']

        if entity.namespace not in dumpable_courses:
            return

        app_context = sites.get_course_index().get_app_context_for_namespace(
            entity.namespace)

        with Namespace(entity.namespace):
            mentors = mentor_model.Mentor.get_all_mentors()
            output = StringIO.StringIO()
            writer = csv_unicode.UnicodeWriter(output, delimiter=',',
                    quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['Mentor Email', 'Mentee Email', 'Local Chapter College ID (if any)'])
            for mentor in mentors:
                # row = [mentor.email, mentor.user_id, mentor.local_chapter,
                #        mentor.college_id]
                # row = [mentor.email, mentor.user_id]
                mentee_students = StudentProfileDAO.bulk_get_student_by_id(
                    mentor.mentee)

                for s in mentee_students:
                    if s:
                        # row.append(s.email)
                        # row.append(s.user_id)

                        writer.writerow([
                            mentor.email, s.email, mentor.college_id
                            if mentor.local_chapter else ''
                        ])

            filename = 'mentor_mentee_dump_%s_%s.csv' % (
                entity.namespace, time.strftime("%d-%m-%Y_%H-%M"))
            settings = None
            c = courses.Course(None, app_context=app_context)
            settings = c.get_environ(app_context)
            insert_file(filename, '', output, settings)
            output.close()


class ReEnrollToGroupMapReduce(jobs.MapReduceJob):
    """A job that re enrolls all users to announcement groups"""

    def __init__(self, app_context):
        super(ReEnrollToGroupMapReduce, self).__init__(app_context)
        self._job_name = 'job-%s' % self.__class__.__name__

    @staticmethod
    def get_description():
        return 'ReEnrollToGroupMapReduce'

    @staticmethod
    def entity_class():
        return Student

    def build_additional_mapper_params(selfl, unused_app_context):
        course = courses.Course.get(unused_app_context)
        announcement_email = course.get_course_announcement_list_email()
        return {'announcement_email': announcement_email}

    @staticmethod
    def map(entity):
        service = google_service_account.GoogleServiceManager.get_service(
            name='admin', version='directory_v1')
        if not service:
            logging.error('No admin service defined. Failed to add to group.')
            return
        mapper_params = context.get().mapreduce_spec.mapper.params
        announcement_email = mapper_params['announcement_email']
        user_email = entity.email
        members = service.members()
        data = {
            "email": user_email,
            "role": "MEMBER"
        }
        try:
            members.insert(groupKey=announcement_email, body=data).execute()
        except Exception as e:
            logging.error('Failed to insert user into group %s, user %s: %s',
                          announcement_email, user_email, str(e))


class AllCoursesProfileDumpHandler(BaseHandler):
    """Iterates through each course and run job to calcalute average score for
    each unit."""

    def get(self):
        if not roles.Roles.is_super_admin():
            self.response.write('Unauthorized\n')
            return
        job = ProfileDataDumpMapReduce(None)
        job.submit()
        self.response.write('OK\n')

class VideoIdMissingHandler(BaseHandler):
    """Iterates through each course and run job to calcalute average score for
    each unit."""

    def get(self):
        if not roles.Roles.is_super_admin():
            self.response.write('Unauthorized\n')
            return
        job = VideoIDDumpMapReduce(None)
        job.submit()
        self.response.write('OK\n')

class AllCoursesMentorDumpHandler(BaseHandler):
    """Iterates through each course and runs job to generate a mentor-mentee csv
    dump."""

    def get(self):
        if not roles.Roles.is_super_admin():
            self.response.write('Unauthorized\n')
            return
        namespaces = self.request.get_all('namespace')
        job = MentorMenteeDumpMapReduce(
            None, namespaces=namespaces,
            include_closed=bool(self.request.get('include_closed')))
        job.submit()
        self.response.write('OK\n')

class ComputeStudentReportAllCoursesHandler(BaseHandler):
    """Iterates through each course and runs job to generate a mentor-mentee csv
    dump."""

    def get(self):
        if not roles.Roles.is_super_admin():
            self.response.write('Unauthorized\n')
            return
        namespaces = self.request.get_all('namespace')
        job = ComputeStudentReportAllCoursesMapReduce(
            None, namespaces=namespaces)
        job.submit()
        self.response.write('OK\n')


class PerCourseCourseDurableJob(jobs.DurableJob):
    def __init__(self, app_context):
        super(PerCourseCourseDurableJob, self).__init__(app_context)

    @property
    def _course(self):
        return courses.Course(None, app_context=self._app_context)


class QuestionWiseScoreDump(PerCourseCourseDurableJob):
    """A Job that dumps student scores for each question"""

    QUESTION_ID_TEMPLATE = 'a-%s:q-%s'
    QEUESTION_GROUP_ID_TEMPLATE = 'a-%s:qg-%s:q-%s'

    def __init__(self, app_context):
        super(QuestionWiseScoreDump, self).__init__(app_context)
        self._score_id_to_title_list = []
        self.instance_id_to_qid = {}
        self.question_data = {
            'questions': {},
            'question_groups': {}
        }
        self._load_question_data()
        self._update_csv_title_list()

    def _load_question_data(self):
        """Loads the questions into memory"""
        with Namespace(self._namespace):
            question_groups = models.QuestionGroupDAO.get_all()
            questions = models.QuestionDAO.get_all()
        for qg in question_groups:
            self.question_data['question_groups'][int(qg.id)] = qg.dict
        for q in questions:
            self.question_data['questions'][int(q.id)] = q.dict

    def _update_csv_title_list(self):
        for assessment in self._course.get_assessment_list():
            components = self._course.get_assessment_components(
                assessment.unit_id)
            # questions = [c for c in components if c['cpt_name'] in
            #              ['question', 'question-group']]
            # question_groups = [
            #     c for c in components if c['cpt_name'] == 'question-group']
            # self._score_id_to_title_list += [
            #     (
            #         'q_%s-%s' % (assessment.unit_id, question['instanceid']),
            #         '%s: Question-%s' % (assessment.title, question['quid'])
            #     ) for question in questions
            # ]
            for c in components:
                if c['cpt_name'] == 'question':
                    # Simply add it to the list
                    self._score_id_to_title_list.append(
                        (self.QUESTION_ID_TEMPLATE % (
                            assessment.unit_id, c['quid']),
                        '%s: Question' % assessment.title)
                    )
                    self.instance_id_to_qid[c['instanceid']] = c['quid']
                elif c['cpt_name'] == 'question-group':
                    qg = self.question_data['question_groups'][int(c['qgid'])]
                    for q in qg['items']:
                        self._score_id_to_title_list.append(
                            (self.QEUESTION_GROUP_ID_TEMPLATE % (
                                assessment.unit_id, c['qgid'], q['question']),
                            '%s: Question from a group' % assessment.title)
                        )
                    self.instance_id_to_qid[c['instanceid']] = c['qgid']


            # # Update question keys
            # self._question_keys['questions'].update(dict(
            #     (question['quid'], question['description'])
            #     for question in questions
            # ))
            #
            # self._question_keys['question_groups'].update(dict(
            #     (qg['qgid'], qg['description'])
            #     for qg in question_groups
            # ))

    def generate_question_keys_csv(self):
        """
        Generates a CSV which displays question and question group data
        in a csv
        """
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(
            output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([])
        writer.writerow([])
        writer.writerow(['Question ID to Description'])
        writer.writerow(['Question ID', 'Description'])
        for quid, q in self.question_data['questions'].iteritems():
            writer.writerow(['ID: ' + str(quid), q['description']])

        writer.writerow([])
        writer.writerow([])
        writer.writerow(['Question Group ID to Description'])
        writer.writerow(['Question Group ID', 'Description'])
        for qgid, qg in self.question_data['question_groups'].iteritems():
            writer.writerow(['ID: ' + str(qgid), qg['description']])

        return output

    class StudentRow(object):
        """Aggregates Question wise score statistics."""

        def __init__(self, output, score_id_to_title_list, students,
                     parent_obj):
            self._output = output
            self._score_id_to_title_list = score_id_to_title_list
            self._students = students
            self._parent_obj = parent_obj

        def get_scores_row(self, student_answers):
            scores_row = []
            unit_scores = (
                transforms.loads(student_answers.data)
            )
            score_dict = {}
            for unit_id, value in unit_scores.iteritems():
                question_scores = value.get('individualScores', {})
                for instance_id, score in question_scores.iteritems():
                    if instance_id not in self._parent_obj.instance_id_to_qid:
                        logging.debug('Question not found for instance_id %s',
                                      str(instance_id))
                        # Question has probably been deleted. Move on.
                        continue
                    if isinstance(score, list):
                        # score_id = 'qg_%s-%s' % (unit_id, instance_id)
                        qgid = self._parent_obj.instance_id_to_qid[instance_id]
                        qg = self._parent_obj.question_data[
                            'question_groups'][int(qgid)]
                        responses = value.get(instance_id)
                        for i, item in enumerate(qg['items']):
                            score_id = (
                                QuestionWiseScoreDump.
                                QEUESTION_GROUP_ID_TEMPLATE) % (
                                    unit_id, qgid, item['question']
                                )
                            response = "Couldn't Find Response"
                            for r in responses:
                                response_id = r[r.rfind('.') + 1:]
                                if str(response_id) == str(item['question']):
                                    response = responses[r]
                                    break
                            score_dict[score_id] = (score[i], response)
                    else:
                        quid = self._parent_obj.instance_id_to_qid[instance_id]
                        score_id = (
                            QuestionWiseScoreDump.QUESTION_ID_TEMPLATE % (
                                unit_id, quid))
                        response = value.get(instance_id)
                        score_dict[score_id] = (score, response)


            for s in self._score_id_to_title_list:
                score_id = str(s[0])
                score_response_tuple = score_dict.get(score_id)
                if score_response_tuple:
                    score, response = score_response_tuple
                    if isinstance(response, list):
                        selected_values = [unicode(i) for i, r in enumerate(response) if r]
                        response = u"Selected options: %s" % ', '.join(selected_values)
                    elif isinstance(response, dict) and 'response' in response:
                        response = u"Short Answer Response: %s" % response['response']
                    scores_row.append(
                        u', '.join((unicode(score), unicode(response)))
                    )
                else:
                    scores_row.append('')

            return scores_row

        def visit(self, student_answers):
            student = self._students[student_answers.key().name()]
            basic_info_row = [student.email, student.user_id]
            scores_row = self.get_scores_row(student_answers)
            self._output.writerow(basic_info_row + scores_row)

    def run(self):
        """Generates question wise score report"""
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(
            output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        head_row = ['email', 'user_id']
        for s in self._score_id_to_title_list:
            head_row.append(s[1] + '(' + str(s[0]) + ')')
        writer.writerow(head_row)

        student_row = self.StudentRow(
            writer, self._score_id_to_title_list,
            dict((s.user_id, s) for s in Student.all().fetch(None)),
            self)

        mapper = utils.QueryMapper(
            models.StudentAnswersEntity.all(),
            batch_size=500, report_every=1000)

        def map_fn(student_answer):
            student_row.visit(student_answer)

        mapper.run(map_fn)

        filename = 'question_dump_%s_%s.csv' % (
            self._namespace, time.strftime("%d-%m-%Y_%H-%M"))
        settings = self._course.get_environ(self._app_context)
        f = insert_file(filename, '', output, settings)
        output.close()

        # Write question keys to a csv
        filename = 'question_dump_keys_%s_%s.csv' % (
            self._namespace, time.strftime("%d-%m-%Y_%H-%M"))
        output = self.generate_question_keys_csv()
        f = insert_file(filename, '', output, settings)
        output.close()


class ComputeStudentReport(PerCourseCourseDurableJob):
    """A job that computes student statistics."""

    def __init__(self, app_context):
        super(ComputeStudentReport, self).__init__(app_context)
        self._unit_id_to_title_list = []
        self._update_units()

    def _update_units(self):
        for unit in self._course.get_units():
            if unit.scored():
                self._unit_id_to_title_list.append((unit.unit_id, unit.title))

    class StudentRow(object):
        """Aggregates scores statistics."""

        def __init__(self, output, unit_id_to_title_list):
            self._output = output
            self._unit_id_to_title_list = unit_id_to_title_list

        def get_scores_row(self, student):
            scores_row = []
            score_dict = (
                transforms.loads(student.scores) if student.scores else dict())
            for u in self._unit_id_to_title_list:
                unit_name = str(u[0])
                score = ''
                if score_dict.has_key(unit_name):
                    score = str(score_dict[unit_name])
                scores_row.append(score)
            return scores_row

        def visit(self, student):
            basic_info_row = [student.email, student.user_id]
            scores_row = self.get_scores_row(student)
            self._output.writerow(basic_info_row + scores_row)

    def run(self):
        """Computes student statistics."""
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(
            output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        head_row = ['email', 'user id']
        for u in self._unit_id_to_title_list:
            head_row.append(u[1] + '(' + str(u[0]) + ')')
        writer.writerow(head_row)

        student_row = self.StudentRow(writer, self._unit_id_to_title_list)

        mapper = utils.QueryMapper(
            Student.all(), batch_size=500, report_every=1000)

        def map_fn(student):
            student_row.visit(student)

        mapper.run(map_fn)

        filename = '%s_%s.csv' % (self._namespace, time.strftime("%d-%m-%Y_%H-%M"))
        settings = self._course.get_environ(self._app_context)
        file = insert_file(filename, '', output, settings)
        output.close()


class ComputeStudentReportAllCoursesMapReduce(ProfileDataDumpMapReduce):
    """A job that computes student report for all courses"""

    def __init__(self, app_context, namespaces=None):
        self._namespace = ''
        self._course = None
        self._app_context = None
        self._job_name = 'job-%s' % self.__class__.__name__
        self.dumpable_courses = []
        if namespaces:
            self.dumpable_courses = namespaces
        else:
            for course in sites.get_all_courses():
                if course and not course.closed:
                    self.dumpable_courses.append(course.get_namespace_name())

    @staticmethod
    def get_description():
        return self.__class__.__name__

    @staticmethod
    def entity_class():
        return course_list.CourseList

    @staticmethod
    def map(entity):
        mapper_params = context.get().mapreduce_spec.mapper.params
        dumpable_courses = mapper_params['dumpable_courses']

        if entity.namespace not in dumpable_courses:
            return

        app_context = sites.get_course_index().get_app_context_for_namespace(
            entity.namespace)
        with Namespace(entity.namespace):
            dummy_job_obj = ComputeStudentReport(app_context)
            dummy_job_obj.run()


class SaveCourseSettings(PerCourseCourseDurableJob):
    """A job that computes student Qualification."""

    def __init__(self, app_context):
        super(SaveCourseSettings, self).__init__(app_context)

    def run(self):
        """Computes student statistics."""
        settings = self._course.get_environ(self._app_context)
        self._course.save_settings(settings)


class ComputeQualificationForMains(PerCourseCourseDurableJob):
    """A job that computes student Qualification."""

    def __init__(self, app_context):
        super(ComputeQualificationForMains, self).__init__(app_context)
        self._first_cutoff_units = set()
        self._second_cutoff_units = set()
        self._unit_to_multiplier = dict()
        self._update_units()

    def _add_subunits(self, punit_id, l):
        for unit in self._course.get_subunits(punit_id):
            if not unit.now_available:
                continue
            if unit.type != 'PA' and unit.type != 'A':
                continue
            l.add(unit.unit_id)
            self._unit_to_multiplier[str(unit.unit_id)] = (
                100 if unit.type == 'PA' else 1)


    def _update_units(self):
        for unit in self._course.get_public_units():
            if unit.type == 'U':
                if unit.index <= 3:
                    self._add_subunits(unit.unit_id, self._first_cutoff_units)
                elif unit.index <= 6:
                    self._add_subunits(unit.unit_id, self._second_cutoff_units)


    class StudentRow(object):
        """Aggregates scores statistics."""

        def __init__(self, output, multiplier, first_cutoff_units, second_cutoff_units):
            self._output = output
            self._multiplier = multiplier
            self._first_cutoff_units = first_cutoff_units
            self._second_cutoff_units = second_cutoff_units

        def clears_cutoff(self, score_dict, units):
            t_score = 0
            for u in units:
                unit_name = str(u)
                if score_dict.has_key(unit_name):
                    t_score += (
                        score_dict[unit_name] * self._multiplier[unit_name])
            if t_score > 0:
                if (t_score / len(units)) >= 60:
                    return True
            return False

        def visit(self, student):
            if not student.is_enrolled:
                return
            write_output = False
            cleared_row_info = [student.email, student.user_id]
            score_dict = (
                transforms.loads(student.scores) if student.scores else dict())

            if self.clears_cutoff(score_dict, self._first_cutoff_units):
                cleared_row_info += [True]
                write_output = True
            else:
                cleared_row_info += [False]

            if self.clears_cutoff(score_dict, self._second_cutoff_units):
                cleared_row_info += [True]
                write_output = True
            else:
                cleared_row_info += [False]

            if write_output:
                self._output.writerow(cleared_row_info)


    def run(self):
        """Computes student statistics."""
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(
            output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        head_row = ['email', 'user id', 'Qualified in First', 'Qualified in Second']
        writer.writerow(head_row)

        student_row = self.StudentRow(
            writer, self._unit_to_multiplier, self._first_cutoff_units,
            self._second_cutoff_units)

        mapper = utils.QueryMapper(
            Student.all(), batch_size=500, report_every=1000)

        def map_fn(student):
            student_row.visit(student)

        mapper.run(map_fn)

        filename = 'qualified_%s_%s.csv' % (self._namespace, time.strftime("%d-%m-%Y_%H-%M"))
        settings = self._course.get_environ(self._app_context)
        file = insert_file(filename, '', output, settings)
        output.close()


class DumpStudentProfile(jobs.DurableJob):
    """A job that computes student statistics."""

    def __init__(self, app_context):
        self._namespace = ''
        if app_context:
            self._course = courses.Course(None, app_context=app_context)
            self._settings = self._course.get_environ(app_context)
            self._course_namespace = app_context.get_namespace_name()
        else:
            self._course = None
            self._settings = None
            self._course_namespace = ''
        self._job_name = 'job-%s-%s' % (
            self.__class__.__name__, self._course_namespace)

    class StudentRow(object):
        """Aggregates scores statistics."""

        def __init__(self, output, course_namespace):
            self._output = output
            self._course_namespace = course_namespace

        def visit(self, profile):
            if not profile.enrollment_info:
                return
            enrollment_info = transforms.loads(profile.enrollment_info)
            if (self._course_namespace and self._course_namespace not in
                    enrollment_info.keys()):
                    return
            self._output.writerow([
                profile.email, profile.user_id, profile.nick_name,
                profile.age_group,
                profile.mobile_number,
                profile.country_of_residence, profile.state_of_residence,
                profile.city_of_residence, profile.name_of_college,
                profile.college_roll_no, profile.local_chapter,
                profile.college_id,profile.employer_id,profile.graduation_year,
                profile.profession,profile.employer_name,
                profile.qualification,profile.degree,
                profile.department, profile.study_year,
                profile.designation, profile.motivation, profile.exam_taker])


    def run(self):
        """Computes student statistics."""
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(
            output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
        'email', 'user id', 'name', 'age_group', 'mobile_number',
        'country', 'state', 'city', 'college', 'college_roll_no',
            'local_chapter','college_id','employer_id' ,'graduation year', 'profession', 'employer name',
            'qualification', 'degree','department','study_year','designation','motivation','exam_taker'])
        student_row = self.StudentRow(writer, self._course_namespace)

        mapper = utils.QueryMapper(
            PersonalProfile.all(), batch_size=500, report_every=1000)

        def map_fn(student):
            student_row.visit(student)

        mapper.run(map_fn)

	filename = 'profile_%s_%s.csv' % (self._course_namespace,
			time.strftime("%d-%m-%Y_%H-%M"))
        file = insert_file(filename, '', output, self._settings)
        output.close()

class DumpStudentProfileForSingleCourse(jobs.DurableJob):
    """A job that dumps the profile for single course"""

    def __init__(self, app_context):
        self._namespace = ''
        self._course = courses.Course(None, app_context=app_context)
        self._settings = self._course.get_environ(app_context)
        self._course_namespace = app_context.get_namespace_name()
        self._namespace = self._course_namespace
        self._job_name = 'job-%s-%s' % (
            self.__class__.__name__, self._course_namespace)

    class StudentRow(object):
        """Aggregates scores statistics."""

        def __init__(self, output, course_namespace):
            self._output = output
            self._course_namespace = course_namespace

        def visit(self, student):
            email = student.email
            profile = StudentProfileDAO.get_profile_by_email(email)
            if not profile:
                return
            if not profile.enrollment_info:
                return
            enrollment_info = transforms.loads(profile.enrollment_info)
            if (self._course_namespace and self._course_namespace not in
                    enrollment_info.keys()):
                return
            self._output.writerow([
                profile.email, profile.user_id, profile.nick_name,
                profile.age_group,
                profile.mobile_number,
                profile.country_of_residence, profile.state_of_residence,
                profile.city_of_residence, profile.name_of_college,
                profile.college_roll_no, profile.local_chapter,
                profile.college_id,profile.employer_id,profile.graduation_year,
                profile.profession,profile.employer_name,
                profile.qualification,profile.degree,
                profile.department, profile.study_year,
                profile.designation, profile.motivation, profile.exam_taker])

    def run(self):
        """Computes student statistics."""
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(
            output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
        'email', 'user id', 'name', 'age_group', 'mobile_number',
        'country', 'state', 'city', 'college', 'college_roll_no',
            'local_chapter','college_id','employer_id' ,'graduation year', 'profession', 'employer name',
            'qualification', 'degree','department','study_year','designation','motivation','exam_taker'])
        student_row = self.StudentRow(writer, self._course_namespace)
        namespace_manager.set_namespace(self._course_namespace)
        mapper = utils.QueryMapper(
            Student.all(), batch_size=500, report_every=1000)

        def map_fn(student):
            student_row.visit(student)

        mapper.run(map_fn)

        filename = 'profile_%s_%s.csv' % (self._course_namespace,
            time.strftime("%d-%m-%Y_%H-%M"))
        file = insert_file(filename, '', output, self._settings)
        output.close()


class ReIndexStudentProfile(jobs.DurableJob):
    """A job that computes student statistics."""

    def __init__(self):
        self._namespace = ''
        self._job_name = 'job-%s-%s' % (
            self.__class__.__name__, self._namespace)

    class StudentRow(object):
        """Aggregates scores statistics."""

        def visit(self, profile):
            try:
            	profile.put()
            except Exception as inst:
      		logging.error(type(inst))

    def run(self):
        """Computes student statistics."""
        student_row = self.StudentRow()

        mapper = utils.QueryMapper(
            PersonalProfile.all(), batch_size=500, report_every=1000)

        def map_fn(student):
            student_row.visit(student)
        mapper.run(map_fn)

class ReIndexPersonalProfileMapReduce(jobs.MapReduceJob):
    """A Job that re-indexes PersonalProfile objects"""

    def __init__(self):
        self._job_name = 'job-%s' % self.__class__.__name__
        self._namespace = appengine_config.DEFAULT_NAMESPACE_NAME
        self._course = None
        self._settings = None
        self._course_namespace = self._namespace
        self._app_context = None

    @staticmethod
    def get_description():
        return 'ReIndexPersonalProfileMapReduce'

    @staticmethod
    def entity_class():
        return PersonalProfile

    @staticmethod
    def map(entity):
        try:
            entity.put()
        except Exception as inst:
            logging.error(
                'Failed to save PersonalProfile object %s', str(inst))

class ReIndexCourseListMapReduce(jobs.MapReduceJob):
    """A Job that re-indexes CourseList objects"""

    def __init__(self):
        self._job_name = 'job-%s' % self.__class__.__name__
        self._namespace = appengine_config.DEFAULT_NAMESPACE_NAME
        self._course = None
        self._settings = None
        self._course_namespace = self._namespace
        self._app_context = None

    @staticmethod
    def get_description():
        return 'ReIndexCourseListMapReduce'

    @staticmethod
    def entity_class():
        return course_list.CourseList

    @staticmethod
    def map(entity):
        try:
            app_context = sites._build_app_context_from_course_list_item(entity)
            course = courses.Course(None, app_context=app_context)
	    settings = course.get_environ(app_context)
            course.save_settings(settings)

        except Exception as inst:
            logging.error(
                'Failed to save course_list object %s', str(entity))


class PortExplorerFieldsMapReduce(jobs.MapReduceJob):
    """A Job that re-indexes CourseList objects"""

    def __init__(self):
        self._job_name = 'job-%s' % self.__class__.__name__
        self._namespace = appengine_config.DEFAULT_NAMESPACE_NAME
        self._course = None
        self._settings = None
        self._course_namespace = self._namespace
        self._app_context = None

    @staticmethod
    def get_description():
        return 'PortExplorerFieldsMapReduce'

    @staticmethod
    def entity_class():
        return course_list.CourseList

    @staticmethod
    def map(entity):
        try:
            app_context = sites._build_app_context_from_course_list_item(entity)
            course = courses.Course(None, app_context=app_context)
            settings = course.get_environ(app_context)
            if 'explorer' in settings:
                if 'blurb' in settings['explorer']:
                    settings['course']['explorer_summary'] = (
                        settings['explorer']['blurb'])
                if 'list_in_explorer' in settings['explorer']:
                    settings['course']['show_in_explorer'] = (
                        settings['explorer']['list_in_explorer'])
                if entity.featured:
                    settings['course']['featured'] = True
                elif 'featured' in settings['explorer']:
                    settings['course']['featured'] = (
                        settings['explorer']['featured'])

                course.save_settings(settings)

        except Exception as inst:
            logging.error(
                'Failed to save course_list object %s', str(entity))



class PerCourseJobHandler(BaseHandler):
    """ Download students list and store it on drive."""

    def schedule_site_wide_job(self):
        self.response.write('Course Not Specified\n')

    def get(self):
        namespaces = self.request.get_all('namespace')
        if not namespaces or len(namespaces) == 0:
            if not roles.Roles.is_super_admin():
                self.response.write('Unauthorized\n')
                return
            self.schedule_site_wide_job()
            self.response.write('Launched for all course. \n OK\n')
        else:
            for context in sites.get_all_courses():
                if (namespaces and len(namespaces) > 0 and
                    context.get_namespace_name() not in namespaces and
                    'all' not in namespaces):
                    continue
                if not roles.Roles.is_course_admin(context):
                    self.response.write('Unauthorized\n')
                    return
                self.schedule_job(context)
            self.response.write('Launched for this specific course.\n OK\n')


class GenerateStudentReportHandler(PerCourseJobHandler):
    """ Download students list and store it on drive."""

    def schedule_job(self, context):
        job = ComputeStudentReport(context)
        job.submit()

class GenerateQuestionWiseScoreDumpHandler(PerCourseJobHandler):

    def schedule_job(self, context):
        job = QuestionWiseScoreDump(context)
        job.submit()

class DumpProfilesHandler(PerCourseJobHandler):
    """ Download students list and store it on drive."""

    def schedule_site_wide_job(self):
        job = DumpStudentProfile(None)
        job.submit()

    def schedule_job(self, context):
        job = DumpStudentProfileForSingleCourse(context)
        job.submit()

class DumpQualifiedStudents(PerCourseJobHandler):
    """ Download students list and store it on drive."""

    def schedule_job(self, context):
        job = ComputeQualificationForMains(context)
        job.submit()

class ReIndexStudentProfileHandler(PerCourseJobHandler):
    """ Download students list and store it on drive."""

    def schedule_site_wide_job(self):
        job = ReIndexStudentProfile()
        job.submit()

class ReIndexPersonalProfileMapReduceHandler(BaseHandler):
    """Re Indexes all personal profile objects"""

    def get(self):
        if not roles.Roles.is_super_admin():
            self.error(403)
            self.response.write('Forbidden\n')
            return
        job = ReIndexPersonalProfileMapReduce()
        job.submit()
        self.response.write('OK\n')

class ReIndexCourseListMapReduceHandler(BaseHandler):
    """Re Indexes all Course List objects"""

    def get(self):
        if not roles.Roles.is_super_admin():
            self.error(403)
            self.response.write('Forbidden\n')
            return
        job = ReIndexCourseListMapReduce()
        job.submit()
        self.response.write('OK\n')

class PortExplorerFieldsMapReduceHandler(BaseHandler):
    """Re Indexes all Course List objects"""

    def get(self):
        if not roles.Roles.is_super_admin():
            self.error(403)
            self.response.write('Forbidden\n')
            return
        job = PortExplorerFieldsMapReduce()
        job.submit()
        self.response.write('OK\n')


class SaveCourseSettingsHandler(PerCourseJobHandler):
    """ Download students list and store it on drive."""

    def schedule_job(self, context):
        job = SaveCourseSettings(context)
        job.submit()


class FixSPOCRoleHandler(BaseHandler):
    """Fixes any issues related to the SPoC role"""

    def get(self):
        if not roles.Roles.is_super_admin():
            self.error(403)
            self.response.write('Forbidden\n')
            return

        with Namespace(appengine_config.DEFAULT_NAMESPACE_NAME):
            local_chapters = local_chapter_model.LocalChapterDAO.get_local_chapter_list()
            new_emails = []
            for lc in local_chapters:
                new_emails += lc.spoc_emails
            for role in models.RoleDAO.get_all():
                if role.name == spoc_base.SPOCBase.SPOC_ROLE_NAME:
                    role.dict['users'] = new_emails
                    models.RoleDAO.save(role)
        self.response.write('OK\n')


class ReEnrollToGroupMapReduceHandler(BaseHandler):

    def get(self):
        if not roles.Roles.is_super_admin():
            self.error(403)
            self.response.write('Forbidden\n')
            return

        namespace = self.request.get('namespace')
        if not namespace:
            self.error(400)
            self.response.write('Invalid namespace')
            return

        with Namespace(namespace):
            app_context = sites.get_app_context_for_namespace(namespace)
            if app_context:
                job = ReEnrollToGroupMapReduce(app_context)
                job.submit()
                self.response.write('OK\n')
                return
