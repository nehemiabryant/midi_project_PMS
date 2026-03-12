from flask import Blueprint, jsonify, request
from ..transactions import role_transaction, karyawan_transaction
from ..helpers.decorators import login_required, super_admin_required

role_mgmt_bp = Blueprint('role_mgmt', __name__)


# ---------------------------------------------------------------------------
# sr_ms_app_role — CRUD Roles
# ---------------------------------------------------------------------------

@role_mgmt_bp.route('/roles', methods=['GET'])
@login_required
@super_admin_required
def list_roles():
    result = role_transaction.get_all_roles_trx()
    if not result.get('status'):
        return jsonify({'error': 'server_error', 'details': result.get('msg')}), 500
    return jsonify({'data': result.get('data')}), 200


@role_mgmt_bp.route('/roles', methods=['POST'])
@login_required
@super_admin_required
def create_role():
    data = request.get_json(silent=True)
    if not data or not data.get('approle_name'):
        return jsonify({'error': 'bad_request', 'details': 'approle_name is required'}), 400

    approle_name = data['approle_name'].strip()
    if not approle_name:
        return jsonify({'error': 'bad_request', 'details': 'approle_name cannot be empty'}), 400

    result = role_transaction.create_role_trx(approle_name)
    if not result.get('status'):
        return jsonify({'error': 'server_error', 'details': result.get('msg')}), 500

    return jsonify({'data': result.get('data'), 'message': 'Role berhasil dibuat'}), 201


@role_mgmt_bp.route('/roles/<int:approle_id>', methods=['PUT'])
@login_required
@super_admin_required
def update_role(approle_id):
    data = request.get_json(silent=True)
    if not data or not data.get('approle_name'):
        return jsonify({'error': 'bad_request', 'details': 'approle_name is required'}), 400

    approle_name = data['approle_name'].strip()
    result = role_transaction.update_role_trx(approle_id, approle_name)
    if not result.get('status'):
        msg = result.get('msg', '')
        if 'tidak ditemukan' in msg.lower():
            return jsonify({'error': 'not_found', 'details': msg}), 404
        return jsonify({'error': 'server_error', 'details': msg}), 500
    return jsonify({'data': result.get('data'), 'message': 'Role berhasil diupdate'}), 200


@role_mgmt_bp.route('/roles/<int:approle_id>', methods=['DELETE'])
@login_required
@super_admin_required
def delete_role(approle_id):
    result = role_transaction.delete_role_trx(approle_id)
    if not result.get('status'):
        msg = result.get('msg', '')
        status_code = 404 if 'tidak ditemukan' in msg.lower() else 400
        return jsonify({'error': 'bad_request', 'details': msg}), status_code
    return jsonify({'message': result.get('msg')}), 200


# ---------------------------------------------------------------------------
# sr_ms_permission — List Permissions
# ---------------------------------------------------------------------------

@role_mgmt_bp.route('/permissions', methods=['GET'])
@login_required
@super_admin_required
def list_permissions():
    result = role_transaction.get_all_permissions_trx()
    if not result.get('status'):
        return jsonify({'error': 'server_error', 'details': result.get('msg')}), 500
    return jsonify({'data': result.get('data')}), 200


# ---------------------------------------------------------------------------
# sr_role_permission — Role-Permission Mapping
# ---------------------------------------------------------------------------

@role_mgmt_bp.route('/roles/<int:approle_id>/permissions', methods=['GET'])
@login_required
@super_admin_required
def get_role_permissions(approle_id):
    role_result = role_transaction.get_role_by_id_trx(approle_id)
    if not role_result.get('status'):
        return jsonify({'error': 'not_found', 'details': 'Role tidak ditemukan'}), 404

    perms_result = role_transaction.get_permissions_by_role_trx(approle_id)
    if not perms_result.get('status'):
        return jsonify({'error': 'server_error', 'details': perms_result.get('msg')}), 500

    return jsonify({'data': {
        'role': role_result.get('data'),
        'permissions': perms_result.get('data')
    }}), 200


@role_mgmt_bp.route('/roles/<int:approle_id>/permissions', methods=['POST'])
@login_required
@super_admin_required
def set_role_permissions(approle_id):
    role_result = role_transaction.get_role_by_id_trx(approle_id)
    if not role_result.get('status'):
        return jsonify({'error': 'not_found', 'details': 'Role tidak ditemukan'}), 404

    data = request.get_json(silent=True)
    if not data or 'permission_ids' not in data:
        return jsonify({'error': 'bad_request', 'details': 'permission_ids is required (array of int)'}), 400
    if not isinstance(data['permission_ids'], list):
        return jsonify({'error': 'bad_request', 'details': 'permission_ids must be an array'}), 400

    result = role_transaction.set_role_permissions_trx(approle_id, data['permission_ids'])
    if not result.get('status'):
        return jsonify({'error': 'server_error', 'details': result.get('msg')}), 500

    return jsonify({
        'data': {'role': role_result.get('data'), 'permissions': result.get('data')},
        'message': 'Permissions berhasil diupdate'
    }), 200


# ---------------------------------------------------------------------------
# sr_user — Assigned Roles
# ---------------------------------------------------------------------------

@role_mgmt_bp.route('/assigned-roles', methods=['GET'])
@login_required
@super_admin_required
def list_assigned_roles():
    result = role_transaction.get_all_assigned_roles_trx()
    if not result.get('status'):
        return jsonify({'error': 'server_error', 'details': result.get('msg')}), 500
    return jsonify({'data': result.get('data')}), 200


@role_mgmt_bp.route('/assigned-roles', methods=['POST'])
@login_required
@super_admin_required
def assign_role():
    data = request.get_json(silent=True)
    if not data or not data.get('nik') or not data.get('approle_id'):
        return jsonify({'error': 'bad_request', 'details': 'nik and approle_id are required'}), 400

    nik = str(data['nik']).strip()
    approle_id = int(data['approle_id'])

    result = role_transaction.assign_role_trx(nik, approle_id)
    if not result.get('status'):
        msg = result.get('msg', '')
        status_code = 409 if 'sudah memiliki' in msg.lower() else 500
        return jsonify({'error': 'conflict' if status_code == 409 else 'server_error', 'details': msg}), status_code

    return jsonify({'data': result.get('data'), 'message': 'Role berhasil di-assign'}), 201


@role_mgmt_bp.route('/assigned-roles/<int:user_id>', methods=['DELETE'])
@login_required
@super_admin_required
def remove_assigned_role(user_id):
    result = role_transaction.remove_assigned_role_trx(user_id)
    if not result.get('status'):
        msg = result.get('msg', '')
        status_code = 404 if 'tidak ditemukan' in msg.lower() else 500
        return jsonify({'error': 'not_found' if status_code == 404 else 'server_error', 'details': msg}), status_code
    return jsonify({'message': result.get('msg')}), 200


# ---------------------------------------------------------------------------
# Karyawan Search
# ---------------------------------------------------------------------------

@role_mgmt_bp.route('/karyawan/search', methods=['GET'])
@login_required
@super_admin_required
def search_karyawan():
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 5, type=int)
    offset = request.args.get('offset', 0, type=int)

    result = karyawan_transaction.search_karyawan_trx(query, limit, offset)
    if not result.get('status'):
        return jsonify({'error': 'server_error', 'details': result.get('msg')}), 500
    return jsonify({'data': result.get('data')}), 200
