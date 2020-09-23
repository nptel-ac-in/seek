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

"""Methods to register Scoring module.."""

__author__ = 'Thejesh GN (tgn@google.com)'


from models import custom_modules
from modules.dashboard import dashboard
from modules.dashboard import tabs
from modules.scoring import base
from modules.scoring import scorer
from modules.scoring import dashboard as scoring_dashboard

# Module registration
custom_module = None

def register_module():
    """Registers this module in the registry."""

    namespaced_routes = []
    tabs.Registry.register(
        base.ScoringBase.DASHBOARD_NAV,
        base.ScoringBase.DASHBOARD_RESCORING_TAB,
        'Objectective Assessement',
        scoring_dashboard.ScoringDashboardHandler)

    dashboard.DashboardHandler.add_custom_get_action(
        base.ScoringBase.DASHBOARD_NAV, None)

    dashboard.DashboardHandler.add_nav_mapping(
        base.ScoringBase.DASHBOARD_NAV, base.ScoringBase.NAME)

    dashboard.DashboardHandler.add_custom_post_action(
        base.ScoringBase.RESCORE_OBJ_ASSESSMENT_ACTION,
        scoring_dashboard.ScoringDashboardHandler.confirm_rescore_page)
    dashboard.DashboardHandler.add_custom_post_action(
        base.ScoringBase.RESCORE_OBJ_ASSESSMENT_CONFIRMED_ACTION,
        scoring_dashboard.ScoringDashboardHandler.rescore_assignment)

    global custom_module
    custom_module = custom_modules.Module(
        base.ScoringBase.NAME,
        'Provides Scoring support',
        [], namespaced_routes)
    return custom_module
