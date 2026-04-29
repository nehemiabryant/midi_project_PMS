import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_sr(shared_conn=None) -> dict:
    sql = """
          SELECT r.sr_no, r.req_id, r.name, r.created_at, ka.nama AS requester_name
          FROM public.sr_request r
          JOIN public.karyawan_all ka ON r.req_id = ka.nik
          ORDER BY sr_no ASC
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
        SELECT r.sr_no, r.smk_id, r.ctg_id, c.category, r.maker_id, r.req_id, r.division, r.name, r.module, r.purpose, r.details, 
            r.frequency, r.value, r.value_det, r.num_user
        FROM public.sr_request r
        LEFT JOIN sr_ms_ctg c ON r.ctg_id = c.ctg_id
        WHERE r.sr_no = %(sr_no)s"""
    
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

def update_sr_adjustment(db_params: dict, shared_conn=None) -> dict:
    sql = """
        UPDATE public.sr_request 
        SET 
            ctg_id = %(ctg_id)s, q_id = %(q_id)s, prj_id = %(prj_id)s, status_midikriing = %(status_midikriing)s
        WHERE sr_no = %(sr_no)s
        RETURNING sr_no;
    """

    if shared_conn:
        return shared_conn.selectData(sql, db_params)

    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=True)
        if conn:
            return conn.selectData(sql, db_params)
        else:
            Log.error('DB Error | update_sr_adjustment | Connection failed.')
            return {'status': False, 'data': [], 'msg': 'Database connection failed.'}
    except Exception as e:
        Log.error(f'DB Exception | update_sr_adjustment | Msg: {str(e)}')
        return {'status': False, 'msg': 'Failed to adjust SR'}
    finally:
        if conn: conn.close()

