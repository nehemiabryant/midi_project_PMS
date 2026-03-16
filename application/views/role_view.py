from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash
from ..transactions import role_transaction, karyawan_transaction
from ..helpers.decorators import login_required, super_admin_required

role_mgmt_bp = Blueprint('role_mgmt', __name__)


# ---------------------------------------------------------------------------
# Master Role — Page + Form Handlers
# ---------------------------------------------------------------------------

@role_mgmt_bp.route('/masterRole', methods=['GET'])
@login_required
@super_admin_required
def master_role_menu():
    rp_result = role_transaction.get_roles_with_permissions_trx()
    perms_result = role_transaction.get_all_permissions_trx()
    roles = rp_result.get('roles', []) if rp_result.get('status') else []
    role_permissions = rp_result.get('role_permissions', {}) if rp_result.get('status') else {}
    permissions = perms_result.get('data', []) if perms_result.get('status') else []

    return render_template('page/master_role.html', active_menu='master_role',
                           roles=roles, permissions=permissions,
                           role_permissions=role_permissions)


@role_mgmt_bp.route('/masterRole/create', methods=['POST'])
@login_required
@super_admin_required
def master_role_create():
    approle_name = request.form.get('approle_name', '').strip()
    if not approle_name:
        flash('Nama role tidak boleh kosong.', 'error')
        return redirect(url_for('role_mgmt.master_role_menu'))

    result = role_transaction.create_role_trx(approle_name)
    if not result.get('status'):
        flash(result.get('msg', 'Gagal membuat role.'), 'error')
        return redirect(url_for('role_mgmt.master_role_menu'))

    role_id = result['data']['approle_id']
    perm_ids = [int(x) for x in request.form.getlist('permission_ids')]
    role_transaction.set_role_permissions_trx(role_id, perm_ids)

    flash('Role berhasil dibuat.', 'success')
    return redirect(url_for('role_mgmt.master_role_menu'))

@role_mgmt_bp.route('/masterRole/new', methods=['GET'])
@login_required
@super_admin_required
def new_role_menu():
    perms_result = role_transaction.get_all_permissions_trx()
    permissions = perms_result.get('data', []) if perms_result.get('status') else []

    return render_template(
        'page/new_role.html',
        active_menu='master_role',
        permissions=permissions
    )

@role_mgmt_bp.route('/masterRole/<int:approle_id>/edit', methods=['GET'])
@login_required
@super_admin_required
def edit_role_menu(approle_id):

    result = role_transaction.get_role_by_id_trx(approle_id)

    if not result.get('status'):
        flash('Role tidak ditemukan.', 'error')
        return redirect(url_for('role_mgmt.master_role_menu'))

    role = result.get('data')

    return render_template(
        'page/edit_role.html',
        active_menu='master_role',
        role=role
    )


@role_mgmt_bp.route('/masterRole/<int:approle_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def master_role_delete(approle_id):
    result = role_transaction.delete_role_trx(approle_id)
    if not result.get('status'):
        flash(result.get('msg', 'Gagal menghapus role.'), 'error')
    else:
        flash('Role berhasil dihapus.', 'success')
    return redirect(url_for('role_mgmt.master_role_menu'))


# ---------------------------------------------------------------------------
# Master User — Page + Form Handlers
# ---------------------------------------------------------------------------

@role_mgmt_bp.route('/masterUser', methods=['GET'])
@login_required
@super_admin_required
def master_user_menu():
    users_result = role_transaction.get_all_assigned_roles_trx()
    roles_result = role_transaction.get_all_roles_trx()
    assigned_users = users_result.get('data', []) if users_result.get('status') else []
    roles = roles_result.get('data', []) if roles_result.get('status') else []
    return render_template('page/master_user.html', active_menu='master_user', assigned_users=assigned_users, roles=roles)


@role_mgmt_bp.route('/masterUser/assign', methods=['POST'])
@login_required
@super_admin_required
def master_user_assign():
    nik = request.form.get('nik', '').strip()
    approle_id = request.form.get('approle_id', '').strip()

    if not nik or not approle_id:
        flash('NIK dan role harus diisi.', 'error')
        return redirect(url_for('role_mgmt.master_user_menu'))

    result = role_transaction.assign_role_trx(nik, int(approle_id))
    if not result.get('status'):
        flash(result.get('msg', 'Gagal assign role.'), 'error')
    else:
        flash('Role berhasil di-assign.', 'success')
    return redirect(url_for('role_mgmt.master_user_menu'))


@role_mgmt_bp.route('/masterUser/<int:user_id>/remove', methods=['POST'])
@login_required
@super_admin_required
def master_user_remove(user_id):
    result = role_transaction.remove_assigned_role_trx(user_id)
    if not result.get('status'):
        flash(result.get('msg', 'Gagal menghapus assignment.'), 'error')
    else:
        flash('Assignment berhasil dihapus.', 'success')
    return redirect(url_for('role_mgmt.master_user_menu'))


# ---------------------------------------------------------------------------
# Karyawan Search — tetap JSON untuk autocomplete JS
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
