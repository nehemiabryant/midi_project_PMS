from common.midiconnectserver.midilog import Logger
from ..models import user as user_model

Log = Logger()


def get_user_role_info_trx(nik: str) -> dict:
    """
    Ambil role dan permissions user dari DB.
    Return: {'name': str, 'permissions': list[str]}
    Jika user tidak punya role, return nama dan permissions kosong.
    """
    try:
        result = user_model.get_user_role_info_model(nik)
        if not result.get('status'):
            return {'name': '', 'permissions': []}

        raw = result.get('data', [[], []])
        if not raw or len(raw) < 2 or not raw[1]:
            return {'name': '', 'permissions': []}

        headers, rows = raw[0], raw[1]
        row = dict(zip(headers, rows[0]))

        return {
            'name': row.get('approle_name', ''),
            'permissions': list(row.get('permissions', []) or [])
        }
    except Exception as e:
        Log.error(f'Exception | get_user_role_info | Msg: {str(e)}')
        return {'name': '', 'permissions': []}
