import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

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
        RETURNING sr_no; -- Return the generated sr_no so you can show it to the user
    """
    
    # ... your DatabasePG execution code remains exactly the same ...

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("DB_MAGANG")
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

def get_plu_container_model():
    sql = f"""
        select * from amu_plu_container_t
    """
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("DB_MAGANG")
        if conn:
            result = conn.selectHeader(sql)
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