import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_sr() -> dict:
    sql = """
        SELECT sr_no,ctg_id, req_id, division, name, module, purpose, details, 
            frequency, value, value_det, num_user
        FROM public.sr_request
    """
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

def get_my_sr(nik: str) -> dict:
    sql = """
        SELECT sr_no,ctg_id, req_id, division, name, module, purpose, details, 
            frequency, value, value_det, num_user
        FROM public.sr_request
        WHERE req_id = %(nik)s
    """
    conn = None
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

def create_sr(db_params: dict) -> dict:
    sql = """
        INSERT INTO public.sr_request (
            sr_no, ctg_id, req_id, division, name, module, purpose, 
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
            %(ctg_id)s, %(req_id)s, %(division)s, %(name)s, %(module)s, %(purpose)s, 
            %(details)s, %(frequency)s, %(value)s, %(value_det)s, %(num_user)s, NOW()
        )
        RETURNING sr_no;
    """

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
        Log.error(f'DB Exception | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn:
            conn.close()

def get_sr_by_no(sr_no: str) -> dict:
    sql = """
        SELECT sr_no, ctg_id, req_id, division, name, module, purpose, details, 
            frequency, value, value_det, num_user
        FROM public.sr_request WHERE sr_no = %(sr_no)s"""
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

def update_sr(db_params: dict) -> dict:
    # Query to UPDATE existing data based on the sr_no
    sql = """
        UPDATE public.sr_request 
        SET 
            ctg_id = %(ctg_id)s, name = %(name)s, module = %(module)s, purpose = %(purpose)s, 
            details = %(details)s, frequency = %(frequency)s, value = %(value)s, 
            value_det = %(value_det)s, num_user = %(num_user)s
        WHERE sr_no = %(sr_no)s;
    """
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            # Use executeData because it has the COMMIT command!
            result = conn.executeData(sql, db_params)
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | update_sr | Msg: {str(e)}')
        return {'status': False, 'msg': 'Failed to update SR'}
    finally:
        if conn: conn.close()