# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: request.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import common_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='request.proto',
  package='nsjail_programming_server',
  serialized_pb=_b('\n\rrequest.proto\x12\x19nsjail_programming_server\x1a\x0c\x63ommon.proto\"%\n\x14ServerDetailsMessage\x12\r\n\x05token\x18\x01 \x02(\t\"\xa2\x05\n\x0b\x43odeRequest\x12\x39\n\x04\x63ode\x18\x01 \x02(\x0b\x32+.nsjail_programming_server.CodeRequest.Code\x12\x10\n\x08language\x18\x02 \x02(\t\x12V\n\x13\x63ompilation_options\x18\x03 \x01(\x0b\x32\x39.nsjail_programming_server.CodeRequest.CompilationOptions\x12N\n\x0fruntime_options\x18\x04 \x01(\x0b\x32\x35.nsjail_programming_server.CodeRequest.RuntimeOptions\x12\x42\n\ttestcases\x18\x05 \x03(\x0b\x32/.nsjail_programming_server.CodeRequest.TestCase\x1a\x44\n\x04\x43ode\x12\x11\n\tfull_code\x18\x01 \x02(\t\x12\x10\n\x08\x66ilename\x18\x02 \x01(\t\x12\x17\n\x0f\x62inary_filename\x18\x03 \x01(\t\x1al\n\x12\x43ompilationOptions\x12\x42\n\x0fresource_limits\x18\x01 \x01(\x0b\x32).nsjail_programming_server.ResourceLimits\x12\x12\n\nextra_args\x18\x02 \x03(\t\x1ah\n\x0eRuntimeOptions\x12\x42\n\x0fresource_limits\x18\x01 \x01(\x0b\x32).nsjail_programming_server.ResourceLimits\x12\x12\n\nextra_args\x18\x04 \x03(\t\x1a<\n\x08TestCase\x12\r\n\x05input\x18\x01 \x02(\t\x12\x0e\n\x06output\x18\x02 \x02(\t\x12\x11\n\tdirectory\x18\x03 \x01(\t\"\xb2\x05\n\tCodeReply\x12\x43\n\x0eoverall_status\x18\x01 \x02(\x0e\x32+.nsjail_programming_server.CodeReply.Status\x12R\n\x12\x63ompilation_result\x18\x02 \x02(\x0b\x32\x36.nsjail_programming_server.CodeReply.CompilationResult\x12N\n\x11test_case_results\x18\x03 \x03(\x0b\x32\x33.nsjail_programming_server.CodeReply.TestCaseResult\x1a\x86\x01\n\x11\x43ompilationResult\x12;\n\x06status\x18\x01 \x02(\x0e\x32+.nsjail_programming_server.CodeReply.Status\x12\x0e\n\x06output\x18\x02 \x01(\t\x12\r\n\x05\x65rror\x18\x03 \x01(\t\x12\x15\n\rnsjail_output\x18\x04 \x01(\t\x1a\x8a\x01\n\x0eTestCaseResult\x12;\n\x06status\x18\x01 \x02(\x0e\x32+.nsjail_programming_server.CodeReply.Status\x12\x15\n\ractual_output\x18\x02 \x01(\t\x12\r\n\x05\x65rror\x18\x04 \x01(\t\x12\x15\n\rnsjail_output\x18\x05 \x01(\t\"\xa5\x01\n\x06Status\x12\x06\n\x02OK\x10\x00\x12\x15\n\x11\x43OMPILATION_ERROR\x10\x01\x12\x10\n\x0cWRONG_ANSWER\x10\x02\x12\x17\n\x13TIME_LIMIT_EXCEEDED\x10\x03\x12\x11\n\rRUNTIME_ERROR\x10\x04\x12\x19\n\x15MEMORY_LIMIT_EXCEEDED\x10\x05\x12\x16\n\x12PRESENTATION_ERROR\x10\x06\x12\x0b\n\x07NOT_RUN\x10\x07\",\n\x12ServerDetailsReply\x12\x16\n\x0eserver_details\x18\x01 \x02(\t')
  ,
  dependencies=[common_pb2.DESCRIPTOR,])
