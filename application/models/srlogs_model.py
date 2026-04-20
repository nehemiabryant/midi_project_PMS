import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_next_iteration(sr_no: str, smk_id: int, shared_conn=None) -> int:
    sql = """
        SELECT COALESCE(MAX(iteration), 0) + 1 AS next_iter
        FROM public.sr_logs
        WHERE sr_no = %(sr_no)s AND smk_id = %(smk_id)s
    """

    if shared_conn:
        result = shared_conn.selectData(sql, {'sr_no': sr_no, 'smk_id': smk_id})
        if result.get('status') and result.get('data'):
            return result['data'][0][0]

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectData(sql, {'sr_no': sr_no, 'smk_id': smk_id})
            if result.get('status') and result.get('data'):
                return result['data'][0][0] 
            else:
                Log.error(f'DB Error | Msg: {result.get("msg")}')
                return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_next_iteration | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()

def get_sr_logs(sr_no: str, shared_conn=None) -> dict:
    sql = """
        SELECT logs_id, sr_no, smk_id, action_by, iteration, started_at, finished_at, created_at
        FROM public.sr_logs
        WHERE sr_no = %(sr_no)s
        ORDER BY logs_id ASC
    """

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
        Log.error(f'DB Exception | get_sr_logs | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch SR logs'}
    finally:
        if conn: conn.close()

def create_sr_log(db_params: dict, shared_conn=None) -> dict:
    sql = """
        INSERT INTO public.sr_logs (
            sr_no, smk_id, action_by, iteration, started_at, created_at
        )
        VALUES (
            %(sr_no)s, %(smk_id)s, %(action_by)s, %(iteration)s, NOW(), NOW()
        )
    """

    if shared_conn:
        result = shared_conn.executeDataNoCommit(sql, db_params)
        return result

    conn = None
    result = {'status': False, 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase", autocommit=True)
        if conn:
            result = conn.executeData(sql, db_params)
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | create_sr_log | Msg: {str(e)}')
        return {'status': False, 'msg': 'Failed to create SR log'}
    finally:
        if conn: conn.close()

def update_sr_log(logs_id: int, shared_conn=None) -> dict:
    sql = """
        UPDATE public.sr_logs 
        SET finished_at = NOW()
        WHERE logs_id = %(logs_id)s;
    """

    if shared_conn:
        result = shared_conn.executeDataNoCommit(sql, {'logs_id': logs_id})
        return result

    conn = None
    result = {'status': False, 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.executeData(sql, {'logs_id': logs_id})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | update_sr_log | Msg: {str(e)}')
        return {'status': False, 'msg': 'Failed to update SR log'}
    finally:
        if conn: conn.close()

def get_sr_documentation_logs(sr_no: str, shared_conn=None) -> dict:
    """
    Fetches a clean, un-bloated timeline for non-IT users.
    Squishes multiple iterations down into a single Start and Finish date per phase.
    """
    sql = """
        SELECT 
            smk_id,
            MIN(started_at) AS official_start_date, -- Gets the start of Iteration 1
            MAX(finished_at) AS official_finish_date -- Gets the finish of the final Iteration
        FROM public.sr_logs
        WHERE sr_no = %(sr_no)s
        GROUP BY smk_id
        ORDER BY smk_id ASC
    """

    if shared_conn:
        result = shared_conn.selectDataHeader(sql, {'sr_no': sr_no})
        return result

    conn = None
    result = {'status': False, 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'sr_no': sr_no})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_sr_docs | Msg: {str(e)}')
        return {'status': False, 'msg': 'Failed to update SR log'}
    finally:
        if conn: conn.close()

def get_active_log_id(sr_no: str, shared_conn=None) -> dict:
    """
    Fetches the chronologically latest log.
    Returns both the logs_id and the smk_id so we can detect database drift.
    """
    sql = """
        SELECT logs_id, smk_id 
        FROM public.sr_logs 
        WHERE sr_no = %(sr_no)s 
        ORDER BY logs_id DESC 
        LIMIT 1;
    """
    
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
            return None
    except Exception as e:
        Log.error(f'DB Exception | get_active_log_id | Msg: {str(e)}')
        return None
    finally:
        if conn: conn.close()

def sync_actual_date_from_logs(sr_no: str, smk_id: int, shared_conn=None) -> dict:
    """
    Checks if the log belongs to a mapped phase. If so, calculates min/max 
    from sr_logs and upserts the result into sr_actual_date.
    """
    # 1. Map smk_id (from sr_logs) to phase_id (for sr_actual_date)
    phase_mapping = {
        106: 1,
        109: 2,
        111: 3,
        113: 4,
        115: 5,
        116: 6
    }

    # 2. Guard Clause: If the log isn't one of these 6 phases, we don't sync it.
    if smk_id not in phase_mapping:
        # Return True so we don't break the parent transaction; it's an expected skip.
        return {'status': True, 'msg': f'smk_id {smk_id} is not mapped to a phase. Sync skipped.'}

    phase_id = phase_mapping[smk_id]

    # 3. Proceed with the sync using BOTH IDs
    sql = """
        INSERT INTO sr_actual_date (sr_no, phase_id, start_date, finish_date)
        SELECT 
            %(sr_no)s,
            %(phase_id)s,
            (ARRAY_AGG(started_at ORDER BY logs_id ASC))[1],
            (ARRAY_AGG(finished_at ORDER BY logs_id DESC))[1]
        FROM sr_logs
        WHERE sr_no = %(sr_no)s AND smk_id = %(smk_id)s
        ON CONFLICT (sr_no, phase_id) 
        DO UPDATE SET 
            start_date = EXCLUDED.start_date,
            finish_date = EXCLUDED.finish_date;
    """
    
    params = {
        'sr_no': sr_no, 
        'phase_id': phase_id, 
        'smk_id': smk_id
    }
    
    # Use shared connection if part of an existing transaction
    if shared_conn:
        return shared_conn.executeDataNoCommit(sql, params)
        
    # Standalone execution fallback
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'): 
            return {'status': False, 'msg': conn.status.get('msg')}
            
        return conn.executeData(sql, params)
    except Exception as e:
        Log.error(f'DB Exception | sync_actual_date_from_logs | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: 
            conn.close()

def get_actual_date(sr_no: str) -> dict:                                                                                                                                                                             
    """ Get all actual_date for a given SR """                                                                                 
    sql = """                                                                                                                                                                                                        
        SELECT 
            m.phase_id, 
            m.phase_detail, 
            a.start_date, 
            a.finish_date
        FROM 
            sr_ms_phase m
        LEFT JOIN 
            sr_actual_date a ON m.phase_id = a.phase_id AND a.sr_no = %(sr_no)s
        ORDER BY 
            m.phase_id ASC;                                                                                                  
    """        
    conn = None                                                                                                                                                                                                      
    try:        
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):                                                                                                                                                                            
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}                                                                                                                                      
        return conn.selectDataHeader(sql, {'sr_no': sr_no})                                                                                                                                                          
    except Exception as e:                                                                                                                                                                                           
        Log.error(f'DB Exception | get_actual_date | Msg: {str(e)}')                                                                                                                                           
        return {'status': False, 'data': [], 'msg': str(e)}                                                                                                                                                          
    finally:
        if conn: conn.close()  

def upsert_actual_date(sr_no: str, phase_id: int, start_date: str, finish_date: str, shared_conn=None) -> dict:
    """Upsert actual dates for a specific SR and Phase."""
    sql = """
        INSERT INTO sr_actual_date (sr_no, phase_id, start_date, finish_date)
        VALUES (%(sr_no)s, %(phase_id)s, %(start_date)s, %(finish_date)s)
        ON CONFLICT (sr_no, phase_id) 
        DO UPDATE SET 
            start_date = EXCLUDED.start_date,
            finish_date = EXCLUDED.finish_date;
    """
    
    # Handle empty strings from the frontend, converting them to None (NULL in DB)
    params = {
        'sr_no': sr_no,
        'phase_id': phase_id,
        'start_date': start_date if start_date else None,
        'finish_date': finish_date if finish_date else None
    }

    if shared_conn:
        result = shared_conn.executeDataNoCommit(sql, params)
        return result
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'msg': conn.status.get('msg')}
            
        return conn.executeData(sql, params)
    except Exception as e:
        Log.error(f'DB Exception | upsert_actual_date | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: 
            conn.close()

def get_target_date(sr_no: str) -> dict:                                                                                                        
    """ Get all target_date """                                                           
    sql = """                                                                                                                                             
        SELECT 
            m.phase_id, m.phase_detail, t.start_date, t.finish_date
        FROM 
            sr_ms_phase m
        LEFT JOIN 
            sr_target_date t ON m.phase_id = t.phase_id AND t.sr_no = %(sr_no)s
        ORDER BY 
            m.phase_id ASC;                                                                                        
    """         
    conn = None                                                                                                                                           
    try:        
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):                                                                                                                 
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}                                                                           
        return conn.selectDataHeader(sql, {'sr_no': sr_no})                                                                                               
    except Exception as e:                                                                                                                                
        Log.error(f'DB Exception | get_all_target_date | Msg: {str(e)}')                                                                                  
        return {'status': False, 'data': [], 'msg': str(e)}                                                                                               
    finally:
        if conn: conn.close()  

def upsert_target_date(sr_no: str, phase_id: int, start_date: str, finish_date: str, shared_conn=None) -> dict:
    """Upsert target dates for a specific SR and Phase."""
    sql = """
        INSERT INTO sr_target_date (sr_no, phase_id, start_date, finish_date)
        VALUES (%(sr_no)s, %(phase_id)s, %(start_date)s, %(finish_date)s)
        ON CONFLICT (sr_no, phase_id) 
        DO UPDATE SET 
            start_date = EXCLUDED.start_date,
            finish_date = EXCLUDED.finish_date;
    """
    
    # Handle empty strings from the frontend, converting them to None (NULL in DB)
    params = {
        'sr_no': sr_no,
        'phase_id': phase_id,
        'start_date': start_date if start_date else None,
        'finish_date': finish_date if finish_date else None
    }

    if shared_conn:
        result = shared_conn.executeDataNoCommit(sql, params)
        return result
    
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'msg': conn.status.get('msg')}
            
        # Using your executeData wrapper!
        return conn.executeData(sql, params)
    except Exception as e:
        Log.error(f'DB Exception | upsert_target_date | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: 
            conn.close()