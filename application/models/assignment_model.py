from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

# Constants
ASSIGNABLE_PICROLE_IDS = [4, 5, 6, 7]  # IT SCM, IT DEV, IT QA, IT RO
IT_SM_ROLE_ID = 3
STATUS_BACKLOG_SCRUM = 105
STATUS_SD_ON_PROGRESS = 106
IT_USER_ROLE_NAME = 'User IT'  # approle_name di sr_ms_app_role


def get_it_users_model() -> dict:
    """Ambil semua user dari sr_user yang punya role 'User IT', JOIN karyawan_all untuk nama."""
    sql = """
        SELECT su.nik, COALESCE(k.nama, '') AS nama
        FROM sr_user su
        JOIN sr_ms_app_role r ON su.approle_id = r.approle_id
        LEFT JOIN karyawan_all k ON su.nik = k.nik
        WHERE r.approle_name = %(role_name)s
        ORDER BY k.nama
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'role_name': IT_USER_ROLE_NAME})
    except Exception as e:
        Log.error(f'DB Exception | get_it_users | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_assignable_picroles_model() -> dict:
    """Ambil PIC roles yang bisa di-assign oleh SM: SCM(4), DEV(5), QA(6), RO(7)."""
    sql = """
        SELECT it_role_id, it_role_detail
        FROM sr_ms_it
        WHERE it_role_id IN (4, 5, 6, 7)
        ORDER BY it_role_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectHeader(sql)
    except Exception as e:
        Log.error(f'DB Exception | get_assignable_picroles | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_sr_assignments_model(sr_no: str, it_role_ids: list = None) -> dict:
    """Ambil assignment pada SR. Jika it_role_ids diberikan, filter hanya role tersebut."""
    sql = """
        SELECT sa.assign_id, sa.sr_no, sa.assigned_user,
               COALESCE(k.nama, '') AS nama,
               sa.it_role_id, it.it_role_detail,
               sa.assigned_by, sa.assigned_at
        FROM sr_assignments sa
        LEFT JOIN karyawan_all k ON sa.assigned_user = k.nik
        LEFT JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.sr_no = %(sr_no)s
    """
    params = {'sr_no': sr_no}
    if it_role_ids:
        sql += " AND sa.it_role_id IN %(it_role_ids)s"
        params['it_role_ids'] = tuple(it_role_ids)
    sql += " ORDER BY sa.it_role_id, sa.assign_id"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, params)
    except Exception as e:
        Log.error(f'DB Exception | get_sr_assignments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_sm_on_sr_model(sr_no: str, nik: str) -> dict:
    """Cek apakah NIK adalah IT SM (it_role_id=3) yang ter-assign pada SR ini."""
    sql = """
        SELECT sa.assign_id, sa.assigned_user, sa.it_role_id
        FROM sr_assignments sa
        WHERE sa.sr_no = %(sr_no)s
          AND sa.assigned_user = %(nik)s
          AND sa.it_role_id = %(sm_role)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no, 'nik': nik, 'sm_role': IT_SM_ROLE_ID})
    except Exception as e:
        Log.error(f'DB Exception | get_sm_on_sr | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_sr_detail_with_status_model(sr_no: str) -> dict:
    """Ambil detail SR beserta status untuk halaman assignment."""
    sql = """
        SELECT r.sr_no, r.name, r.module, r.purpose, r.division, r.details,
               r.smk_id, s.smk_ket,
               r.req_id, COALESCE(k.nama, '') AS req_name
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
        Log.error(f'DB Exception | get_sr_detail_with_status | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def insert_assignments_and_update_status_model(sr_no: str, assignments: list, assigned_by: str) -> dict:
    """
    Insert semua assignment dan update status SR (105→106) secara ATOMIK.
    assignments = list of {'nik': str, 'it_role_id': int}
    Menggunakan autocommit=False + manual commit/rollback.
    """
    insert_sql = """
        INSERT INTO sr_assignments (sr_no, assigned_user, assigned_by, it_role_id, assigned_at)
        VALUES (%(sr_no)s, %(assigned_user)s, %(assigned_by)s, %(it_role_id)s, NOW())
    """
    update_sql = """
        UPDATE sr_request SET smk_id = %(new_status)s WHERE sr_no = %(sr_no)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=False)
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}

        for a in assignments:
            result = conn.executeDataNoCommit(insert_sql, {
                'sr_no': sr_no,
                'assigned_user': a['nik'],
                'assigned_by': assigned_by,
                'it_role_id': a['it_role_id']
            })
            if not result.get('status'):
                raise Exception(result.get('msg', 'Gagal insert assignment'))

        result = conn.executeDataNoCommit(update_sql, {
            'sr_no': sr_no,
            'new_status': STATUS_SD_ON_PROGRESS
        })
        if not result.get('status'):
            raise Exception(result.get('msg', 'Gagal update status SR'))

        conn._conn.commit()
        return {'status': True, 'data': [], 'msg': 'Assignment berhasil disimpan dan status SR diupdate.'}
    except Exception as e:
        if conn:
            try:
                conn._conn.rollback()
            except Exception:
                pass
        Log.error(f'DB Exception | insert_assignments_and_update_status | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
