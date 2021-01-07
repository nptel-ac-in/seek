import os
from concurrent.futures import ThreadPoolExecutor
from google.cloud import ndb
import sys
from modules.google_service_account import google_service_account
from time import sleep
files = ['21t1_cs1001'] #,'21t1_hs1001','21t1_ma1001','21t1_ma1002']
for file in files:
    group_email = file + '-announce@nptel.iitm.ac.in'
    emails_file = file + '.csv'
    if not emails_file:
        raise Exception("Please provide email file")

    emails = [e.strip() for e in open(emails_file).read().split('\n') if e.strip()]
    # groups = [
    # 'ma1001-discuss@onlinedegree.iitm.ac.in',
    #group_email = ['21t1-cs1001-announce@nptel.iitm.ac.in','21t1-hs1001-announce@nptel.iitm.ac.in','21t1-ma1001-announce@nptel.iitm.ac.in','21t1-ma1002-announce@nptel.iitm.ac.in']
    # 'ma1002-discuss@onlinedegree.iitm.ac.in',
    # 'ma1002-announce@onlinedegree.iitm.ac.in',
    # 'cs1001-discuss@onlinedegree.iitm.ac.in',
    # 'cs1001-announce@onlinedegree.iitm.ac.in',
    # 'hs1001-discuss@onlinedegree.iitm.ac.in',
    # 'hs1001-announce@onlinedegree.iitm.ac.in',
    # print(emails)
    len_emails = len(emails)
    # print(len_emails)

    input("press enter to continue")

    success_emails = {}
    # for group_email in group_emails:
    if os.path.exists(f'success/{group_email}'):
        _ = os.popen(
            f'ls success/{group_email}').read()
        _ = _.replace(' ', '\n')
        _ = _.split('\n')
        success_emails = dict([(key, True) for key in _])


    with ndb.Client().context():
        service = google_service_account.GoogleServiceManager.get_service(
            name='admin', version='directory_v1')
        print(service)
        members = service.members()

        import pdb; pdb.set_trace()
        def add_to_group(user_email, group_email):
            user_email = user_email.lower()
            try:
                data = {
                      "email": user_email,
                      "role": "MEMBER"
                    }
                members.insert(groupKey=group_email, body=data).execute()
                print(f"inserted {user_email} into {group_email}")
            except Exception as e:
                if "already exists" not in str(e):
                    print("Failed", e, user_email, group_email)
                    os.system(f"mkdir -p failed/{group_email}")
                    os.system(f"touch failed/{group_email}/{user_email}")
                    sleep(1)
                    return
            os.system(f"mkdir -p success/{group_email}")
            os.system(f"touch success/{group_email}/{user_email}")

        for i, user_email in enumerate(emails):
            if success_emails.get(user_email, False):
                os.system(f"mkdir -p skipped/{group_email}")
                os.system(f"touch skipped/{group_email}/{user_email}")
                continue
            add_to_group(user_email, group_email)
            print(f'{i+1} out of {len_emails}')
