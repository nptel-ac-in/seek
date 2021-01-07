from google.cloud import ndb
from common.utils import Namespace
with ndb.Client().context():
    from models.models import Student
    with Namespace("ns_course1"):
        asd = Student.get_by_id("552c1420ac4c45f888005b404ce5ebb1")
        print(asd.scores)
        import pdb; pdb.set_trace()
        print(asd)

