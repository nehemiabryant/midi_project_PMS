from common.midiconnectserver.midilog import Logger
from ..models import karyawan as karyawan_model

Log = Logger()

def search_karyawan_trx(query: str, limit: int = 20, offset: int = 0) -> dict:
    try:
        result = karyawan_model.search_karyawan_model(query, limit, offset)
        if not result.get('status'):
            return result
        raw = result.get('data', [[], []])
        if not raw or len(raw) < 2:
            return {'status': True, 'data': []}
        headers, rows = raw[0], raw[1]
        return {'status': True, 'data': [dict(zip(headers, row)) for row in rows]}
    except Exception as e:
        Log.error(f'Exception | search_karyawan | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def get_karyawan_by_nik_trx(nik: str) -> dict:
    try:
        result = karyawan_model.get_karyawan_by_nik_model(nik)
        if not result.get('status'):
            return result
        raw = result.get('data', [[], []])
        if not raw or len(raw) < 2 or not raw[1]:
            return {'status': False, 'data': [], 'msg': 'Karyawan tidak ditemukan'}
        headers, rows = raw[0], raw[1]
        return {'status': True, 'data': dict(zip(headers, rows[0]))}
    except Exception as e:
        Log.error(f'Exception | get_karyawan_by_nik | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}