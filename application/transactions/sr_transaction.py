from common.midiconnectserver.midilog import Logger
from ..models import sr_model, karyawan
from ..utils import tokenization, converters
from . import attachment_transaction

Log = Logger()

def get_all_sr_trx() -> dict:
    try:
        # 1. Fetch the raw data from the model
        db_result = sr_model.get_sr() 
        
        if not db_result.get('status'):
            return db_result

        # 2. Extract the headers and rows from the nested list
        raw_data = db_result.get('data', [[], []])
        if not raw_data or len(raw_data) < 2:
            return {'status': True, 'data': []} # Return empty if no data

        headers = raw_data[0]
        rows = raw_data[1]

        # 3. Zip them together into a list of dictionaries!
        # This turns [['id', 'name'], [(1, 'Budi')]] into [{'id': 1, 'name': 'Budi'}]
        formatted_list = []
        for row in rows:
            #formatted_list.append(dict(zip(headers, row)))
            formatted_list.append(converters.convert_to_dicts([row], headers)[0]) # Convert single row to dict

        return {'status': True, 'data': formatted_list}
    except Exception as e:
        Log.error(f'Exception | Get All SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    
def get_my_sr_trx(nik: str) -> dict:
    try:
        # 1. Fetch the raw data from the model
        db_result = sr_model.get_my_sr(nik) 
        
        if not db_result.get('status'):
            return db_result

        # 2. Extract the headers and rows from the nested list
        raw_data = db_result.get('data', [[], []])
        if not raw_data or len(raw_data) < 2:
            return {'status': True, 'data': []} # Return empty if no data

        headers = raw_data[0]
        rows = raw_data[1]

        # 3. Zip them together into a list of dictionaries!
        # This turns [['id', 'name'], [(1, 'Budi')]] into [{'id': 1, 'name': 'Budi'}]
        formatted_list = []
        for row in rows:
            row_dict = dict(zip(headers, row))
        
            row_dict['token'] = tokenization.encrypt_id(row_dict['sr_no'])

            formatted_list.append(row_dict)

        return {'status': True, 'data': formatted_list}
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
        
        if not db_result.get('status') or not db_result.get('data') or len(db_result['data']) < 2:
            return db_result

        headers = db_result['data'][0]
        rows = db_result['data'][1]

        if not rows:
            return {'status': False, 'data': [], 'msg': 'Service Request not found.'}

        sr_list = converters.convert_to_dicts(rows, headers)
        
        sr_dict = sr_list[0] 

        req_nik = sr_dict.get('req_id', '')
        maker_nik = sr_dict.get('maker_id', '')
        req_name = ''
        maker_name = ''


        if req_nik:
            req_result = karyawan.get_karyawan_nama_by_nik(req_nik)
            if isinstance(req_result, str):
                req_name = req_result

        if maker_nik:
            maker_result = karyawan.get_karyawan_nama_by_nik(maker_nik)
            if isinstance(maker_result, str):
                maker_name = maker_result

        sr_dict['user_info'] = {
            'maker': {
                'nik': maker_nik,
                'name': maker_name
            },
            'requester': {
                'nik': req_nik,
                'name': req_name
            }
        }

        attachments = attachment_transaction.get_attachments_for_view(sr_no)

        sr_dict['attachments'] = attachments

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