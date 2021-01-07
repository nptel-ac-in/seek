from models import odb
from models import course_list
from controllers import sites
from models import courses
from controllers import utils
from modules.dashboard import utils as dutils
with odb.ndb.Client().context():
    course = course_list.CourseList.query().get()
    assert course
    app_context = sites._build_app_context_from_course_list_item(course)
    # all_files = dutils.list_files(app_context, '/assets/img/',
    # all_files = dutils.list_files(app_context, '/assets/',
    #                               merge_local_files=True)
    # import pdb; pdb.set_trace()
    # print(all_files)
    course = courses.Course.get(app_context)
    print(course._model.children_order)
