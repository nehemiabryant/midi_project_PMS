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
        SELECT sr_no, smk_id, ctg_id, maker_id, req_id, division, name, module, purpose, details, 
            frequency, value, value_det, num_user
        FROM public.sr_request
        WHERE req_id = %(nik)s
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