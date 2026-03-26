from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

SUPER_ADMIN_ROLE_ID = 1

# sr_ms_app_role
def get_all_roles_model() -> dict:
    sql = "SELECT approle_id, approle_name FROM sr_ms_app_role ORDER BY approle_id"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectHeader(sql)
    except Exception as e:
        Log.error(f'DB Exception | get_all_roles | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_role_by_id_model(approle_id: int) -> dict:
    sql = "SELECT approle_id, approle_name FROM sr_ms_app_role WHERE approle_id = %(approle_id)s"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'approle_id': approle_id})
    except Exception as e:
        Log.error(f'DB Exception | get_role_by_id | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def create_role_model(approle_name: str) -> dict:
    sql_insert = "INSERT INTO sr_ms_app_role (approle_name) VALUES (%(approle_name)s)"
    sql_select = """
        SELECT approle_id, approle_name FROM sr_ms_app_role
        WHERE approle_name = %(approle_name)s
        ORDER BY approle_id DESC LIMIT 1
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        res = conn.executeData(sql_insert, {'approle_name': approle_name})
        if not res.get('status'):
            return res
        return conn.selectDataHeader(sql_select, {'approle_name': approle_name})
    except Exception as e:
        Log.error(f'DB Exception | create_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def update_role_model(approle_id: int, approle_name: str) -> dict:
    sql_update = """
        UPDATE sr_ms_app_role SET approle_name = %(approle_name)s
        WHERE approle_id = %(approle_id)s
    """
    sql_select = "SELECT approle_id, approle_name FROM sr_ms_app_role WHERE approle_id = %(approle_id)s"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        res = conn.executeData(sql_update, {'approle_name': approle_name, 'approle_id': approle_id})
        if not res.get('status'):
            return res
        if res.get('rowcount', 0) == 0:
            return {'status': False, 'data': [], 'msg': 'Role tidak ditemukan'}
        return conn.selectDataHeader(sql_select, {'approle_id': approle_id})
    except Exception as e:
        Log.error(f'DB Exception | update_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def delete_role_model(approle_id: int) -> dict:
    if approle_id == SUPER_ADMIN_ROLE_ID:
        return {'status': False, 'data': [], 'msg': 'Role Admin tidak bisa dihapus'}
    sql = "DELETE FROM sr_ms_app_role WHERE approle_id = %(approle_id)s"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.executeData(sql, {'approle_id': approle_id})
    except Exception as e:
        Log.error(f'DB Exception | delete_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


# sr_role_permission — semua mapping dalam satu query

def get_roles_with_permissions_model() -> dict:
    """
    Ambil semua role beserta nama permission-nya dalam SATU query JOIN.
    Menggantikan query terpisah get_all_roles + get_all_role_permissions.
    """
    sql = """
        SELECT
            r.approle_id,
            r.approle_name,
            p.permission_id,
            p.permission_detail
        FROM sr_ms_app_role r
        LEFT JOIN sr_role_permission rp ON r.approle_id = rp.approle_id
        LEFT JOIN sr_ms_permission p ON rp.permission_id = p.permission_id
        ORDER BY r.approle_id, p.permission_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectHeader(sql)
    except Exception as e:
        Log.error(f'DB Exception | get_roles_with_permissions | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_all_permissions_model() -> dict:
    sql = "SELECT permission_id, permission_detail FROM sr_ms_permission ORDER BY permission_id"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectHeader(sql)
    except Exception as e:
        Log.error(f'DB Exception | get_all_permissions | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

# sr_role_permission
def get_permissions_by_role_model(approle_id: int) -> dict:
    sql = """
        SELECT p.permission_id, p.permission_detail
        FROM sr_role_permission rp
        JOIN sr_ms_permission p ON rp.permission_id = p.permission_id
        WHERE rp.approle_id = %(approle_id)s
        ORDER BY p.permission_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'approle_id': approle_id})
    except Exception as e:
        Log.error(f'DB Exception | get_permissions_by_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def set_role_permissions_model(approle_id: int, permission_ids: list) -> dict:
    """Delete lama + insert baru dalam satu transaksi atomik."""
    sql_delete = "DELETE FROM sr_role_permission WHERE approle_id = %(approle_id)s"
    sql_insert = """
        INSERT INTO sr_role_permission (approle_id, permission_id)
        VALUES (%(approle_id)s, %(permission_id)s)
    """
    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=False)
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}

        res = conn.executeDataNoCommit(sql_delete, {'approle_id': approle_id})
        if not res.get('status'):
            conn._conn.rollback()
            return res

        for perm_id in permission_ids:
            res = conn.executeDataNoCommit(sql_insert, {'approle_id': approle_id, 'permission_id': perm_id})
            if not res.get('status'):
                conn._conn.rollback()
                return res

        conn._conn.commit()
        return {'status': True, 'data': [], 'msg': 'Permissions berhasil diupdate'}
    except Exception as e:
        if conn and conn._conn:
            try: conn._conn.rollback()
            except: pass
        Log.error(f'DB Exception | set_role_permissions | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

# sr_user
def get_all_assigned_roles_model() -> dict:
    sql = """
        SELECT su.user_id, su.nik, su.approle_id,
               r.approle_name,
               COALESCE(k.nama, '') AS nama
        FROM sr_user su
        JOIN sr_ms_app_role r ON su.approle_id = r.approle_id
        LEFT JOIN karyawan_all k ON su.nik = k.nik
        ORDER BY su.user_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectHeader(sql)
    except Exception as e:
        Log.error(f'DB Exception | get_all_assigned_roles | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def check_assigned_role_model(nik: str, approle_id: int) -> dict:
    sql = "SELECT user_id FROM sr_user WHERE nik = %(nik)s AND approle_id = %(approle_id)s"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'nik': nik, 'approle_id': approle_id})
    except Exception as e:
        Log.error(f'DB Exception | check_assigned_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def assign_role_model(nik: str, approle_id: int) -> dict:
    sql_insert = "INSERT INTO sr_user (nik, approle_id) VALUES (%(nik)s, %(approle_id)s)"
    sql_select = """
        SELECT su.user_id, su.nik, su.approle_id, r.approle_name
        FROM sr_user su
        JOIN sr_ms_app_role r ON su.approle_id = r.approle_id
        WHERE su.nik = %(nik)s AND su.approle_id = %(approle_id)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        res = conn.executeData(sql_insert, {'nik': nik, 'approle_id': approle_id})
        if not res.get('status'):
            return res
        return conn.selectDataHeader(sql_select, {'nik': nik, 'approle_id': approle_id})
    except Exception as e:
        Log.error(f'DB Exception | assign_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def update_assigned_role_model(user_id: int, approle_id: int) -> dict:
    sql = "UPDATE sr_user SET approle_id = %(approle_id)s WHERE user_id = %(user_id)s"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.executeData(sql, {'user_id': user_id, 'approle_id': approle_id})
    except Exception as e:
        Log.error(f'DB Exception | update_assigned_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def remove_assigned_role_model(user_id: int) -> dict:
    sql = "DELETE FROM sr_user WHERE user_id = %(user_id)s"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.executeData(sql, {'user_id': user_id})
    except Exception as e:
        Log.error(f'DB Exception | remove_assigned_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_user_permissions_model(nik: str) -> dict:
    sql = """
        SELECT DISTINCT p.permission_detail
        FROM sr_user su
        JOIN sr_role_permission rp ON su.approle_id = rp.approle_id
        JOIN sr_ms_permission p ON rp.permission_id = p.permission_id
        WHERE su.nik = %(nik)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'nik': nik})
    except Exception as e:
        Log.error(f'DB Exception | get_user_permissions | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_user_role_name_model(nik: str) -> dict:
    sql = """
        SELECT r.approle_name
        FROM sr_user su
        JOIN sr_ms_app_role r ON su.approle_id = r.approle_id
        WHERE su.nik = %(nik)s
        LIMIT 1
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'nik': nik})
    except Exception as e:
        Log.error(f'DB Exception | get_user_role_name | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
