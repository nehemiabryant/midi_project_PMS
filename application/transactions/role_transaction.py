from common.midiconnectserver.midilog import Logger
from ..models import role as role_model
from ..utils.converters import parse_rows, parse_single_row

Log = Logger()

# Roles
def get_all_roles_trx() -> dict:
    try:
        result = role_model.get_all_roles_model()
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_rows(result)}
    except Exception as e:
        Log.error(f'Exception | get_all_roles | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def get_role_by_id_trx(approle_id: int) -> dict:
    try:
        result = role_model.get_role_by_id_model(approle_id)
        if not result.get('status'):
            return result
        data = parse_single_row(result)
        if data is None:
            return {'status': False, 'data': [], 'msg': 'Role tidak ditemukan'}
        return {'status': True, 'data': data}
    except Exception as e:
        Log.error(f'Exception | get_role_by_id | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def create_role_trx(approle_name: str) -> dict:
    try:
        result = role_model.create_role_model(approle_name)
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_single_row(result)}
    except Exception as e:
        Log.error(f'Exception | create_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def update_role_trx(approle_id: int, approle_name: str) -> dict:
    try:
        result = role_model.update_role_model(approle_id, approle_name)
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_single_row(result)}
    except Exception as e:
        Log.error(f'Exception | update_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def delete_role_trx(approle_id: int) -> dict:
    try:
        result = role_model.delete_role_model(approle_id)
        if not result.get('status'):
            return result
        if result.get('rowcount', 0) == 0:
            return {'status': False, 'data': [], 'msg': 'Role tidak ditemukan'}
        return {'status': True, 'data': [], 'msg': 'Role berhasil dihapus'}
    except Exception as e:
        Log.error(f'Exception | delete_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

# Semua role-permission mapping (untuk hindari N+1 query)
def get_roles_with_permissions_trx() -> dict:
    """
    Return sekaligus:
      - 'roles': list of {approle_id, approle_name}
      - 'role_permissions': dict {approle_id: [permission_id, ...]}
    Hanya 1 koneksi ke DB.
    """
    try:
        result = role_model.get_roles_with_permissions_model()
        rows = parse_rows(result) if result.get('status') else []
        roles_seen = {}
        role_permissions = {}
        for row in rows:
            rid = row['approle_id']
            if rid not in roles_seen:
                roles_seen[rid] = {'approle_id': rid, 'approle_name': row['approle_name']}
                role_permissions[rid] = []
            if row['permission_id'] is not None:
                role_permissions[rid].append(row['permission_id'])
        return {
            'status': True,
            'roles': list(roles_seen.values()),
            'role_permissions': role_permissions
        }
    except Exception as e:
        Log.error(f'Exception | get_roles_with_permissions | Msg: {str(e)}')
        return {'status': False, 'roles': [], 'role_permissions': {}}

# Permissions
def get_all_permissions_trx() -> dict:
    try:
        result = role_model.get_all_permissions_model()
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_rows(result)}
    except Exception as e:
        Log.error(f'Exception | get_all_permissions | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def get_permissions_by_role_trx(approle_id: int) -> dict:
    try:
        result = role_model.get_permissions_by_role_model(approle_id)
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_rows(result)}
    except Exception as e:
        Log.error(f'Exception | get_permissions_by_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def set_role_permissions_trx(approle_id: int, permission_ids: list) -> dict:
    try:
        result = role_model.set_role_permissions_model(approle_id, permission_ids)
        if not result.get('status'):
            return result
        # Fetch updated permissions untuk response
        return get_permissions_by_role_trx(approle_id)
    except Exception as e:
        Log.error(f'Exception | set_role_permissions | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

# Assigned Roles (sr_user)
def get_all_assigned_roles_trx() -> dict:
    try:
        result = role_model.get_all_assigned_roles_model()
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_rows(result)}
    except Exception as e:
        Log.error(f'Exception | get_all_assigned_roles | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def assign_role_trx(nik: str, approle_id: int) -> dict:
    try:
        # Cek duplikasi terlebih dahulu
        check = role_model.check_assigned_role_model(nik, approle_id)
        if parse_rows(check):
            return {'status': False, 'data': [], 'msg': 'User sudah memiliki role ini'}

        result = role_model.assign_role_model(nik, approle_id)
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_single_row(result)}
    except Exception as e:
        Log.error(f'Exception | assign_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def remove_all_roles_by_nik_trx(nik: str) -> dict:
    try:
        result = role_model.remove_all_roles_by_nik_model(nik)
        if not result.get('status'):
            return result
        return {'status': True, 'data': [], 'msg': 'User berhasil dihapus'}
    except Exception as e:
        Log.error(f'Exception | remove_all_roles_by_nik | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def reassign_roles_trx(nik: str, approle_ids: list) -> dict:
    """Hapus semua role user lalu insert ulang secara atomik."""
    from common.midiconnectserver import DatabasePG
    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=False)
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}

        del_result = role_model.delete_all_roles_by_nik_model(nik, conn)
        if not del_result.get('status'):
            raise Exception(del_result.get('msg', 'Gagal menghapus role lama'))

        for approle_id in approle_ids:
            sql = "INSERT INTO sr_user (nik, approle_id) VALUES (%(nik)s, %(approle_id)s)"
            ins = conn.executeData(sql, {'nik': nik, 'approle_id': int(approle_id)})
            if not ins.get('status'):
                raise Exception(ins.get('msg', 'Gagal insert role baru'))

        conn._conn.commit()
        return {'status': True, 'data': [], 'msg': f'{len(approle_ids)} role berhasil diupdate.'}
    except Exception as e:
        try: conn._conn.rollback()
        except Exception: pass
        Log.error(f'Exception | reassign_roles | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

