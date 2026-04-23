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
          AND sa.deleted_at IS NULL
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
        AND deleted_at IS NULL
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
    
def get_active_role_ids_on_sr_model(sr_no: str) -> set:               
    """Ambil set it_role_id yang sudah punya is_active=TRUE pada SR ini."""                                                              
    sql = """                                                         
        SELECT DISTINCT it_role_id
        FROM sr_assignments                                          
        WHERE sr_no = %(sr_no)s                                       
        AND is_active = TRUE
        AND deleted_at IS NULL                                      
    """         
    conn = None                                                      
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):                             
            return set()
        result = conn.selectData(sql, {'sr_no': sr_no})               
        if result.get('status') and result.get('data'):
            return {int(row[0]) for row in result['data']}            
        return set()
    except Exception as e:                                            
        Log.error(f'DB Exception | get_active_role_ids_on_sr | Msg: {str(e)}')                                                            
        return set()
    finally:                                                          
        if conn: conn.close()

def get_active_role_ids_by_assign_ids_model(assign_ids: list) -> set:
    """Dari list assign_id yang akan dihapus, kembalikan role_id yang is_active=TRUE."""                                                    
    if not assign_ids:
        return set()                                                  
    sql = """   
        SELECT DISTINCT it_role_id FROM sr_assignments               
        WHERE assign_id IN %(ids)s
        AND is_active = TRUE                                        
        AND deleted_at IS NULL
    """                                                               
    conn = None 
    try:                                                             
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return set()
        result = conn.selectData(sql, {'ids': tuple(assign_ids)})     
        if result.get('status') and result.get('data'):
            return {int(row[0]) for row in result['data']}            
        return set()                                                  
    except Exception as e:                                           
        Log.error(f'DB Exception | get_active_role_ids_by_assign_ids | Msg: {str(e)}')
        return set()                                                 
    finally:
        if conn: conn.close()


