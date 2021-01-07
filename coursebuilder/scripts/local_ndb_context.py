"""enters an ndb context for local testing using the python shell"""
from models.odb import ndb
client = ndb.Client()
context = client.context()
entered = context.__enter__()
