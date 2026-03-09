import traceback, pandas as pd
from common.midiconnectserver import DatabaseORA, DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_user_info_model(nik):
    sql = f"""
        SELECT ka.nik, ka.nama, ka.email || '@' || ka.domain AS email
        FROM karyawan_all ka
        WHERE nik = :nik
    """
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("DB_MAGANG")
        if conn:
            result = conn.selectDataHeader(sql, {'nik': nik})
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