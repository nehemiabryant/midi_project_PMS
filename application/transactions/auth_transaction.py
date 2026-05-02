from common.midiconnectserver.midilog import Logger
from ..models import user as user_model
from ..utils.converters import parse_single_row

Log = Logger()


def get_user_role_info_trx(nik: str) -> dict:
    """
    Ambil semua role dan permissions user dari DB.
    Return:
      - {'error': False, 'name': [...], 'permissions': [...]}  → berhasil (ada atau tidak di sr_user)
      - {'error': True,  'name': [],   'permissions': []}      → gagal teknis (DB error)
    """
    try:
        result = user_model.get_user_role_info_model(nik)
        if not result.get('status'):
            Log.error(f'get_user_role_info_trx | DB query failed | NIK: {nik} | Msg: {result.get("msg")}')
            return {'error': True, 'name': [], 'permissions': []}

        row = parse_single_row(result)
        if not row:
            return {'error': False, 'name': [], 'permissions': []}

        return {
            'error': False,
            'name': list(row.get('role_names', []) or []),
            'permissions': list(row.get('permissions', []) or [])
        }
    except Exception as e:
        Log.error(f'Exception | get_user_role_info | Msg: {str(e)}')
        return {'error': True, 'name': [], 'permissions': []}
