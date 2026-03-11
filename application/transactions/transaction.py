from common.midiconnectserver.midilog import Logger
from flask import flash, jsonify, render_template, session
from ..models import model

Log = Logger()

def get_user_info_trx(nik):
    try:
        data = model.get_user_info_model(nik=nik)
        return data
    except Exception as e:
        Log.error(f'Exception | Get User Info | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def get_plu_container_trx():
    try:
        data = model.get_plu_container_model()
        return data
    except Exception as e:
        Log.error(f'Exception | Get User Info | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}