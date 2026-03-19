from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()


def get_my_work_items_model(nik: str) -> dict:
    """
    Ambil semua SR yang di-assign ke user ini beserta role-nya.
    Satu query untuk semua role — hasilnya di-group di transaction layer.
    """
    sql = """
        SELECT r.sr_no, r.name, r.module, r.division,
               r.smk_id, COALESCE(s.smk_ket, '') AS smk_ket,
               r.created_at,
               sa.it_role_id, COALESCE(it.it_role_detail, '') AS it_role_detail
        FROM sr_assignments sa
        JOIN sr_request r ON sa.sr_no = r.sr_no
        LEFT JOIN sr_ms_ket s ON r.smk_id = s.smk_id
        LEFT JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.assigned_user = %(nik)s
        ORDER BY r.created_at DESC
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'nik': nik})
    except Exception as e:
        Log.error(f'DB Exception | get_my_work_items | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_sr_detail_full_model(sr_no: str) -> dict:
    """Ambil detail SR lengkap untuk halaman detail."""
    sql = """
        SELECT r.sr_no, r.name, r.module, r.purpose, r.division, r.details,
               r.frequency, r.value, r.value_det, r.num_user,
               r.smk_id, COALESCE(s.smk_ket, '') AS smk_ket,
               r.req_id, COALESCE(k.nama, '') AS req_name,
               r.created_at
        FROM sr_request r
        LEFT JOIN sr_ms_ket s ON r.smk_id = s.smk_id
        LEFT JOIN karyawan_all k ON r.req_id = k.nik
        WHERE r.sr_no = %(sr_no)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no})
    except Exception as e:
        Log.error(f'DB Exception | get_sr_detail_full | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_all_sr_assignments_model(sr_no: str) -> dict:
    """Ambil semua assignment pada SR (semua role)."""
    sql = """
        SELECT sa.assign_id, sa.sr_no, sa.assigned_user,
               COALESCE(k.nama, '') AS nama,
               sa.it_role_id, COALESCE(it.it_role_detail, '') AS it_role_detail,
               sa.assigned_by, sa.assigned_at
        FROM sr_assignments sa
        LEFT JOIN karyawan_all k ON sa.assigned_user = k.nik
        LEFT JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.sr_no = %(sr_no)s
        ORDER BY sa.it_role_id, sa.assign_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no})
    except Exception as e:
        Log.error(f'DB Exception | get_all_sr_assignments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_user_role_on_sr_model(sr_no: str, nik: str) -> dict:
    """Ambil role user pada SR tertentu (bisa punya multiple role)."""
    sql = """
        SELECT sa.assign_id, sa.it_role_id, COALESCE(it.it_role_detail, '') AS it_role_detail
        FROM sr_assignments sa
        LEFT JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.sr_no = %(sr_no)s AND sa.assigned_user = %(nik)s
        ORDER BY sa.it_role_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no, 'nik': nik})
    except Exception as e:
        Log.error(f'DB Exception | get_user_role_on_sr | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
