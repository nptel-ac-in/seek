import json
import sys
import logging
import datetime
import uuid

import appengine_config
from models import models
from models import odb
from common import utils
from modules.firebase_auth import models as fb_models

SINGLE = False

client = odb.ndb.Client()

emails = []
# with open('email_list.csv') as f:
#     for count, line in enumerate(f.readlines()[1:], start=1):
#         email = line.split(',')[0].strip()
#         emails.append(email)
emails = open('email_list.csv').read().split('\n')
emails = [e.strip() for e in emails if e.strip()]
emails = [
    [x.strip() for x in y.split(',')]
    for y in emails]

emails = list(set(emails))

if len(emails) == 1:
    SINGLE = True

