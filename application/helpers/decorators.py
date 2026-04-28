from functools import wraps
from flask import session, redirect, url_for, jsonify, flash, request
from common.midiconnectserver.midilog import Logger

Log = Logger()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user') or not session.get('role'):
            return redirect(url_for('owh_auth.logout'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('role', {})
        permissions = role.get('permissions', [])
        if 'manage_roles' not in permissions:
            return jsonify({
                'error': 'forbidden',
                'details': 'Akses ditolak. Diperlukan permission manage_roles.'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def bypass_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = session.get('role', {})
        permissions = role.get('permissions', [])
        if 'bypass' not in permissions:
            flash('Akses ditolak. Anda tidak memiliki permission.', 'error')
            return redirect(url_for('owh_dashboard.dashboard_menu'))
        return f(*args, **kwargs)
    return decorated_function

def ajax_required(f):
    """
    Decorator to protect API endpoints from direct browser access.
    Requires the X-Requested-With: XMLHttpRequest header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            # Return a clean JSON error with a 403 Forbidden HTTP status code
            return jsonify({
                'status': False, 
                'msg': 'Forbidden: Direct access to this API is not allowed.'
            }), 403
            
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