from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

# Status ID constants — tidak bisa di-derive secara aman tanpa mengetahui string smk_ket yang tepat.
# TODO: Migrate ke query by smk_ket name ketika konsistensi data di sr_ms_ket terjamin.
STATUS_BACKLOG_SCRUM = 105
STATUS_SD_ON_PROGRESS = 106
STATUS_IT_GM_REVIEW = 104

def get_it_users_model() -> dict:
    """Ambil semua user dari sr_user yang punya role 'IT USER', JOIN karyawan_all untuk nama."""
    it_user_role_name = 'IT USER'  # approle_name di sr_ms_app_role (approle_id=2)
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
        return conn.selectDataHeader(sql, {'role_name': it_user_role_name})
    except Exception as e:
        Log.error(f'DB Exception | get_it_users | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_assignable_picroles_model() -> dict:
    """
    Ambil PIC roles yang bisa di-assign oleh SM.
    Di-derive langsung dari sr_ms_workflow_rules, mengecualikan role oversight (1,2,3,8,9).
    """
    sql = """
        SELECT DISTINCT it.it_role_id, it.it_role_detail
        FROM sr_ms_it it
        WHERE it.it_role_id IN (
            SELECT DISTINCT allowed_picrole
            FROM sr_ms_workflow_rules
            WHERE allowed_picrole IS NOT NULL
              AND allowed_picrole NOT IN (1, 2, 3, 8, 9)
        )
        ORDER BY it.it_role_id
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


def get_it_role_id_by_name_model(role_name: str) -> int | None:
    """Ambil it_role_id dari sr_ms_it berdasarkan it_role_detail (nama role)."""
    sql = "SELECT it_role_id FROM sr_ms_it WHERE it_role_detail = %(role_name)s LIMIT 1"
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return None
        result = conn.selectData(sql, {'role_name': role_name})
        if result.get('status') and result.get('data'):
            return int(result['data'][0][0])
        return None
    except Exception as e:
        Log.error(f'DB Exception | get_it_role_id_by_name | Msg: {str(e)}')
        return None
    finally:
        if conn: conn.close()


def get_user_role_assignment_on_sr_model(sr_no: str, nik: str, role_name: str) -> dict:
    """
    Cek apakah NIK ter-assign pada SR ini dengan role_name tertentu (berdasarkan it_role_detail).
    Menggantikan fungsi spesifik get_sm_on_sr_model dan get_gm_on_sr_model.
    Contoh: get_user_role_assignment_on_sr_model(sr_no, nik, 'IT SM')
    """
    sql = """
        SELECT sa.assign_id, sa.assigned_user, sa.it_role_id, it.it_role_detail
        FROM sr_assignments sa
        JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.sr_no = %(sr_no)s
          AND sa.assigned_user = %(nik)s
          AND it.it_role_detail = %(role_name)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no, 'nik': nik, 'role_name': role_name})
    except Exception as e:
        Log.error(f'DB Exception | get_user_role_assignment_on_sr | Msg: {str(e)}')
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


def get_it_role_on_sr_model(sr_no: str, nik: str) -> dict:
    """Cek apakah it_role pada nik yang ter-assign pada SR ini. Return role_id jika ada."""
    sql = """
        SELECT it_role_id
        FROM sr_assignments
        WHERE sr_no = %(sr_no)s
          AND assigned_user = %(nik)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        result = conn.selectData(sql, {'sr_no': sr_no, 'nik': nik})
        if result.get('status') and result.get('data'):
            return result['data'][0][0]  # Return it_role_id
        else:
            return None  # No IT role found for this user on this SR
    except Exception as e:
        Log.error(f'DB Exception | get_it_role_on_sr | Msg: {str(e)}')
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


def get_sm_options_model(nik_list: list) -> dict:
    """Ambil NIK dan nama dari karyawan_all untuk list NIK IT SM."""
    sql = """
        SELECT nik, COALESCE(nama, '') AS nama
        FROM karyawan_all
        WHERE nik IN %(niks)s
        ORDER BY nama
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'niks': tuple(nik_list)})
    except Exception as e:
        Log.error(f'DB Exception | get_sm_options | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def insert_assignments_model(sr_no: str, assignments: list, assigned_by: str, shared_conn=None) -> dict:
    """
    Insert semua assignment pada SR.
    assignments = list of {'nik': str, 'it_role_id': int}
    Jika shared_conn diberikan, pakai koneksi tersebut (tidak commit/rollback sendiri).
    """
    insert_sql = """
        INSERT INTO sr_assignments (sr_no, assigned_user, assigned_by, it_role_id, assigned_at)
        VALUES (%(sr_no)s, %(assigned_user)s, %(assigned_by)s, %(it_role_id)s, NOW())
        ON CONFLICT DO NOTHING
    """

    if shared_conn:
        for a in assignments:
            result = shared_conn.executeDataNoCommit(insert_sql, {
                'sr_no': sr_no,
                'assigned_user': a['nik'],
                'assigned_by': assigned_by,
                'it_role_id': a['it_role_id']
            })
            if not result.get('status'):
                return {'status': False, 'data': [], 'msg': result.get('msg', 'Gagal insert assignment')}
        return {'status': True, 'data': [], 'msg': 'Assignment berhasil disimpan.'}

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

        conn._conn.commit()
        return {'status': True, 'data': [], 'msg': 'Assignment berhasil disimpan.'}
    except Exception as e:
        if conn:
            try:
                conn._conn.rollback()
            except Exception:
                pass
        Log.error(f'DB Exception | insert_assignments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_sr_origins(sr_no: str, shared_conn=None) -> dict:
    """Fetches the requester and maker of the SR."""
    sql = """
        SELECT r.sr_no, r.req_id, ka_req.nama AS requester_name, 
               r.maker_id, ka_maker.nama AS maker_name
        FROM public.sr_request r
        LEFT JOIN public.karyawan_all ka_req ON r.req_id = ka_req.nik
        LEFT JOIN public.karyawan_all ka_maker ON r.maker_id = ka_maker.nik
        WHERE r.sr_no = %(sr_no)s;
    """
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {'sr_no': sr_no})

    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no})
    except Exception as e:
        Log.error(f'DB Exception | get_sr_origins | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_sr_approvers(sr_no: str, shared_conn=None) -> dict:
    """Fetches the active approvers for the SR based on defined roles."""
    sql = """
        SELECT 
            sa.it_role_id, 
            smi.it_role_detail, 
            sa.assigned_user AS approver_nik, 
            ka.nama AS approver_name
        FROM public.sr_assignments sa
        JOIN public.karyawan_all ka ON sa.assigned_user = ka.nik
        JOIN public.sr_request sr ON sa.sr_no = sr.sr_no
        JOIN public.sr_ms_ket smk ON sr.smk_id = smk.smk_id
        JOIN public.sr_ms_it smi ON sa.it_role_id = smi.it_role_id  -- NEW JOIN
        WHERE sa.sr_no = %(sr_no)s 
          AND smk.workflow = 'approval'
          AND sa.it_role_id IN (1, 2, 3, 8) -- Keep this if you still want to whitelist roles
        ORDER BY array_position(ARRAY[8, 2, 1, 3], sa.it_role_id);
    """
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {'sr_no': sr_no})

    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no})
    except Exception as e:
        Log.error(f'DB Exception | get_sr_approvers | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()