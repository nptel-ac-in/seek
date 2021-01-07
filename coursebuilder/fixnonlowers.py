from scripts import local_ndb_context
from modules.firebase_auth import models as fbm
from models.odb import ndb

all_user_accounts = fbm.UserAccount.query().fetch()

copies = []

def make_copy(user_account):
    old_id = user_account.key.id()
    user_id = user_account.user_id
    return fbm.UserAccount(
        id=old_id.lower(),
        user_id=user_id)

for x in all_user_accounts:
    # if x.key.id().endswith("student.onlinedegree.iitm.ac.in"):
    if not x.key.id().islower():
        copies.append(make_copy(x))

import pdb; pdb.set_trace()
ndb.put_multi(copies)
