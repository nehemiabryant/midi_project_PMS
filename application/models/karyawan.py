from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def search_karyawan_model(query: str, limit: int = 20, offset: int = 0) -> dict:
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}

        if query:
            sql = """
                SELECT nik, nama, jabatan, toko_absen, email
                FROM karyawan_all
                WHERE nik ILIKE %(pattern)s OR nama ILIKE %(pattern)s
                ORDER BY nik
                LIMIT %(limit)s OFFSET %(offset)s
            """
            return conn.selectDataHeader(sql, {'pattern': f'%{query}%', 'limit': limit, 'offset': offset})
        else:
            sql = """
                SELECT nik, nama, jabatan, toko_absen, email
                FROM karyawan_all
                ORDER BY nik
                LIMIT %(limit)s OFFSET %(offset)s
            """
            return conn.selectDataHeader(sql, {'limit': limit, 'offset': offset})
    except Exception as e:
        Log.error(f'DB Exception | search_karyawan | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_karyawan_by_nik_model(nik: str) -> dict:
    sql = """
        SELECT nik, nama, kode_jabatan, jabatan, toko_absen,
                kd_branch, nik_up, nama_up, email, domain, proxy, grade
        FROM karyawan_all
        WHERE nik = %(nik)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'nik': nik})
    except Exception as e:
        Log.error(f'DB Exception | get_karyawan_by_nik | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()