def get_it_role_on_sr_model(sr_no: str, nik: str) -> dict:
    """Cek apakah it_role pada nik yang ter-assign pada SR ini. Return role_id jika ada."""
    sql = """
        SELECT it_role_id
        FROM sr_assignments
        WHERE sr_no = %(sr_no)s
          AND assigned_user = %(nik)s
          AND deleted_at IS NULL
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


def check_role_assignment_model(sr_no: str, nik: str, it_role_id: int) -> bool:
    """Cek apakah nik ter-assign pada SR ini dengan role tertentu. Return True/False."""
    sql = """
        SELECT 1 FROM sr_assignments
        WHERE sr_no = %(sr_no)s
          AND assigned_user = %(nik)s
          AND it_role_id = %(it_role_id)s
          AND deleted_at IS NULL
        LIMIT 1
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return False
        result = conn.selectData(sql, {'sr_no': sr_no, 'nik': nik, 'it_role_id': it_role_id})
        return bool(result.get('status') and result.get('data'))
    except Exception as e:
        Log.error(f'DB Exception | check_role_assignment | Msg: {str(e)}')
        return False
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
    Upsert assignments pada SR.
    - Dict dengan 'assign_id' → UPDATE langsung by PK (tidak INSERT ulang)
    - Dict tanpa 'assign_id'  → INSERT baru (tanpa ON CONFLICT agar error constraint langsung terlihat)
    assignments = list of {'nik': str, 'it_role_id': int, 'is_active': bool (opsional), 'assign_id': int (opsional)}
    """
    sql_update = """
        UPDATE sr_assignments
        SET assigned_user = %(nik)s,
            it_role_id    = %(it_role_id)s,
            assigned_by   = %(assigned_by)s,
            assigned_at   = NOW()
        WHERE assign_id = %(assign_id)s
          AND deleted_at IS NULL
    """

    # 1. Query untuk cek siapa user yang saat ini aktif di role tersebut
    sql_check_active = """
        SELECT assigned_user 
        FROM sr_assignments 
        WHERE sr_no = %(sr_no)s 
          AND it_role_id = %(it_role_id)s 
          AND is_active = TRUE 
          AND deleted_at IS NULL
        LIMIT 1
    """

    # 2. Query untuk menonaktifkan user lama (Audit-Friendly)
    sql_soft_delete = """
        UPDATE sr_assignments
        SET is_active = false,
            deleted_at = NOW(),
            assigned_by = %(assigned_by)s
        WHERE sr_no = %(sr_no)s
          AND it_role_id = %(it_role_id)s
          AND is_active = true
          AND deleted_at IS NULL
    """

    sql_insert = """
        INSERT INTO sr_assignments (sr_no, assigned_user, assigned_by, it_role_id, assigned_at, is_active)
        VALUES (%(sr_no)s, %(assigned_user)s, %(assigned_by)s, %(it_role_id)s, NOW(), %(is_active)s)
    """

    def _execute_all(conn):
        SINGLE_USER_ROLES = {1, 2, 3, 8, 9}

        for a in assignments:
            if a.get('assign_id'):
                sql = sql_update
                params = {
                    'assign_id': a['assign_id'],
                    'nik': a['nik'],
                    'it_role_id': a['it_role_id'],
                    'assigned_by': assigned_by,
                }
                result = conn.executeDataNoCommit(sql, params)
                if not result.get('status'):
                    return {'status': False, 'data': [], 'msg': result.get('msg', 'Gagal update assignment')}
            else:
                role_id = int(a['it_role_id'])

                # ONLY run the soft-delete check for single-user roles
                if role_id in SINGLE_USER_ROLES:
                    check_res = conn.selectData(sql_check_active, {'sr_no': sr_no, 'it_role_id': role_id})
                    
                    if check_res.get('status') and check_res.get('data'):
                        current_active_nik = check_res['data'][0][0]
                        
                        if current_active_nik == a['nik']:
                            Log.info(f"Assignment Smart Bypass | SR: {sr_no} | Role: {role_id} | NIK {a['nik']} is already active.")
                            continue 
                            
                        sd_params = {
                            'sr_no': sr_no,
                            'it_role_id': role_id,
                            'assigned_by': assigned_by
                        }
                        sd_result = conn.executeDataNoCommit(sql_soft_delete, sd_params)
                        if not sd_result.get('status'):
                            return {'status': False, 'data': [], 'msg': sd_result.get('msg', 'Gagal soft-delete assignment lama')}

                # Standard Insert runs for everyone (Multi-users skip the soft-delete above)
                sql = sql_insert
                params = {
                    'sr_no': sr_no,
                    'assigned_user': a['nik'],
                    'assigned_by': assigned_by,
                    'it_role_id': role_id,
                    'is_active': a.get('is_active', False), # Uses the value assigned in Step 5
                }
                result = conn.executeDataNoCommit(sql, params)
                if not result.get('status'):
                    return {'status': False, 'data': [], 'msg': result.get('msg', 'Gagal upsert assignment')}
                    
        return {'status': True, 'data': [], 'msg': 'Assignment berhasil disimpan.'}

    if shared_conn:
        return _execute_all(shared_conn)

    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=False)
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        result = _execute_all(conn)
        if not result.get('status'):
            raise Exception(result.get('msg'))
        conn._conn.commit()
        return {'status': True, 'data': [], 'msg': 'Assignment berhasil disimpan.'}
    except Exception as e:
        if conn:
            try: conn._conn.rollback()
            except Exception: pass
        Log.error(f'DB Exception | insert_assignments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def delete_assignments_by_ids_model(assign_ids: list, shared_conn=None) -> dict:
    """
    Hapus assignment berdasarkan list assign_id.
    Digunakan oleh IT PMO untuk menghapus assignment tertentu pada SR.
    """
    if not assign_ids:
        return {'status': True, 'data': [], 'msg': 'Tidak ada assignment yang dihapus.'}

    sql = """ 
        UPDATE sr_assignments
        SET deleted_at = NOW(), is_active = FALSE
        WHERE assign_id IN %(assign_ids)s
          AND deleted_at IS NULL
    """
    params = {'assign_ids': tuple(assign_ids)}

    if shared_conn:
        result = shared_conn.executeDataNoCommit(sql, params)
        return result if not result.get('status') else {'status': True, 'data': [], 'msg': 'Assignment dihapus.'}

    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=False)
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        result = conn.executeDataNoCommit(sql, params)
        if not result.get('status'):
            raise Exception(result.get('msg', 'Gagal hapus assignment'))
        conn._conn.commit()
        return {'status': True, 'data': [], 'msg': 'Assignment berhasil dihapus.'}
    except Exception as e:
        if conn:
            try: conn._conn.rollback()
            except Exception: pass
        Log.error(f'DB Exception | delete_assignments_by_ids | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_assignment_by_id_model(assign_id: int) -> dict:
    """Ambil detail satu assignment berdasarkan assign_id."""
    sql = """
        SELECT assign_id, sr_no, assigned_user, it_role_id, is_active
        FROM sr_assignments
        WHERE assign_id = %(assign_id)s
          AND deleted_at IS NULL
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'assign_id': assign_id})
    except Exception as e:
        Log.error(f'DB Exception | get_assignment_by_id | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_active_pic_on_sr_model(sr_no: str, nik: str, current_smk_id: int = None) -> dict:
    """Ambil assignment dimana user is_active=TRUE pada SR ini.
    Jika current_smk_id diberikan, filter hanya role yang relevan untuk phase saat ini."""
    sql = """
        SELECT sa.assign_id, sa.it_role_id, sa.is_active, it.it_role_detail
        FROM sr_assignments sa
        JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.sr_no = %(sr_no)s
          AND sa.assigned_user = %(nik)s
          AND sa.is_active = TRUE
          AND deleted_at IS NULL
    """
    params = {'sr_no': sr_no, 'nik': nik}
    if current_smk_id is not None:
        sql += """
          AND EXISTS (
              SELECT 1 FROM sr_ms_workflow_rules wf
              WHERE wf.allowed_picrole = sa.it_role_id
                AND wf.current_smk_id = %(current_smk_id)s
          )
        """
        params['current_smk_id'] = current_smk_id
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, params)
    except Exception as e:
        Log.error(f'DB Exception | get_active_pic_on_sr | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_pic_handover_candidates_model(sr_no: str, it_role_id: int, exclude_nik: str) -> dict:
    """Ambil user lain di role yang sama yang is_active=FALSE — kandidat penerima handover."""
    sql = """
        SELECT sa.assign_id, sa.assigned_user, COALESCE(k.nama, sa.assigned_user) AS nama
        FROM sr_assignments sa
        LEFT JOIN karyawan_all k ON sa.assigned_user = k.nik
        WHERE sa.sr_no = %(sr_no)s
          AND sa.it_role_id = %(it_role_id)s
          AND sa.assigned_user != %(exclude_nik)s
          AND sa.is_active = FALSE
          AND deleted_at IS NULL
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no, 'it_role_id': it_role_id, 'exclude_nik': exclude_nik})
    except Exception as e:
        Log.error(f'DB Exception | get_pic_handover_candidates | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_all_handover_candidates_model(sr_no: str, active_role_ids: list, exclude_nik: str) -> dict:
    """
    Ambil semua kandidat handover untuk semua active role sekaligus (batch).
    Return kolom: assign_id, assigned_user, nama, it_role_id, it_role_detail
    """
    if not active_role_ids:
        return {'status': True, 'data': [[], []]}
    sql = """
        SELECT sa.assign_id, sa.assigned_user, COALESCE(k.nama, sa.assigned_user) AS nama,
               sa.it_role_id, it.it_role_detail
        FROM sr_assignments sa
        LEFT JOIN karyawan_all k ON sa.assigned_user = k.nik
        JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.sr_no = %(sr_no)s
          AND sa.it_role_id IN %(role_ids)s
          AND sa.assigned_user != %(exclude_nik)s
          AND sa.is_active = FALSE
          AND deleted_at IS NULL
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {
            'sr_no': sr_no,
            'role_ids': tuple(active_role_ids),
            'exclude_nik': exclude_nik
        })
    except Exception as e:
        Log.error(f'DB Exception | get_all_handover_candidates | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def toggle_active_pic_model(sr_no: str, it_role_id: int, target_assign_id: int, shared_conn=None) -> dict:
    """
    Toggle is_active: non-aktifkan semua user di role ini pada SR, lalu aktifkan target_assign_id.
    Harus dijalankan dalam satu transaksi agar tidak ada state di mana semua FALSE atau dua TRUE.
    """
    sql_deactivate = """
        UPDATE sr_assignments SET is_active = FALSE
        WHERE sr_no = %(sr_no)s AND it_role_id = %(it_role_id)s
        AND deleted_at IS NULL
    """
    sql_activate = """
        UPDATE sr_assignments SET is_active = TRUE
        WHERE assign_id = %(assign_id)s
    """
    owns_conn = shared_conn is None
    if owns_conn:
        shared_conn = DatabasePG("supabase", autocommit=False)

    try:
        if not shared_conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': shared_conn.status.get('msg')}

        r1 = shared_conn.executeDataNoCommit(sql_deactivate, {'sr_no': sr_no, 'it_role_id': it_role_id})
        if not r1.get('status'):
            raise Exception(r1.get('msg', 'Gagal deactivate'))

        r2 = shared_conn.executeDataNoCommit(sql_activate, {'assign_id': target_assign_id})
        if not r2.get('status'):
            raise Exception(r2.get('msg', 'Gagal activate'))

        if owns_conn:
            shared_conn._conn.commit()
        return {'status': True, 'data': [], 'msg': 'Toggle is_active berhasil.'}
    except Exception as e:
        if owns_conn:
            try:
                shared_conn._conn.rollback()
            except Exception:
                pass
        Log.error(f'DB Exception | toggle_active_pic | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if owns_conn and shared_conn:
            shared_conn.close()

def get_all_active_pics_for_sr_model(sr_no: str, current_smk_id: int) -> dict:
    """Ambil user yang is_active=TRUE pada SR ini, hanya untuk role yang relevan
    dengan fase saat ini (berdasarkan sr_ms_workflow_rules)."""
    sql = """
        SELECT sa.assigned_user AS nik,
               COALESCE(k.nama, sa.assigned_user) AS nama,
               it.it_role_detail
        FROM sr_assignments sa
        LEFT JOIN karyawan_all k ON sa.assigned_user = k.nik
        JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.sr_no = %(sr_no)s
          AND sa.is_active = TRUE
          AND deleted_at IS NULL
          AND EXISTS (
              SELECT 1 FROM sr_ms_workflow_rules wf
              WHERE wf.allowed_picrole = sa.it_role_id
                AND wf.current_smk_id = %(current_smk_id)s
          )
        ORDER BY it.it_role_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no, 'current_smk_id': current_smk_id})
    except Exception as e:
        Log.error(f'DB Exception | get_all_active_pics_for_sr | Msg: {str(e)}')
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
        JOIN public.sr_ms_it smi ON sa.it_role_id = smi.it_role_id
        WHERE sa.sr_no = %(sr_no)s 
          AND sa.it_role_id IN (1, 2, 3, 8)
          AND deleted_at IS NULL
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