from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_all_aplikasi() -> dict:
    sql = """
        SELECT apk_kode, apk_nama, apk_url, apk_dev, apk_opr
        FROM public.master_aplikasi
        ORDER BY created_at ASC
    """

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
        Log.error(f'DB Exception | get_all_apps | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch all application data'}
    finally:
        if conn: conn.close()

def get_aplikasi_name_and_code() -> dict:
    sql = """
        SELECT apk_kode, apk_nama
        FROM public.master_aplikasi
        ORDER BY created_at ASC
    """

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
        Log.error(f'DB Exception | get_aplikasi_name_and_code | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Failed to fetch application name and code'}
    finally:
        if conn: conn.close()

def insert_aplikasi(db_params: dict) -> dict:
    sql = """
        INSERT INTO public.master_aplikasi (apk_kode, apk_nama, apk_url, apk_dev, apk_opr)
        VALUES (%(apk_kode)s, %(apk_nama)s, %(apk_url)s, %(apk_dev)s, %(apk_opr)s)
    """

    conn = None
    result = {'status': False, 'data': None, 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.executeData(sql, db_params)
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': None, 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | insert_aplikasi | Msg: {str(e)}')
        return {'status': False, 'data': None, 'msg': 'Failed to insert application data'}
    finally:
        if conn: conn.close()

def update_aplikasi(db_params: dict) -> dict:
    sql = """
        UPDATE public.master_aplikasi
        SET apk_kode = %(new_apk_kode)s, apk_nama = %(apk_nama)s, apk_url = %(apk_url)s, apk_dev = %(apk_dev)s, apk_opr = %(apk_opr)s
        WHERE apk_kode = %(apk_kode)s
    """

    conn = None
    result = {'status': False, 'data': None, 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.executeData(sql, db_params)
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': None, 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | update_aplikasi | Msg: {str(e)}')
        return {'status': False, 'data': None, 'msg': 'Failed to update application data'}
    finally:
        if conn: conn.close()