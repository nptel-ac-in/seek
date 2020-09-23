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

"""Classes and methods to serve Programming Assignments."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


from models import transforms


class Status(object):
    # Do not change values. Because this effects whats stored in db.
    OK = 1
    BACKEND_ERROR = 2
    COMPILATION_ERROR = 3
    OTHER = 4

class TestCaseStatus(object):
    DEFAULT_VALUES = {
        'passed': False,
        'reason': '',
        'output': '',
        'expected_output': '',
    }
    def __init__(self):
        self.passed = False
        self.reason = ''
        self.output = ''
        self.expected_output = ''

    def to_dict(self):
        return transforms.instance_to_dict(self)

    @classmethod
    def from_dict(cls, adict):
        test_case_status = cls()
        transforms.dict_to_instance(
            adict, test_case_status, defaults=cls.DEFAULT_VALUES)
        return test_case_status

class ProgramEvaluationResult(object):
    def __init__(self):
        self.status = Status.OK
        self.reason = ''
        self.score = 0
        self.compilation_errors = []
        self.test_case_results = []
        self.num_test_evaluated = 0
        self.num_test_passed = 0
        self.summary = ''

    def set_status(self, status, reason=None):
        self.status = status
        self.reason = reason

    def serialize(self):
        adict = dict()
        adict['status'] = self.status
        adict['reason'] = self.reason
        adict['compilation_errors'] = transforms.dumps(self.compilation_errors)
        adict['num_test_evaluated'] = self.num_test_evaluated
        adict['num_test_passed'] = self.num_test_passed
        adict['summary'] = self.summary
        adict['score'] = self.score
        adict['test_case_results'] = [
            a.to_dict() for a in self.test_case_results]
        return transforms.dumps(adict)

    @classmethod
    def deserialize(cls, serialized_str):
        result = cls()
        adict = transforms.loads(serialized_str)
        for key, value in adict.items():
            if 'test_case_results' == key:
                result.test_case_results = [
                    TestCaseStatus.from_dict(a) for a in value]
            elif 'compilation_errors' == key:
                result.compilation_errors = transforms.loads(value)
            elif hasattr(result, key):
                setattr(result, key, value)
        return result
