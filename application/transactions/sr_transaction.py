from common.midiconnectserver.midilog import Logger
from flask import flash, jsonify, render_template, session
from ..models import sr_model

Log = Logger()

def sr_request_trx(raw_data: dict) -> dict:
    try:
        db_params = {
            'ctg_id': raw_data.get('kategori_sr'),
            'req_id': raw_data.get('requester'),
            'division': raw_data.get('divisi'),
            'name': raw_data.get('nama_aplikasi'),
            'module': raw_data.get('modul'),
            'purpose': raw_data.get('tujuan'),
            'details': raw_data.get('detail_permohonan'),
            'frequency': raw_data.get('frequency'),
            'value': raw_data.get('values'),
            'value_det': raw_data.get('keterangan_values'),
        }

        # Validate/Format the number of users
        num_user_str = raw_data.get('number_of_user')
        if num_user_str and num_user_str.isdigit():
            db_params['num_user'] = int(num_user_str)
        else:
            db_params['num_user'] = 0

        data = sr_model.create_sr(db_params)
        return data
    except Exception as e:
        Log.error(f'Exception | Get User Info | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}