_sym_db.RegisterFileDescriptor(DESCRIPTOR)



_CODEREPLY_STATUS = _descriptor.EnumDescriptor(
  name='Status',
  full_name='nsjail_programming_server.CodeReply.Status',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='OK', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='COMPILATION_ERROR', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='WRONG_ANSWER', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='TIME_LIMIT_EXCEEDED', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='RUNTIME_ERROR', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MEMORY_LIMIT_EXCEEDED', index=5, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='PRESENTATION_ERROR', index=6, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='NOT_RUN', index=7, number=7,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=1300,
  serialized_end=1465,
)
_sym_db.RegisterEnumDescriptor(_CODEREPLY_STATUS)


_SERVERDETAILSMESSAGE = _descriptor.Descriptor(
  name='ServerDetailsMessage',
  full_name='nsjail_programming_server.ServerDetailsMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='token', full_name='nsjail_programming_server.ServerDetailsMessage.token', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=58,
  serialized_end=95,
)


_CODEREQUEST_CODE = _descriptor.Descriptor(
  name='Code',
  full_name='nsjail_programming_server.CodeRequest.Code',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='full_code', full_name='nsjail_programming_server.CodeRequest.Code.full_code', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='filename', full_name='nsjail_programming_server.CodeRequest.Code.filename', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='binary_filename', full_name='nsjail_programming_server.CodeRequest.Code.binary_filename', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=426,
  serialized_end=494,
)

_CODEREQUEST_COMPILATIONOPTIONS = _descriptor.Descriptor(
  name='CompilationOptions',
  full_name='nsjail_programming_server.CodeRequest.CompilationOptions',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='resource_limits', full_name='nsjail_programming_server.CodeRequest.CompilationOptions.resource_limits', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='extra_args', full_name='nsjail_programming_server.CodeRequest.CompilationOptions.extra_args', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=496,
  serialized_end=604,
)

_CODEREQUEST_RUNTIMEOPTIONS = _descriptor.Descriptor(
  name='RuntimeOptions',
  full_name='nsjail_programming_server.CodeRequest.RuntimeOptions',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='resource_limits', full_name='nsjail_programming_server.CodeRequest.RuntimeOptions.resource_limits', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='extra_args', full_name='nsjail_programming_server.CodeRequest.RuntimeOptions.extra_args', index=1,
      number=4, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=606,
  serialized_end=710,
)

_CODEREQUEST_TESTCASE = _descriptor.Descriptor(
  name='TestCase',
  full_name='nsjail_programming_server.CodeRequest.TestCase',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='input', full_name='nsjail_programming_server.CodeRequest.TestCase.input', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='output', full_name='nsjail_programming_server.CodeRequest.TestCase.output', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='directory', full_name='nsjail_programming_server.CodeRequest.TestCase.directory', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=712,
  serialized_end=772,
)

_CODEREQUEST = _descriptor.Descriptor(
  name='CodeRequest',
  full_name='nsjail_programming_server.CodeRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='code', full_name='nsjail_programming_server.CodeRequest.code', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='language', full_name='nsjail_programming_server.CodeRequest.language', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='compilation_options', full_name='nsjail_programming_server.CodeRequest.compilation_options', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='runtime_options', full_name='nsjail_programming_server.CodeRequest.runtime_options', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='testcases', full_name='nsjail_programming_server.CodeRequest.testcases', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CODEREQUEST_CODE, _CODEREQUEST_COMPILATIONOPTIONS, _CODEREQUEST_RUNTIMEOPTIONS, _CODEREQUEST_TESTCASE, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=98,
  serialized_end=772,
)


_CODEREPLY_COMPILATIONRESULT = _descriptor.Descriptor(
  name='CompilationResult',
  full_name='nsjail_programming_server.CodeReply.CompilationResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='status', full_name='nsjail_programming_server.CodeReply.CompilationResult.status', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='output', full_name='nsjail_programming_server.CodeReply.CompilationResult.output', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='error', full_name='nsjail_programming_server.CodeReply.CompilationResult.error', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='nsjail_output', full_name='nsjail_programming_server.CodeReply.CompilationResult.nsjail_output', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1022,
  serialized_end=1156,
)

