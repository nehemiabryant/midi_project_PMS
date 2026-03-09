from functools import wraps
from flask import session, redirect, url_for
from common.midiconnectserver.midilog import Logger
# from application.models.app_log_model import AppLogModel

Log = Logger()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user') or not session.get('role'):
            return redirect(url_for('owh.logout'))
        return f(*args, **kwargs)
    return decorated_function

# def log_page_access(kd_menu):
#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             try:
#                 app_log = AppLogModel(kd_menu=kd_menu)
#                 result = app_log.insert_app_log()
#                 if result.get('status') == False:
#                     Log.error(f'{kd_menu} | Failed to log page | Error: {result.get("msg")}')
#             except Exception as e:
#                 Log.error(f'{kd_menu} | Failed to log page | Exception: {str(e)}')
#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator