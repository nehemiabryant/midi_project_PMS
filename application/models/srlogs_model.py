import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_next_iteration(sr_no: str, smk_id: int) -> int:
    sql = """
        SELECT COALESCE(MAX(iteration), 0) + 1 AS next_iter
        FROM public.sr_logs
        WHERE sr_no = %(sr_no)s AND smk_id = %(smk_id)s
    """
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

def get_sr_logs(sr_no: str) -> dict:
    sql = """
        SELECT logs_id, sr_no, smk_id, action_by, iteration, started_at, finished_at, created_at
        FROM public.sr_logs
        WHERE sr_no = %(sr_no)s
        ORDER BY logs_id ASC
    """
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

def create_sr_log(db_params: dict) -> dict:
    sql = """
        INSERT INTO public.sr_logs (
            sr_no, smk_id, action_by, iteration, started_at, created_at
        )
        VALUES (
            %(sr_no)s, %(smk_id)s, %(action_by)s, %(iteration)s, NOW(), NOW()
        )
    """
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

def update_sr_log(logs_id: int) -> dict:
    sql = """
        UPDATE public.sr_logs
        SET finished_at = NOW()
        WHERE logs_id = %(logs_id)s
    """
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

def get_sr_documentation_logs(sr_no: str) -> dict:
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