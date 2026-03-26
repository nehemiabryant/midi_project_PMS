from common.midiconnectserver.midilog import Logger
from ..models import sr_model
from ..utils import tokenization
from ..utils.converters import parse_rows, parse_single_row
from . import attachment_transaction

Log = Logger()

def get_all_sr_trx() -> dict:
    try:
        db_result = sr_model.get_sr()
        if not db_result.get('status'):
            return db_result
        return {'status': True, 'data': parse_rows(db_result)}
    except Exception as e:
        Log.error(f'Exception | Get All SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def get_my_sr_trx(nik: str) -> dict:
    try:
        db_result = sr_model.get_my_sr(nik)
        if not db_result.get('status'):
            return db_result

        items = parse_rows(db_result)
        for item in items:
            item['token'] = tokenization.encrypt_id(item['sr_no'])

        return {'status': True, 'data': items}
    except Exception as e:
        Log.error(f'Exception | Get My SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def create_sr_trx(raw_data: dict, files: dict) -> dict:
    try:
        db_params = {
            'ctg_id': raw_data.get('kategori_sr'),
            'smk_id': 101,
            'maker_id': raw_data.get('maker_id'),
            'req_id': raw_data.get('req_id'),
            'division': raw_data.get('division'),
            'name': raw_data.get('nama_aplikasi'),
            'module': raw_data.get('modul'),
            'purpose': raw_data.get('tujuan'),
            'details': raw_data.get('detail_permohonan'),
            'frequency': raw_data.get('frequency'),
            'value': raw_data.get('values'),
            'value_det': raw_data.get('keterangan_values'),
        }

        num_user_str = raw_data.get('number_of_user')
        if num_user_str and num_user_str.isdigit():
            db_params['num_user'] = int(num_user_str)
        else:
            db_params['num_user'] = 0

        data = sr_model.create_sr(db_params)
        if data.get('status'):
            new_sr_no = data['data'][0][0]

            attachment_transaction.upload_and_record_files(new_sr_no, files)

        return data
    except Exception as e:
        Log.error(f'Exception | Create SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def get_edit_sr_trx(sr_no: str) -> dict:
    try:
        db_result = sr_model.get_sr_by_no(sr_no)
        sr_dict = parse_single_row(db_result)
        if not sr_dict:
            return {'status': False, 'data': [], 'msg': 'Service Request not found.'}

        sr_dict['attachments'] = attachment_transaction.get_attachments_for_view(sr_no)

        return {'status': True, 'data': [sr_dict]}
    except Exception as e:
        Log.error(f'Exception | Get Edit SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def update_sr_trx(raw_data: dict, files: dict, sr_no: str) -> dict:
    try:
        db_params = {
            'sr_no': sr_no,
            'req_id': raw_data.get('req_id'),
            'division': raw_data.get('division'),
            'ctg_id': raw_data.get('kategori_sr'),
            'division': raw_data.get('divisi'),
            'name': raw_data.get('nama_aplikasi'),
            'module': raw_data.get('modul'),
            'purpose': raw_data.get('tujuan'),
            'details': raw_data.get('detail_permohonan'),
            'frequency': raw_data.get('frequency'),
            'value': raw_data.get('values'),
            'value_det': raw_data.get('keterangan_values'),
        }

        num_user_str = raw_data.get('number_of_user')
        if num_user_str and num_user_str.isdigit():
            db_params['num_user'] = int(num_user_str)
        else:
            db_params['num_user'] = 0
        
        data = sr_model.update_sr(db_params)
        if data.get('status'):
            new_sr_no = data['data'][0][0]

            attachment_transaction.upload_and_record_files(new_sr_no, files)

        #return sr_model.update_sr(db_params)
        return {'status': True, 'data': data}
        
    except Exception as e:
        Log.error(f'Exception | Update SR Trx | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}