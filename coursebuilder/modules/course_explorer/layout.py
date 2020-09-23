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

"""Layout."""

__author__ = 'Abhinav Khandelwal (abhinavk@google.com)'


import appengine_config

import yaml

from common.utils import Namespace
from models import transforms
from models import entities
from models.models import MemcacheManager

from google.appengine.ext import db

class ExplorerLayout(entities.BaseEntity):
    """Course categories."""

    top_text = db.TextProperty(indexed=False)
    right_video_id = db.StringProperty(indexed=False)
    category_order = db.TextProperty(indexed=False)


class ExplorerLayoutDTO(object):
    """DTO for ExplorerLayout."""

    def __init__(self, layout=None):
        self.top_text = None
        self.right_video_id = None
        self.category_order = []
        if layout:
            self.top_text = layout.top_text
            self.right_video_id = layout.right_video_id
            self.category_order = yaml.safe_load(layout.category_order) if layout.category_order else []


class ExplorerLayoutDAO(object):
    """All access and mutation methods for ExplorerLayout."""

    TARGET_NAMESPACE = appengine_config.DEFAULT_NAMESPACE_NAME
    KEY = 'exp_layout'

    @classmethod
    def _memcache_key(cls):
        """Makes a memcache key from primary key."""
        return 'entity:explorer-layout'


    @classmethod
    def get_layout(cls):
        with Namespace(cls.TARGET_NAMESPACE):
            c = MemcacheManager.get(
                cls._memcache_key(), namespace=cls.TARGET_NAMESPACE)
            if c:
                return ExplorerLayoutDTO(c)

            c = ExplorerLayout.get_by_key_name(cls.KEY)
            if c:
                MemcacheManager.set(
		    cls._memcache_key(), c, namespace=cls.TARGET_NAMESPACE)
                return ExplorerLayoutDTO(c)
            else:
                return ExplorerLayoutDTO(None)

    @classmethod
    def update_layout(cls, top_text=None, right_video_id=None, category_order=None):
        with Namespace(cls.TARGET_NAMESPACE):
            c = ExplorerLayout.get_by_key_name(cls.KEY)
            if not c:
                c = ExplorerLayout(key_name=cls.KEY)

            if top_text is not None:
                c.top_text = top_text
            if right_video_id is not None:
                c.right_video_id = right_video_id
            if category_order is not None:
                c.category_order = yaml.safe_dump(category_order)
            c.put()
            MemcacheManager.set(
	        cls._memcache_key(), c, namespace=cls.TARGET_NAMESPACE)
