from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_user_role_info_model(nik: str) -> dict:
    """Ambil role name + semua permissions user berdasarkan NIK (untuk session login)."""
    sql = """
        SELECT
            r.approle_name,
            COALESCE(
                ARRAY_AGG(p.permission_detail) FILTER (WHERE p.permission_detail IS NOT NULL),
                ARRAY[]::TEXT[]
            ) AS permissions
        FROM sr_user su
        JOIN sr_ms_app_role r ON su.approle_id = r.approle_id
        LEFT JOIN sr_role_permission rp ON su.approle_id = rp.approle_id
        LEFT JOIN sr_ms_permission p ON rp.permission_id = p.permission_id
        WHERE su.nik = %(nik)s
        GROUP BY r.approle_name
        LIMIT 1
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'nik': nik})
    except Exception as e:
        Log.error(f'DB Exception | get_user_role_info | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()