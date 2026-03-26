from common.midiconnectserver.midilog import Logger
from ..models import karyawan as karyawan_model
from ..utils.converters import parse_rows, parse_single_row

Log = Logger()

def search_karyawan_trx(query: str, limit: int = 20, offset: int = 0) -> dict:
    try:
        result = karyawan_model.search_karyawan_model(query, limit, offset)
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_rows(result)}
    except Exception as e:
        Log.error(f'Exception | search_karyawan | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def get_karyawan_by_nik_trx(nik: str) -> dict:
    try:
        result = karyawan_model.get_karyawan_by_nik_model(nik)
        if not result.get('status'):
            return result
        data = parse_single_row(result)
        if not data:
            return {'status': False, 'data': [], 'msg': 'Karyawan tidak ditemukan'}
        return {'status': True, 'data': data}
    except Exception as e:
        Log.error(f'Exception | get_karyawan_by_nik | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}