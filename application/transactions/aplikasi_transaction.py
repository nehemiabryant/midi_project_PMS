from common.midiconnectserver.midilog import Logger
from common.midiconnectserver import DatabasePG
from ..models import aplikasi_model
from ..utils.converters import parse_rows, parse_single_row, convert_to_dicts

Log = Logger()

def get_all_aplikasi_trx() -> dict:
    try:
        result = aplikasi_model.get_all_aplikasi()
        if not result.get('status'):
            return result
        parsed_data = parse_rows(result)
        return {'status': True, 'data': parsed_data}
    except Exception as e:
        Log.error(f'Exception | Get All Aplikasi Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    
def get_aplikasi_name_and_code_trx() -> dict:
    try:
        result = aplikasi_model.get_aplikasi_name_and_code()
        if not result.get('status'):
            return result
        return {'status': True, 'data': parse_rows(result.get('data'))}
    except Exception as e:
        Log.error(f'Exception | Get Aplikasi Name and Code Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    
def insert_aplikasi_trx(raw_data: dict) -> dict:
    try:
        db_params = {
            'apk_kode': raw_data.get('new_apk_kode'),
            'apk_nama': raw_data.get('apk_nama'),
            'apk_url': raw_data.get('apk_url') or None,
            'apk_dev': raw_data.get('apk_dev') or None,
            'apk_opr': raw_data.get('apk_opr') or None
        }

        data = aplikasi_model.insert_aplikasi(db_params)
        if not data.get('status'):
            return data
        
        return {'status': True, 'data': {}, 'msg': 'Application inserted successfully.'}
    except Exception as e:
        Log.error(f'Exception | Insert Aplikasi Trx | Msg: {str(e)}')
        return {'status': False, 'data': {}, 'msg': str(e)}
    
def update_aplikasi_trx(raw_data: dict) -> dict:
    try:
        db_params = {
            'apk_kode': raw_data.get('apk_kode'),
            'new_apk_kode': raw_data.get('new_apk_kode'),
            'apk_nama': raw_data.get('apk_nama'),
            'apk_url': raw_data.get('apk_url') or None,
            'apk_dev': raw_data.get('apk_dev') or None,
            'apk_opr': raw_data.get('apk_opr') or None
        }
        
        if not db_params['new_apk_kode']:
            db_params['new_apk_kode'] = db_params['apk_kode']

        data = aplikasi_model.update_aplikasi(db_params)
        if not data.get('status'):
            return data
        
        return {'status': True, 'data': {}, 'msg': 'Application updated successfully.'}
    except Exception as e:
        Log.error(f'Exception | Update Aplikasi Trx | Msg: {str(e)}')
        return {'status': False, 'data': {}, 'msg': str(e)}