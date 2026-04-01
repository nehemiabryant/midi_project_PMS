import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_sr(shared_conn=None) -> dict:
    sql = """
        SELECT sr_no, smk_id, ctg_id, maker_id, req_id, division, name, module, purpose, details, 
            frequency, value, value_det, num_user
        FROM public.sr_request
    """

    if shared_conn:
        result = shared_conn.selectHeader(sql)
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectHeader(sql)
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_sr | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SR data'}
    finally:
        if conn: conn.close()

def get_my_sr(nik: str, shared_conn=None) -> dict:
    sql = """
        SELECT r.sr_no, r.smk_id, r.ctg_id, r.maker_id, r.req_id, r.division, r.name, r.module,
               r.purpose, r.details, r.frequency, r.value, r.value_det, r.num_user,
               COALESCE(s.smk_ket, 'Draft') AS smk_ket
        FROM public.sr_request r
        LEFT JOIN sr_ms_ket s ON r.smk_id = s.smk_id
        WHERE r.req_id = %(nik)s AND r.smk_id = 101
    """

    if shared_conn:
        result = shared_conn.selectDataHeader(sql, {'nik': nik})
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'nik': nik})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_sr | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SR data'}
    finally:
        if conn: conn.close()

def create_sr(db_params: dict, shared_conn=None) -> dict:
    sql = """
        INSERT INTO public.sr_request (
            sr_no, smk_id, ctg_id, maker_id, req_id, division, name, module, purpose, 
            details, frequency, value, value_det, num_user, created_at
        )
        VALUES (
            (
                SELECT 
                    TO_CHAR(COALESCE(MAX(SPLIT_PART(sr_no, '/', 1)::INTEGER), 0) + 1, 'FM0000') 
                    || '/SR/MUI-IT/SZ01/' || TO_CHAR(NOW(), 'YYYY')
                FROM public.sr_request
                WHERE sr_no LIKE '%%/SR/MUI-IT/SZ01/' || TO_CHAR(NOW(), 'YYYY')
            ),
            %(smk_id)s, %(ctg_id)s, %(maker_id)s, %(req_id)s, %(division)s, %(name)s, %(module)s, %(purpose)s, 
            %(details)s, %(frequency)s, %(value)s, %(value_det)s, %(num_user)s, NOW()
        )
        RETURNING sr_no;
    """

    if shared_conn:
        result = shared_conn.selectData(sql, db_params)
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase", autocommit=True)
        if conn:
            result = conn.selectData(sql, db_params)
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()

def get_sr_by_no(sr_no: str, shared_conn=None) -> dict:
    sql = """
        SELECT sr_no, smk_id, ctg_id, maker_id, req_id, division, name, module, purpose, details, 
            frequency, value, value_det, num_user
        FROM public.sr_request WHERE sr_no = %(sr_no)s"""
    
    if shared_conn:
        result = shared_conn.selectDataHeader(sql, {'sr_no': sr_no})
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'sr_no': sr_no})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_sr_by_id | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SR'}
    finally:
        if conn: conn.close()

def update_sr(db_params: dict, shared_conn=None) -> dict:
    sql = """
        UPDATE public.sr_request 
        SET 
            ctg_id = %(ctg_id)s, name = %(name)s, module = %(module)s, purpose = %(purpose)s, 
            details = %(details)s, frequency = %(frequency)s, value = %(value)s, 
            value_det = %(value_det)s, num_user = %(num_user)s
        WHERE sr_no = %(sr_no)s
        RETURNING sr_no;
    """

    if shared_conn:
        result = shared_conn.selectData(sql, db_params)
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase", autocommit=True)
        if conn:
            result = conn.selectData(sql, db_params)
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | update_sr | Msg: {str(e)}')
        return {'status': False, 'msg': 'Failed to update SR'}
    finally:
        if conn: conn.close()

def update_sr_prog(db_params: dict, shared_conn=None) -> dict:
    sql = """
        UPDATE sr_request 
        SET smk_id = %(smk_id)s
        WHERE sr_no = %(sr_no)s"""
    
    if shared_conn:
        result = shared_conn.executeDataNoCommit(sql, db_params)
        return result
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.executeData(sql, db_params)
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | update_sr_prog | Msg: {str(e)}')
        return {'status': False, 'msg': 'Failed to update SR'}
    finally:
        if conn: conn.close()

def get_sr_requester(sr_no: str, shared_conn=None) -> str:
    """Gets the original requester's NIK so we can find their manager."""
    sql = "SELECT req_id FROM public.sr_request WHERE sr_no = %(sr_no)s"
    
    if shared_conn:
        result = shared_conn.selectData(sql, {'sr_no': sr_no})
        if result.get('status') and result.get('data'):
            return result['data'][0][0]

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectData(sql, {'sr_no': sr_no})
            if result.get('status') and result.get('data'):
                return result['data'][0][0]  # Return the req_id
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
    except Exception as e:
        Log.error(f'DB Exception | get_sr_requester | Msg: {str(e)}')
    finally:
        if conn: conn.close()

    return None  # Return None if requester not found or error occurred