def update_sr_quarter(db_params: dict, shared_conn=None) -> dict:
    """Update the quarter for a specific SR."""
    sql = """
        UPDATE sr_request 
        SET q_id = %(q_id)s
        WHERE sr_no = %(sr_no)s
        RETURNING sr_no;
    """

    if shared_conn:
        result = shared_conn.selectData(sql, db_params)
        return result
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'msg': conn.status.get('msg')}
            
        return conn.selectData(sql, db_params)
    except Exception as e:
        Log.error(f'DB Exception | update_sr_quarter | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: 
            conn.close()

def update_sr_project_status(db_params: dict, shared_conn=None) -> dict:
    """Update the project status for a specific SR."""
    sql = """
        UPDATE sr_request 
        SET prj_id = %(prj_id)s
        WHERE sr_no = %(sr_no)s
        RETURNING sr_no;
    """

    if shared_conn:
        result = shared_conn.selectData(sql, db_params)
        return result
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'msg': conn.status.get('msg')}
            
        return conn.selectData(sql, db_params)
    except Exception as e:
        Log.error(f'DB Exception | update_sr_project_status | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: 
            conn.close()

def update_sr_midikriing_status(db_params: dict, shared_conn=None) -> dict:
    """Update the midikriing status for a specific SR."""
    sql = """
        UPDATE sr_request 
        SET status_midikriing = %(status_midikriing)s
        WHERE sr_no = %(sr_no)s
        RETURNING sr_no;
    """

    if shared_conn:
        result = shared_conn.selectData(sql, db_params)
        return result
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'msg': conn.status.get('msg')}
            
        return conn.selectData(sql, db_params)
    except Exception as e:
        Log.error(f'DB Exception | update_sr_midikriing_status | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: 
            conn.close()

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
    Calculates dynamic progress based on the specific steps available 
    within each phase.
    """
    sql = """
        WITH phase_bounds AS (
            SELECT 
                phase AS phase_name,
                MIN(smk_id) AS min_id
            FROM public.sr_ms_ket
            GROUP BY phase
        ),
        active_data AS (
            SELECT 
                m.phase AS phase_name,
                r.division,
                COUNT(r.sr_no) AS ticket_count,
                ROUND(
                    (COUNT(r.sr_no) * 100.0) / 
                    NULLIF(SUM(COUNT(r.sr_no)) OVER (PARTITION BY r.division), 0)
                ) AS phase_progress
            FROM public.sr_request r
            JOIN public.sr_ms_ket m ON r.smk_id = m.smk_id
            GROUP BY m.phase, r.division
        )
        SELECT 
            pb.phase_name,
            a.division,
            COALESCE(a.ticket_count, 0) AS ticket_count,
            COALESCE(a.phase_progress, 0) AS global_progress
        FROM phase_bounds pb
        LEFT JOIN active_data a ON pb.phase_name = a.phase_name
        ORDER BY pb.min_id ASC, a.division ASC;
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
            CASE
                WHEN r.smk_id < 106 THEN 0
                WHEN task_counts.total IS NULL OR task_counts.total = 0 THEN 0
                ELSE ROUND(task_counts.completed::numeric / task_counts.total * 100)
            END AS ticket_progress
        FROM public.sr_request r
        JOIN public.sr_ms_ket k ON r.smk_id = k.smk_id
        LEFT JOIN (
            SELECT sa.sr_no,
                   COUNT(*) AS total,
                   COUNT(CASE WHEN t.target_date IS NOT NULL AND t.actual_date IS NOT NULL THEN 1 END) AS completed
            FROM sr_task t
            JOIN sr_assignments sa ON t.assign_id = sa.assign_id
            GROUP BY sa.sr_no
        ) task_counts ON r.sr_no = task_counts.sr_no
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
            r.status_midikriing,
            r.prj_id,
            pr.status_project,
            CASE
                WHEN r.smk_id < 106 THEN 0
                WHEN task_counts.total IS NULL OR task_counts.total = 0 THEN 0
                ELSE ROUND(task_counts.completed::numeric / task_counts.total * 100)
            END AS ticket_progress,
            r.q_id,
            q.quarter
        FROM public.sr_request r
        JOIN public.sr_ms_ket k ON r.smk_id = k.smk_id
        JOIN public.sr_ms_ctg c ON r.ctg_id = c.ctg_id
        JOIN public.karyawan_all ka ON r.req_id = ka.nik
        JOIN public.sr_ms_project pr ON r.prj_id = pr.prj_id
        LEFT JOIN public.sr_ms_quarter q ON r.q_id = q.q_id
        LEFT JOIN (
            SELECT sa.sr_no,
                   COUNT(*) AS total,
                   COUNT(CASE WHEN t.target_date IS NOT NULL AND t.actual_date IS NOT NULL THEN 1 END) AS completed
            FROM sr_task t
            JOIN sr_assignments sa ON t.assign_id = sa.assign_id
            GROUP BY sa.sr_no
        ) task_counts ON r.sr_no = task_counts.sr_no
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

def get_all_categories(shared_conn=None) -> dict:
    """
    Fetches all available SR categories from the sr_ms_ctg table.
    """
    sql = """
        SELECT ctg_id, category
        FROM public.sr_ms_ctg
        ORDER BY ctg_id ASC
    """
    
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Connection setup failed.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': 'Failed to connect to database.'}
    except Exception as e:
        Log.error(f'DB Exception | get_all_categories_model | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_all_quarters(shared_conn=None) -> dict:
    """
    Fetches all available quarters from the sr_ms_quarter table.
    """
    sql = """
        SELECT q_id, quarter
        FROM public.sr_ms_quarter
        ORDER BY q_id ASC
    """
    
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Connection setup failed.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': 'Failed to connect to database.'}
    except Exception as e:
        Log.error(f'DB Exception | get_all_quarters_model | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_all_years(shared_conn=None) -> dict:
    sql = """
        SELECT DISTINCT RIGHT(sr_no, 4) AS filter_year 
        FROM public.sr_request 
        WHERE sr_no IS NOT NULL 
        ORDER BY filter_year DESC
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
        Log.error(f'DB Exception | get_all_years | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch year filters'}
    finally:
        if conn: conn.close()

def get_all_departments(shared_conn=None) -> dict:
    sql = """
        SELECT id_dept, departemen AS department_name, nik
        FROM public.master_departemen
        ORDER BY id_dept ASC
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
        Log.error(f'DB Exception | get_all_departments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch department filters'}
    finally:
        if conn: conn.close()

def get_all_sm_from_departments(shared_conn=None) -> dict:
    sql = """
        SELECT md.id_dept, md.departemen AS department_name, md.nik, COALESCE(k.nama, '') AS nama
        FROM public.master_departemen md 
        LEFT JOIN public.karyawan_all k ON md.nik = k.nik
        ORDER BY md.id_dept ASC
    """
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {})

    conn = None
    result = {'status':False, 'data': [], 'msg': 'Invalid parametes.'}
    try:
        conn = DatabasePG("supabase")
        if conn:
            return conn.selectDataHeader(sql, {})
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {"status": False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_all_sm_from_departments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SM from departments'}
    finally:
        if conn: conn.close()

def get_all_project_status(shared_conn=None) -> dict:
    """
    Fetches all available project statuses from the sr_ms_project table.
    """
    sql = """
        SELECT prj_id, status_project
        FROM public.sr_ms_project
        ORDER BY prj_id ASC
    """
    
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Connection setup failed.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': 'Failed to connect to database.'}
    except Exception as e:
        Log.error(f'DB Exception | get_all_project_status | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_filtered_sr_no(db_params: dict, shared_conn=None) -> dict:
    """
    Fetches strictly the IDs for the current page. Extremely lightweight.
    """
    sql = """
        SELECT DISTINCT r.sr_no
        FROM public.sr_request r
        LEFT JOIN public.sr_ms_quarter q ON r.q_id = q.q_id
        LEFT JOIN public.sr_ms_ctg c ON r.ctg_id = c.ctg_id
        LEFT JOIN public.sr_assignments sa
            ON r.sr_no = sa.sr_no
            AND sa.deleted_at IS NULL
            AND sa.is_active = TRUE
        LEFT JOIN public.master_departemen md ON sa.assigned_user = md.nik
        WHERE
            RIGHT(r.sr_no, 4) = COALESCE(%(filter_year)s, TO_CHAR(NOW(), 'YYYY'))
            AND (%(filter_q_id)s IS NULL OR r.q_id = %(filter_q_id)s)
            AND (%(filter_ctg_id)s IS NULL OR r.ctg_id = %(filter_ctg_id)s)
            AND (%(filter_midikriing)s IS NULL OR r.status_midikriing = %(filter_midikriing)s)
            AND (%(filter_dept_id)s IS NULL OR md.id_dept = %(filter_dept_id)s::bigint)
        ORDER BY r.sr_no DESC
    """
    
    if shared_conn: return shared_conn.selectDataHeader(sql, db_params)
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        return conn.selectDataHeader(sql, db_params) if conn else {'status': False, 'data': [], 'msg': 'DB conn failed'}
    except Exception as e:
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_monitoring_counts(sr_list: list, shared_conn=None) -> dict:
    """
    Calculates the global totals based strictly on the provided array of sr_nos.
    All complex filters and JOINs have been removed for maximum performance.
    
    Expected db_params: {'sr_list': ['SR-001', 'SR-002', ...]}
    """
    sql = """
        SELECT 
            COUNT(*) AS total_count,
            COALESCE(SUM(CASE WHEN smk_id = 116 THEN 1 ELSE 0 END), 0) AS count_completed,
            COALESCE(SUM(CASE WHEN smk_id >= 106 AND smk_id < 116 THEN 1 ELSE 0 END), 0) AS count_progress,
            COALESCE(SUM(CASE WHEN smk_id < 106 OR smk_id IS NULL THEN 1 ELSE 0 END), 0) AS count_not_started
        FROM public.sr_request
        WHERE sr_no = ANY(%(sr_list)s)
    """
    
    if shared_conn: return shared_conn.selectDataHeader(sql, {'sr_list': sr_list})
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        return conn.selectDataHeader(sql, {'sr_list': sr_list}) if conn else {'status': False, 'data': [], 'msg': 'DB conn failed'}
    except Exception as e:
        Log.error(f'DB Exception | get_monitoring_counts | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_monitoring_status_time(sr_list: list, shared_conn=None) -> dict:
    sql = """
        SELECT
            COALESCE(SUM(CASE WHEN r.smk_id = 116 THEN 1 ELSE 0 END), 0) AS complete,
            COALESCE(SUM(CASE WHEN r.smk_id >= 101 AND r.smk_id < 116 AND CURRENT_DATE <= COALESCE(t.finish_date, '2099-12-31'::DATE) THEN 1 ELSE 0 END), 0) AS on_time,
            COALESCE(SUM(CASE WHEN r.smk_id >= 101 AND r.smk_id < 116 AND CURRENT_DATE > t.finish_date THEN 1 ELSE 0 END), 0) AS over
        FROM public.sr_request r
        LEFT JOIN public.sr_target_date t ON r.sr_no = t.sr_no AND t.phase_id = 6
        WHERE r.sr_no = ANY(%(sr_list)s)
    """

    if shared_conn: return shared_conn.selectDataHeader(sql, {'sr_list': sr_list})
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        return conn.selectDataHeader(sql, {'sr_list': sr_list}) if conn else {'status': False, 'data': [], 'msg': 'DB conn failed'}
    except Exception as e:
        Log.error(f'DB Exception | get_monitoring_status_time | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_monitoring_status_overview(sr_list: list, shared_conn=None) -> dict:
    sql = """
        SELECT
            COALESCE(SUM(CASE WHEN smk_id = 116 THEN 1 ELSE 0 END), 0) AS completed,
            COALESCE(SUM(CASE WHEN smk_id >= 106 AND smk_id < 116 THEN 1 ELSE 0 END), 0) AS on_progress,
            COALESCE(SUM(CASE WHEN smk_id < 106 OR smk_id IS NULL THEN 1 ELSE 0 END), 0) AS not_started
        FROM public.sr_request
        WHERE sr_no = ANY(%(sr_list)s)
    """

    if shared_conn: return shared_conn.selectDataHeader(sql, {'sr_list': sr_list})
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        return conn.selectDataHeader(sql, {'sr_list': sr_list}) if conn else {'status': False, 'data': [], 'msg': 'DB conn failed'}
    except Exception as e:
        Log.error(f'DB Exception | get_monitoring_status_overview | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_monitoring_overdue_projects(sr_list: list, shared_conn=None) -> dict:
    sql = """
        SELECT
            ROW_NUMBER() OVER(ORDER BY t.finish_date ASC) AS no,
            
            (
                SELECT STRING_AGG(COALESCE(k.nama, sa.assigned_user), ', ')
                FROM public.sr_assignments sa
                LEFT JOIN public.karyawan_all k ON sa.assigned_user = k.nik
                WHERE sa.sr_no = r.sr_no
                  AND sa.is_active = TRUE
                  AND sa.deleted_at IS NULL
                  AND EXISTS (
                      SELECT 1 FROM public.sr_ms_workflow_rules wf
                      WHERE wf.allowed_picrole = sa.it_role_id
                        AND wf.current_smk_id = COALESCE(r.smk_id, 0)
                  )
            ) AS pic_name,
            
            r.sr_no, 
            r.name AS aplikasi, 
            c.category AS tipe, 
            t.finish_date AS target_selesai,
            
            CASE 
                WHEN r.smk_id < 106 OR r.smk_id IS NULL THEN 'Not Started'
                ELSE 'In Progress'
            END AS status
            
        FROM public.sr_request r
        LEFT JOIN public.sr_ms_ctg c ON r.ctg_id = c.ctg_id
        INNER JOIN public.sr_target_date t ON r.sr_no = t.sr_no AND t.phase_id = 6
        
        WHERE r.sr_no = ANY(%(sr_list)s)
          AND COALESCE(r.smk_id, 0) < 116
          AND CURRENT_DATE > t.finish_date
    """

    if shared_conn: return shared_conn.selectDataHeader(sql, {'sr_list': sr_list})
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        return conn.selectDataHeader(sql, {'sr_list': sr_list}) if conn else {'status': False, 'data': [], 'msg': 'DB conn failed'}
    except Exception as e:
        Log.error(f'DB Exception | get_monitoring_overdue_projects | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_monitoring_complete_projects(sr_list: list, shared_conn=None) -> dict:
    sql = """
        SELECT
            ROW_NUMBER() OVER(ORDER BY a.finish_date DESC) AS no,
            
            (
                SELECT STRING_AGG(COALESCE(k.nama, sa.assigned_user), ', ')
                FROM public.sr_assignments sa
                LEFT JOIN public.karyawan_all k ON sa.assigned_user = k.nik
                WHERE sa.sr_no = r.sr_no
                  AND sa.is_active = TRUE
                  AND sa.deleted_at IS NULL
                  AND EXISTS (
                      SELECT 1 FROM public.sr_ms_workflow_rules wf
                      WHERE wf.allowed_picrole = sa.it_role_id
                        AND wf.current_smk_id = 116
                  )
            ) AS pic_name,
            
            r.sr_no, 
            r.name AS aplikasi,
            c.category AS tipe, 
            t.finish_date AS target_selesai,
            
            CASE 
                WHEN a.finish_date > COALESCE(t.finish_date, '2099-12-31'::DATE) THEN 'SELESAI TERLAMBAT'
                ELSE 'TEPAT WAKTU'
            END AS status
            
        FROM public.sr_request r
        LEFT JOIN public.sr_ms_ctg c ON r.ctg_id = c.ctg_id
        LEFT JOIN public.sr_target_date t ON r.sr_no = t.sr_no AND t.phase_id = 6
        LEFT JOIN public.sr_actual_date a ON r.sr_no = a.sr_no AND a.phase_id = 6
        
        WHERE r.sr_no = ANY(%(sr_list)s)
          AND r.smk_id = 116
    """

    if shared_conn: return shared_conn.selectDataHeader(sql, {'sr_list': sr_list})
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        return conn.selectDataHeader(sql, {'sr_list': sr_list}) if conn else {'status': False, 'data': [], 'msg': 'DB conn failed'}
    except Exception as e:
        Log.error(f'DB Exception | get_monitoring_complete_projects | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_monitoring_all_projects(sr_list: list, shared_conn=None) -> dict:
    sql = """
        SELECT
            -- Generates an auto-incrementing row number, newest SRs first
            ROW_NUMBER() OVER(ORDER BY r.sr_no DESC) AS no,
            
            -- Subquery to fetch the current active PIC(s)
            (
                SELECT STRING_AGG(COALESCE(k.nama, sa.assigned_user), ', ')
                FROM public.sr_assignments sa
                LEFT JOIN public.karyawan_all k ON sa.assigned_user = k.nik
                WHERE sa.sr_no = r.sr_no
                  AND sa.is_active = TRUE
                  AND sa.deleted_at IS NULL
                  AND EXISTS (
                      SELECT 1 FROM public.sr_ms_workflow_rules wf
                      WHERE wf.allowed_picrole = sa.it_role_id
                        AND wf.current_smk_id = COALESCE(r.smk_id, 0)
                  )
            ) AS pic_it,
            
            r.sr_no, 
            r.name AS aplikasi,
            r.module AS modul,      -- Replaced 'status' with 'module'
            t.finish_date AS target_selesai,
            c.category AS tipe
            
        FROM public.sr_request r
        LEFT JOIN public.sr_ms_ctg c ON r.ctg_id = c.ctg_id
        LEFT JOIN public.sr_target_date t ON r.sr_no = t.sr_no AND t.phase_id = 6
        
        WHERE r.sr_no = ANY(%(sr_list)s)
    """

    if shared_conn: return shared_conn.selectDataHeader(sql, {'sr_list': sr_list})
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        return conn.selectDataHeader(sql, {'sr_list': sr_list}) if conn else {'status': False, 'data': [], 'msg': 'DB conn failed'}
    except Exception as e:
        Log.error(f'DB Exception | get_monitoring_all_projects | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()