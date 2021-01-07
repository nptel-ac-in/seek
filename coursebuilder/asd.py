existing_user_accounts = {}

for user in UserAccount.query():
    existing_user_accounts[user.key().id()] = user.user_id

user_accounts = []
for x in emails:
    if x not in existing_user_accounts:
        UserAccount(id=x)
result = ndb.put_multi(user_accounts)

for user in UserAccount.query():
    existing_user_accounts[x.key().id()] = x.user_id

for e in emails:
    profile = PersonalProfile(id=existing_user_accounts[e],
                              ...
                              ..)
    student = Student(id=existing_user_accounts[e],
                      ...)
    profiles.append(profile)...


put_multi...
