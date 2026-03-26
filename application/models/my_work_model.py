from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

# Oversight role territory — tidak bisa di-derive dari sr_ms_workflow_rules karena
# lingkup monitoring role ini lebih luas dari lingkup aksinya.
# Nilai representasi smk_id di mana role tersebut bisa melihat item di My Work.
# TODO: Pindahkan ke tabel sr_ms_role_territory ketika skema DB diperluas.
_OVERSIGHT_TERRITORY = {
    1: [104],                                                                     # IT GM
    2: [103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116],  # IT PM
    3: [105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116],             # IT SM
    8: [102],                                                                     # Atasan (Manager)
}

def get_role_territory_model() -> dict:
    """
    Bangun mapping {it_role_id: [smk_ids]} dari dua sumber:
    1. PIC roles (4-7+): langsung dari sr_ms_workflow_rules.allowed_picrole + current_smk_id
    2. Oversight roles (1,2,3,8): dari _OVERSIGHT_TERRITORY (tidak bisa di-derive dari DB)
    Return: dict {role_id: [smk_id, ...]}
    """
    sql = """
        SELECT DISTINCT allowed_picrole, current_smk_id
        FROM public.sr_ms_workflow_rules
        WHERE allowed_picrole IS NOT NULL
          AND allowed_picrole NOT IN (1, 2, 3, 8, 9)
        ORDER BY allowed_picrole, current_smk_id
    """
    territory = {}
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            Log.warning(f'Cannot fetch role territory from DB: {conn.status.get("msg")}. Returning oversight territory only.')
            return dict(_OVERSIGHT_TERRITORY)

        result = conn.selectHeader(sql)
        if result.get('status') and result.get('data') and len(result['data']) >= 2:
            headers = result['data'][0]
            rows = result['data'][1]
            for row in rows:
                row_dict = dict(zip(headers, row))
                role_id = int(row_dict['allowed_picrole'])
                smk_id = int(row_dict['current_smk_id'])
                if role_id not in territory:
                    territory[role_id] = []
                if smk_id not in territory[role_id]:
                    territory[role_id].append(smk_id)

        # Merge oversight territory — log warning jika ada overlap (inkonsistensi data)
        for role_id, smk_ids in _OVERSIGHT_TERRITORY.items():
            if role_id in territory:
                Log.warning(f'Role {role_id} ada di PIC territory DB dan _OVERSIGHT_TERRITORY. Nilai oversight akan menggantikan.')
            territory[role_id] = smk_ids

        return territory

    except Exception as e:
        Log.error(f'Exception | get_role_territory_model | Msg: {str(e)}')
        return dict(_OVERSIGHT_TERRITORY)
    finally:
        if conn: conn.close()


def get_my_work_items_model(nik: str) -> dict:
    """
    Ambil semua SR yang di-assign ke user ini beserta role-nya.
    Filter: SR hanya muncul jika smk_id masuk teritori role user pada SR tersebut.
    Territory di-derive secara dinamis dari DB (PIC roles) dan konstanta (oversight roles).
    """
    territory = get_role_territory_model()
    if not territory:
        return {'status': False, 'data': [], 'msg': 'Gagal memuat konfigurasi territory role.'}

    # Build dynamic WHERE condition
    # Aman: role_id adalah integer dari data internal DB (bukan user input)
    # smk_ids tetap menggunakan parameterized query
    conditions = []
    params = {'nik': nik}
    for role_id, smk_ids in territory.items():
        if smk_ids:
            key = f'smk_{role_id}'
            conditions.append(f"(sa.it_role_id = {int(role_id)} AND r.smk_id IN %({key})s)")
            params[key] = tuple(smk_ids)

    territory_filter = "(" + " OR ".join(conditions) + ")" if conditions else "FALSE"

    sql = f"""
        SELECT r.sr_no, r.name, r.module, r.division,
               r.smk_id, COALESCE(s.smk_ket, '') AS smk_ket,
               r.created_at,
               sa.it_role_id, COALESCE(it.it_role_detail, '') AS it_role_detail
        FROM sr_assignments sa
        JOIN sr_request r ON sa.sr_no = r.sr_no
        LEFT JOIN sr_ms_ket s ON r.smk_id = s.smk_id
        LEFT JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.assigned_user = %(nik)s
          AND {territory_filter}
        ORDER BY r.created_at DESC
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, params)
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
