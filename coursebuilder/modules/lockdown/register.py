from models import custom_modules
from modules.admin import admin
from modules.lockdown import base
from modules.lockdown import unlock

custom_module = None


def register_module(*args, **kwargs):
    global custom_module

    admin.BaseAdminHandler.add_menu_item(
        'analytics', base.LockdownBase.UNLOCK_ACTION, 'Unlock',
        action=base.LockdownBase.UNLOCK_ACTION, sub_group_name='advanced')

    admin.GlobalAdminHandler.add_custom_get_action(base.LockdownBase.UNLOCK_ACTION,unlock.UnlockDashboardHandler.display_html)
    admin.GlobalAdminHandler.add_custom_post_action(base.LockdownBase.UNLOCK_ACTION,unlock.UnlockDashboardHandler.unlock_assessment)


    custom_module = custom_modules.Module(
        'Lockdown',
        'Locks assessments once they go public.',
        [], [])

    return custom_module