_CODEREPLY_TESTCASERESULT = _descriptor.Descriptor(
  name='TestCaseResult',
  full_name='nsjail_programming_server.CodeReply.TestCaseResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='status', full_name='nsjail_programming_server.CodeReply.TestCaseResult.status', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='actual_output', full_name='nsjail_programming_server.CodeReply.TestCaseResult.actual_output', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='error', full_name='nsjail_programming_server.CodeReply.TestCaseResult.error', index=2,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='nsjail_output', full_name='nsjail_programming_server.CodeReply.TestCaseResult.nsjail_output', index=3,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1159,
  serialized_end=1297,
)

_CODEREPLY = _descriptor.Descriptor(
  name='CodeReply',
  full_name='nsjail_programming_server.CodeReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='overall_status', full_name='nsjail_programming_server.CodeReply.overall_status', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='compilation_result', full_name='nsjail_programming_server.CodeReply.compilation_result', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='test_case_results', full_name='nsjail_programming_server.CodeReply.test_case_results', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CODEREPLY_COMPILATIONRESULT, _CODEREPLY_TESTCASERESULT, ],
  enum_types=[
    _CODEREPLY_STATUS,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=775,
  serialized_end=1465,
)


_SERVERDETAILSREPLY = _descriptor.Descriptor(
  name='ServerDetailsReply',
  full_name='nsjail_programming_server.ServerDetailsReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='server_details', full_name='nsjail_programming_server.ServerDetailsReply.server_details', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1467,
  serialized_end=1511,
)

_CODEREQUEST_CODE.containing_type = _CODEREQUEST
_CODEREQUEST_COMPILATIONOPTIONS.fields_by_name['resource_limits'].message_type = common_pb2._RESOURCELIMITS
_CODEREQUEST_COMPILATIONOPTIONS.containing_type = _CODEREQUEST
_CODEREQUEST_RUNTIMEOPTIONS.fields_by_name['resource_limits'].message_type = common_pb2._RESOURCELIMITS
_CODEREQUEST_RUNTIMEOPTIONS.containing_type = _CODEREQUEST
_CODEREQUEST_TESTCASE.containing_type = _CODEREQUEST
_CODEREQUEST.fields_by_name['code'].message_type = _CODEREQUEST_CODE
_CODEREQUEST.fields_by_name['compilation_options'].message_type = _CODEREQUEST_COMPILATIONOPTIONS
_CODEREQUEST.fields_by_name['runtime_options'].message_type = _CODEREQUEST_RUNTIMEOPTIONS
_CODEREQUEST.fields_by_name['testcases'].message_type = _CODEREQUEST_TESTCASE
_CODEREPLY_COMPILATIONRESULT.fields_by_name['status'].enum_type = _CODEREPLY_STATUS
_CODEREPLY_COMPILATIONRESULT.containing_type = _CODEREPLY
_CODEREPLY_TESTCASERESULT.fields_by_name['status'].enum_type = _CODEREPLY_STATUS
_CODEREPLY_TESTCASERESULT.containing_type = _CODEREPLY
_CODEREPLY.fields_by_name['overall_status'].enum_type = _CODEREPLY_STATUS
_CODEREPLY.fields_by_name['compilation_result'].message_type = _CODEREPLY_COMPILATIONRESULT
_CODEREPLY.fields_by_name['test_case_results'].message_type = _CODEREPLY_TESTCASERESULT
_CODEREPLY_STATUS.containing_type = _CODEREPLY
DESCRIPTOR.message_types_by_name['ServerDetailsMessage'] = _SERVERDETAILSMESSAGE
DESCRIPTOR.message_types_by_name['CodeRequest'] = _CODEREQUEST
DESCRIPTOR.message_types_by_name['CodeReply'] = _CODEREPLY
DESCRIPTOR.message_types_by_name['ServerDetailsReply'] = _SERVERDETAILSREPLY

ServerDetailsMessage = _reflection.GeneratedProtocolMessageType('ServerDetailsMessage', (_message.Message,), dict(
  DESCRIPTOR = _SERVERDETAILSMESSAGE,
  __module__ = 'request_pb2'
  # @@protoc_insertion_point(class_scope:nsjail_programming_server.ServerDetailsMessage)
  ))
_sym_db.RegisterMessage(ServerDetailsMessage)

CodeRequest = _reflection.GeneratedProtocolMessageType('CodeRequest', (_message.Message,), dict(

  Code = _reflection.GeneratedProtocolMessageType('Code', (_message.Message,), dict(
    DESCRIPTOR = _CODEREQUEST_CODE,
    __module__ = 'request_pb2'
    # @@protoc_insertion_point(class_scope:nsjail_programming_server.CodeRequest.Code)
    ))
  ,

  CompilationOptions = _reflection.GeneratedProtocolMessageType('CompilationOptions', (_message.Message,), dict(
    DESCRIPTOR = _CODEREQUEST_COMPILATIONOPTIONS,
    __module__ = 'request_pb2'
    # @@protoc_insertion_point(class_scope:nsjail_programming_server.CodeRequest.CompilationOptions)
    ))
  ,

  RuntimeOptions = _reflection.GeneratedProtocolMessageType('RuntimeOptions', (_message.Message,), dict(
    DESCRIPTOR = _CODEREQUEST_RUNTIMEOPTIONS,
    __module__ = 'request_pb2'
    # @@protoc_insertion_point(class_scope:nsjail_programming_server.CodeRequest.RuntimeOptions)
    ))
  ,

  TestCase = _reflection.GeneratedProtocolMessageType('TestCase', (_message.Message,), dict(
    DESCRIPTOR = _CODEREQUEST_TESTCASE,
    __module__ = 'request_pb2'
    # @@protoc_insertion_point(class_scope:nsjail_programming_server.CodeRequest.TestCase)
    ))
  ,
  DESCRIPTOR = _CODEREQUEST,
  __module__ = 'request_pb2'
  # @@protoc_insertion_point(class_scope:nsjail_programming_server.CodeRequest)
  ))
_sym_db.RegisterMessage(CodeRequest)
_sym_db.RegisterMessage(CodeRequest.Code)
_sym_db.RegisterMessage(CodeRequest.CompilationOptions)
_sym_db.RegisterMessage(CodeRequest.RuntimeOptions)
_sym_db.RegisterMessage(CodeRequest.TestCase)

CodeReply = _reflection.GeneratedProtocolMessageType('CodeReply', (_message.Message,), dict(

  CompilationResult = _reflection.GeneratedProtocolMessageType('CompilationResult', (_message.Message,), dict(
    DESCRIPTOR = _CODEREPLY_COMPILATIONRESULT,
    __module__ = 'request_pb2'
    # @@protoc_insertion_point(class_scope:nsjail_programming_server.CodeReply.CompilationResult)
    ))
  ,

  TestCaseResult = _reflection.GeneratedProtocolMessageType('TestCaseResult', (_message.Message,), dict(
    DESCRIPTOR = _CODEREPLY_TESTCASERESULT,
    __module__ = 'request_pb2'
    # @@protoc_insertion_point(class_scope:nsjail_programming_server.CodeReply.TestCaseResult)
    ))
  ,
  DESCRIPTOR = _CODEREPLY,
  __module__ = 'request_pb2'
  # @@protoc_insertion_point(class_scope:nsjail_programming_server.CodeReply)
  ))
_sym_db.RegisterMessage(CodeReply)
_sym_db.RegisterMessage(CodeReply.CompilationResult)
_sym_db.RegisterMessage(CodeReply.TestCaseResult)

ServerDetailsReply = _reflection.GeneratedProtocolMessageType('ServerDetailsReply', (_message.Message,), dict(
  DESCRIPTOR = _SERVERDETAILSREPLY,
  __module__ = 'request_pb2'
  # @@protoc_insertion_point(class_scope:nsjail_programming_server.ServerDetailsReply)
  ))
_sym_db.RegisterMessage(ServerDetailsReply)


# @@protoc_insertion_point(module_scope)