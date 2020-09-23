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
import urlparse
import StringIO
import time

from apiclient import errors
from apiclient.http import MediaIoBaseUpload

from mapreduce import context

from common import csv_unicode
from common import safe_dom
from controllers import sites
from controllers.utils import ApplicationHandler
from controllers.utils import BaseHandler
from controllers.utils import HUMAN_READABLE_TIME_FORMAT
import jinja2
from models import courses
from models import jobs
from models import roles
from models import transforms
from models import utils
from models import data_sources
from models import analytics
from modules.google_service_account import google_service_account
from modules.nptel import settings

from models.models import PersonalProfile
from models.models import Student
from models.models import StudentProfileDAO
from models.course_list import CourseListDAO


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
            entity_dump = transforms.dumps(transforms.entity_to_dict(entity))
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
                        'college','college_roll_no','local_chapter','college_id',
                        'graduation year','profession','employer name'])
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
            row.append(person_profile_dict['graduation_year'])
            row.append(person_profile_dict['profession'])
            row.append(person_profile_dict['employer_name'])
            writer.writerow(row)

        filename = 'profile_%s_%s.csv' % (key,time.strftime("%d-%m-%Y_%H-%M"))
        settings = None

        app_context = sites.get_course_index().get_app_context_for_namespace(key)
        c = courses.Course(None, app_context=app_context)
        settings = c.get_environ(app_context)

        insert_file(filename, '', output, settings)
        output.close()


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


class PerCourseCourseDurableJob(jobs.DurableJob):
    def __init__(self, app_context):
        super(PerCourseCourseDurableJob, self).__init__(app_context)

    @property
    def _course(self):
        return courses.Course(None, app_context=self._app_context)


class ComputeStudentReport(PerCourseCourseDurableJob):
    """A job that computes student statistics."""

    def __init__(self, app_context):
        super(ComputeStudentReport, self).__init__(app_context)
        self._app_context = app_context
        self._unit_id_to_title_list = []
        self._update_units()

    def _update_units(self):
        for unit in self._course.get_units():
            if unit.scored():
                self._unit_id_to_title_list.append((unit.unit_id, unit.title))
        env = courses.Course.get_environ(self._app_context)
        if env.has_key('deleted_assessment_options'):
            deleted_assesments = env['deleted_assessment_options']
            if deleted_assesments.has_key('items'):
                for deleted_assesment in deleted_assesments['items']:
                    self._unit_id_to_title_list.append(
                        (int(deleted_assesment['deleted_assesment_id']),
                        deleted_assesment['deleted_assesment_name'])
                        )

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
                profile.college_id,profile.graduation_year,
                profile.profession,profile.employer_name])

    def run(self):
        """Computes student statistics."""
        output = StringIO.StringIO()
        writer = csv_unicode.UnicodeWriter(
            output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
	    'email', 'user id', 'name', 'age_group', 'mobile_number',
	    'country', 'state', 'city', 'college', 'college_roll_no',
            'local_chapter','college_id' ,'graduation year', 'profession', 'employer name'])
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
        self.response.write('OK\n')


class GenerateStudentReportHandler(PerCourseJobHandler):
    """ Download students list and store it on drive."""

    def schedule_job(self, context):
        job = ComputeStudentReport(context)
        job.submit()

class DumpProfilesHandler(PerCourseJobHandler):
    """ Download students list and store it on drive."""

    def schedule_site_wide_job(self):
        job = DumpStudentProfile(None)
        job.submit()

    def schedule_job(self, context):
        job = DumpStudentProfile(context)
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


class SaveCourseSettingsHandler(PerCourseJobHandler):
    """ Download students list and store it on drive."""

    def schedule_job(self, context):
        job = SaveCourseSettings(context)
        job.submit()
