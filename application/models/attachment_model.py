import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_next_iteration(sr_no: str, attach_ctg: int) -> int:
    sql = """
        SELECT COALESCE(MAX(iteration), 0) + 1 AS next_iter
        FROM public.sr_attachments
        WHERE sr_no = %(sr_no)s AND attach_ctg = %(attach_ctg)s
    """
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectData(sql, {'sr_no': sr_no, 'attach_ctg': attach_ctg})
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

def insert_attachment(db_params: dict) -> dict:
    sql = """
        INSERT INTO public.sr_attachments (sr_no, attach_ctg, file_url, iteration)
        VALUES (%(sr_no)s, %(attach_ctg)s, %(file_url)s, %(iteration)s)
    """
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.executeData(sql, db_params) # executeData has autocommit handling
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | insert_attachment | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()

def get_latest_attachments(sr_no: str) -> dict:
    # A clever query to fetch ONLY the highest iteration for each category!
    sql = """
        SELECT attach_ctg, file_url
        FROM public.sr_attachments a
        WHERE sr_no = %(sr_no)s
          AND iteration = (
              SELECT MAX(iteration)
              FROM public.sr_attachments b
              WHERE b.sr_no = a.sr_no AND b.attach_ctg = a.attach_ctg
          )
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
        Log.error(f'DB Exception | get_latest_attachments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()