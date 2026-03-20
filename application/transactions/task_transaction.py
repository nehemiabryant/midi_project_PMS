from common.midiconnectserver.midilog import Logger
from ..models import task_model

Log = Logger()


def _parse_single_row(db_result: dict) -> dict | None:
    """Helper: parse selectDataHeader result ke single dict. Return None jika kosong."""
    if not db_result.get('status'):
        return None
    raw = db_result.get('data', [[], []])
    if not raw or len(raw) < 2 or not raw[1]:
        return None
    return dict(zip(raw[0], raw[1][0]))


def _parse_rows(db_result: dict) -> list:
    """Helper: parse selectDataHeader result ke list of dicts."""
    if not db_result.get('status'):
        return []
    raw = db_result.get('data', [[], []])
    if not raw or len(raw) < 2 or not raw[1]:
        return []
    headers = raw[0]
    return [dict(zip(headers, row)) for row in raw[1]]


def _validate_pic_access(nik: str, sr_no: str, it_role_id: int = None) -> dict:
    """
    Validasi apakah user ter-assign pada SR.
    Jika it_role_id diberikan, cari assignment dengan role tersebut.
    Jika tidak, ambil assignment pertama.
    Return: {'valid': True, 'assignment': {...}} atau {'valid': False, 'msg': '...'}
    """
    assign_result = task_model.get_assignment_info_model(nik, sr_no)
    assignments = _parse_rows(assign_result)
    if not assignments:
        return {'valid': False, 'msg': 'Anda tidak ter-assign pada SR ini.'}

    if it_role_id:
        assignment = next((a for a in assignments if a['it_role_id'] == it_role_id), None)
        if not assignment:
            return {'valid': False, 'msg': f'Anda tidak memiliki role tersebut pada SR ini.'}
    else:
        assignment = assignments[0]

    return {'valid': True, 'assignment': assignment, 'msg': ''}


def get_tasks_trx(sr_no: str, nik: str) -> dict:
    """Ambil semua task pada SR untuk picrole user yang login."""
    try:
        access = _validate_pic_access(nik, sr_no)
        if not access['valid']:
            return {'status': False, 'data': [], 'msg': access['msg']}

        assignment = access['assignment']
        it_role_id = assignment['it_role_id']

        result = task_model.get_tasks_by_sr_and_role_model(sr_no, it_role_id)
        tasks = _parse_rows(result)

        return {'status': True, 'data': tasks}
    except Exception as e:
        Log.error(f'Exception | get_tasks_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def create_task_trx(sr_no: str, nik: str, data: dict) -> dict:
    """Buat task baru pada SR. Hanya PIC yang ter-assign. it_role_id wajib jika user punya >1 role."""
    try:
        it_role_id = data.get('it_role_id')
        if it_role_id:
            it_role_id = int(it_role_id)

        access = _validate_pic_access(nik, sr_no, it_role_id)
        if not access['valid']:
            return {'status': False, 'data': [], 'msg': access['msg']}

        assignment = access['assignment']
        assign_id = assignment['assign_id']

        task_detail = data.get('task_detail', '').strip()
        if not task_detail:
            return {'status': False, 'data': [], 'msg': 'Task detail tidak boleh kosong.'}

        target_date = data.get('target_date') or None
        actual_date = data.get('actual_date') or None

        result = task_model.create_task_model(assign_id, task_detail, target_date, actual_date)
        if not result.get('status'):
            return {'status': False, 'data': [], 'msg': result.get('msg', 'Gagal membuat task.')}

        return {'status': True, 'data': result.get('data', []), 'msg': 'Task berhasil dibuat.'}
    except Exception as e:
        Log.error(f'Exception | create_task_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def update_task_trx(task_id: int, nik: str, data: dict) -> dict:
    """Update task. Validasi: user harus punya picrole sama dengan task owner pada SR yang sama."""
    try:
        # 1. Ambil info task yang mau diupdate
        task_result = task_model.get_task_by_id_model(task_id)
        task_row = _parse_single_row(task_result)
        if not task_row:
            return {'status': False, 'data': [], 'msg': 'Task tidak ditemukan.'}

        sr_no = task_row['sr_no']
        task_it_role_id = task_row['it_role_id']

        # 2. Validasi user ter-assign pada SR ini dengan it_role yang sama
        access = _validate_pic_access(nik, sr_no)
        if not access['valid']:
            return {'status': False, 'data': [], 'msg': access['msg']}

        assignment = access['assignment']
        if assignment['it_role_id'] != task_it_role_id:
            return {'status': False, 'data': [], 'msg': 'Anda tidak memiliki akses untuk mengubah task ini.'}

        # 3. Update
        task_detail = data.get('task_detail', '').strip()
        if not task_detail:
            return {'status': False, 'data': [], 'msg': 'Task detail tidak boleh kosong.'}

        target_date = data.get('target_date') or None
        actual_date = data.get('actual_date') or None

        result = task_model.update_task_model(task_id, task_detail, target_date, actual_date)
        if not result.get('status'):
            return {'status': False, 'data': [], 'msg': result.get('msg', 'Gagal mengupdate task.')}

        return {'status': True, 'data': result.get('data', []), 'msg': 'Task berhasil diupdate.'}
    except Exception as e:
        Log.error(f'Exception | update_task_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def delete_task_trx(task_id: int, nik: str) -> dict:
    """Hapus task. Validasi: user harus punya picrole sama dengan task owner pada SR yang sama."""
    try:
        # 1. Ambil info task
        task_result = task_model.get_task_by_id_model(task_id)
        task_row = _parse_single_row(task_result)
        if not task_row:
            return {'status': False, 'data': [], 'msg': 'Task tidak ditemukan.'}

        sr_no = task_row['sr_no']
        task_it_role_id = task_row['it_role_id']

        # 2. Validasi akses
        access = _validate_pic_access(nik, sr_no)
        if not access['valid']:
            return {'status': False, 'data': [], 'msg': access['msg']}

        assignment = access['assignment']
        if assignment['it_role_id'] != task_it_role_id:
            return {'status': False, 'data': [], 'msg': 'Anda tidak memiliki akses untuk menghapus task ini.'}

        # 3. Delete
        result = task_model.delete_task_model(task_id)
        if not result.get('status'):
            return {'status': False, 'data': [], 'msg': 'Gagal menghapus task.'}

        return {'status': True, 'data': [], 'msg': 'Task berhasil dihapus.'}
    except Exception as e:
        Log.error(f'Exception | delete_task_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
