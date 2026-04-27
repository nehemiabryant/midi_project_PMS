from common.midiconnectserver.midilog import Logger
from ..models import user as user_model
from ..utils.converters import parse_single_row

Log = Logger()


def get_user_role_info_trx(nik: str) -> dict:
    """
    Ambil semua role dan permissions user dari DB. Return: {'name': list[str], 'permissions': list[str]}
    """
    try:
        result = user_model.get_user_role_info_model(nik)
        row = parse_single_row(result)
        if not row:
            return {'name': [], 'permissions': []}

        return {
            'name': list(row.get('role_names', []) or []),
            'permissions': list(row.get('permissions', []) or [])
        }
    except Exception as e:
        Log.error(f'Exception | get_user_role_info | Msg: {str(e)}')
        return {'name': [], 'permissions': []}