def get_dashboard_top_cards(shared_conn=None) -> dict:
    """Calculates the high-level totals for the top dashboard cards."""
    sql = """
        SELECT 
            COUNT(*) AS total_sr,
            COUNT(CASE WHEN m.phase != 'Takeout' AND m.phase != 'RO' THEN 1 END) AS active_sr,
            COUNT(CASE WHEN m.phase = 'RO' THEN 1 END) AS completed_sr,
            COUNT(CASE WHEN m.phase = 'Takeout' THEN 1 END) AS overdue_sr
        FROM public.sr_request r
        JOIN public.sr_ms_ket m ON r.smk_id = m.smk_id;
    """
    
    if shared_conn:
        result = shared_conn.selectDataHeader(sql, {})
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_dashboard_top_cards | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SR'}
    finally:
        if conn: conn.close()

def get_dashboard_grid(shared_conn=None) -> dict:
    """
    Uses a CTE to calculate global division progress (excluding 'Takeout'),
    then groups active tickets by phase and division.
    """
    sql = """
        WITH division_progress AS (
            -- STEP A: Calculate global progress per division 
            -- (smk_id - 100) gives us the current step out of 16.
            SELECT 
                r.division,
                ROUND((SUM(r.smk_id - 100) / (COUNT(r.sr_no) * 16.0)) * 100) AS global_progress
            FROM public.sr_request r
            JOIN public.sr_ms_ket m ON r.smk_id = m.smk_id
            WHERE m.phase != 'Takeout'
            GROUP BY r.division
        )
        
        -- STEP B & C: Group by phase and join the pre-calculated progress!
        SELECT 
            m.phase AS phase_name,
            r.division,
            COUNT(r.sr_no) AS ticket_count,
            dp.global_progress
        FROM public.sr_request r
        JOIN public.sr_ms_ket m ON r.smk_id = m.smk_id
        JOIN division_progress dp ON r.division = dp.division
        WHERE m.phase != 'Takeout'
        GROUP BY m.phase, r.division, dp.global_progress
        ORDER BY m.phase ASC, r.division ASC;
    """

    if shared_conn:
        result = shared_conn.selectDataHeader(sql, {})
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_dashboard_grid | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SR'}
    finally:
        if conn: conn.close()

def get_srs_by_phase(phase_name: str, shared_conn=None) -> dict:
    """
    Fetches lightweight SR data for the Master-Detail sidebar based on the macro-phase.
    """
    sql = """
        SELECT 
            r.sr_no,
            r.name AS app_name,
            r.division,
            k.smk_ket AS current_status,
            r.smk_id,
            -- Calculate individual ticket progress (Step 1 to 16)
            LEAST(GREATEST(ROUND(((r.smk_id - 100) / 16.0) * 100), 0), 100) AS ticket_progress
        FROM public.sr_request r
        JOIN public.sr_ms_ket k ON r.smk_id = k.smk_id
        WHERE k.phase = %(phase_name)s
        ORDER BY r.sr_no ASC; 
    """
    
    if shared_conn:
        result = shared_conn.selectDataHeader(sql, {'phase_name': phase_name})
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'phase_name': phase_name})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_srs_by_phase | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SR'}
    finally:
        if conn: conn.close()

def get_sr_detail(sr_no: str, shared_conn=None) -> dict:
    """
    Fetches the comprehensive details of a single SR ticket.
    """
    sql = """
        SELECT 
            r.sr_no,
            r.name AS app_name,
            r.ctg_id,
            c.category AS ctg_name,
            r.req_id,
            ka.nama AS requester_name,
            r.division,
            r.module,
            r.purpose,
            r.details,
            r.frequency,
            r.value,
            r.value_det,
            r.num_user,
            k.smk_ket AS current_status,
            r.smk_id,
            LEAST(GREATEST(ROUND(((r.smk_id - 100) / 16.0) * 100), 0), 100) AS ticket_progress
        FROM public.sr_request r
        JOIN public.sr_ms_ket k ON r.smk_id = k.smk_id
        JOIN public.sr_ms_ctg c ON r.ctg_id = c.ctg_id
        JOIN public.karyawan_all ka ON r.req_id = ka.nik
        WHERE r.sr_no = %(sr_no)s
        LIMIT 1;
    """
    
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {'sr_no': sr_no})

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'sr_no': sr_no})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_sr_detail | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SR detail'}
    finally:
        if conn: conn.close()