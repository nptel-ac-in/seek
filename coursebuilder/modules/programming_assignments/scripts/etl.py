# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Examples of custom extract-transform-load jobs.

Custom jobs are run via tools/etl/etl.py. You must do environment setup before
etl.py can be invoked; see its module docstring for details.

See tools/etl/etl_lib.py for documentation on writing Job subclasses.
"""

__author__ = [
    'abhinavk@google.com',
]

import os
import sys
from controllers import sites
from models import courses
from models import models
from models import transforms
from modules.prog_assignments import prog_assignment
from tools.etl import etl_lib
from google.appengine.api import namespace_manager


def iter_all(query, batch_size=1000):
    """Yields query results iterator. Proven method for large datasets."""
    prev_cursor = None
    any_records = True
    while any_records:
        any_records = False
        query = query.with_cursor(prev_cursor)
        print 'starting query'
        for entity in query.fetch(limit=batch_size):
            any_records = True
            yield entity
        prev_cursor = query.cursor()
        print 'At cursor ' + prev_cursor


class DownloadProgrammingSubmissions(etl_lib.Job):
    """Example job that reads student emails from remote server to local file.

    Usage:

    etl.py run tools.etl.examples.DownloadProgrammingSubmissions /course myapp \
        server.appspot.com

    Arguments to etl.py are documented in tools/etl/etl.py. You must do some
    environment configuration (setting up imports, mostly) before you can run
    etl.py; see the tools/etl/etl.py module-level docstring for details.
    """

    def _configure_parser(self):
        # Add custom arguments by manipulating self.parser.
        self.parser.add_argument(
            'path', default='.',
            help='Absolute path to save output to', type=str)
        self.parser.add_argument(
            '--batch_size', default=20,
            help='Number of students to download in each batch', type=int)

    def main(self):
        # By the time main() is invoked, arguments are parsed and available as
        # self.args. If you need more complicated argument validation than
        # argparse gives you, do it here:
        if self.args.batch_size < 1:
            sys.exit('--batch size must be positive')
        if not os.path.isdir(self.args.path):
            sys.exit('Cannot download to %s; Its not a directory' % self.args.path)

        # Arguments passed to etl.py are also parsed and available as
        # self.etl_args. Here we use them to figure out the requested course's
        # namespace.
        namespace = etl_lib.get_context(
            self.etl_args.course_url_prefix).get_namespace_name()

        file_dict = dict()
        # Because our models are namespaced, we need to change to the requested
        # course's namespace before doing datastore reads or we won't find its
        # data. Get the current namespace so we can change back when we're done.
        old_namespace = namespace_manager.get_namespace()
        try:
            namespace_manager.set_namespace(namespace)
            # For this example, we'll only process the first 1000 results. Can
            # do a keys_only query because the student's email is key.name().
            for sub in  iter_all(student_work.Submission.all()):
                print sub.key().name()
                unit_id = sub.unit_id
                if unit_id not in file_dict:
                    f = open(self.args.path + '/' + namespace + '-' + str(unit_id), 'w')
                    file_dict[unit_id] = f
                data = dict()
                data['unit_id'] = unit_id
                data['user'] = sub.key().name()
                data['code'] = sub.contents
                file_dict[unit_id].write(transforms.dumps(data) + '\n')
        finally:
            # The current namespace is global state. We must change it back to
            # the old value no matter what to prevent corrupting datastore
            # operations that run after us.
            namespace_manager.set_namespace(old_namespace)


class DownloadProgrammingQuestions(etl_lib.Job):
    """Example job that reads student emails from remote server to local file.

    Usage:

    etl.py run tools.etl.examples.DownloadProgrammingQuestions /course myapp \
        server.appspot.com

    Arguments to etl.py are documented in tools/etl/etl.py. You must do some
    environment configuration (setting up imports, mostly) before you can run
    etl.py; see the tools/etl/etl.py module-level docstring for details.
    """

    def _configure_parser(self):
        # Add custom arguments by manipulating self.parser.
        self.parser.add_argument(
            'path', default='.',
            help='Absolute path to save output to', type=str)
        self.parser.add_argument(
            '--batch_size', default=20,
            help='Number of students to download in each batch', type=int)

    def main(self):
        # By the time main() is invoked, arguments are parsed and available as
        # self.args. If you need more complicated argument validation than
        # argparse gives you, do it here:
        if self.args.batch_size < 1:
            sys.exit('--batch size must be positive')
        if not os.path.isdir(self.args.path):
            sys.exit('Cannot download to %s; Its not a directory' % self.args.path)

        # Arguments passed to etl.py are also parsed and available as
        # self.etl_args. Here we use them to figure out the requested course's
        # namespace.
        namespace = etl_lib.get_context(
            self.etl_args.course_url_prefix).get_namespace_name()

        # Because our models are namespaced, we need to change to the requested
        # course's namespace before doing datastore reads or we won't find its
        # data. Get the current namespace so we can change back when we're done.
        old_namespace = namespace_manager.get_namespace()
        try:
            namespace_manager.set_namespace(namespace)

            app_context = sites.get_app_context_for_namespace(namespace)
            course = courses.Course(None, app_context=app_context)
            if not course:
                return

            units = course.get_units()
            for unit in units:
                if unit.type != 'PA':
                    continue
                content = prog_assignment.ProgAssignmentBaseHandler.get_content(
                    course, unit)
                f = open(self.args.path + '/' + namespace + '-problem-' + str(unit.unit_id), 'w')
                f.write(transforms.dumps(content))

        finally:
            # The current namespace is global state. We must change it back to
            # the old value no matter what to prevent corrupting datastore
            # operations that run after us.
            namespace_manager.set_namespace(old_namespace)
