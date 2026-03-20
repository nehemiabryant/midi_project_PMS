from common.midiconnectserver.midilog import Logger
from ..models import assignment_model

Log = Logger()

# Constants dari model
ASSIGNABLE_PICROLE_IDS = assignment_model.ASSIGNABLE_PICROLE_IDS
STATUS_BACKLOG_SCRUM = assignment_model.STATUS_BACKLOG_SCRUM


def _parse_single_row(db_result: dict) -> dict | None:
    """Helper: parse selectDataHeader result ke single dict."""
    if not db_result.get('status'):
        return None
    raw = db_result.get('data', [[], []])
    if not raw or len(raw) < 2 or not raw[1]:
        return None
    return dict(zip(raw[0], raw[1][0]))


def _parse_rows(db_result: dict) -> list:
    """Helper: parse selectDataHeader/selectHeader result ke list of dicts."""
    if not db_result.get('status'):
        return []
    raw = db_result.get('data', [[], []])
    if not raw or len(raw) < 2 or not raw[1]:
        return []
    headers = raw[0]
    return [dict(zip(headers, row)) for row in raw[1]]


def get_assign_page_data_trx(sr_no: str, nik: str) -> dict:
    """
    Ambil semua data yang dibutuhkan halaman assignment.
    Validasi: user harus IT SM yang ter-assign pada SR ini.

    Return:
    - sr_detail: detail SR
    - picroles: list PIC roles yang bisa di-assign (SCM, DEV, QA, RO)
    - it_users: list user IT yang bisa di-assign
    - current_assignments: assignment yang sudah ada
    - is_locked: True jika assignment sudah di-submit (status != 105)
    """
    try:
        # 1. Validasi: user harus IT SM pada SR ini
        sm_result = assignment_model.get_sm_on_sr_model(sr_no, nik)
        sm_row = _parse_single_row(sm_result)
        if not sm_row:
            return {'status': False, 'data': [], 'msg': 'Anda bukan IT SM pada SR ini atau tidak memiliki akses.'}

        # 2. Ambil detail SR
        sr_result = assignment_model.get_sr_detail_with_status_model(sr_no)
        sr_detail = _parse_single_row(sr_result)
        if not sr_detail:
            return {'status': False, 'data': [], 'msg': 'SR tidak ditemukan.'}

        # 3. Tentukan apakah assignment sudah locked
        is_locked = sr_detail.get('smk_id') != STATUS_BACKLOG_SCRUM

        # 4. Ambil PIC roles yang bisa di-assign
        picroles_result = assignment_model.get_assignable_picroles_model()
        picroles = _parse_rows(picroles_result)

        # 5. Ambil daftar user IT
        users_result = assignment_model.get_it_users_model()
        it_users = _parse_rows(users_result)

        # 6. Ambil assignment yang sudah ada (hanya role 4,5,6,7)
        assignments_result = assignment_model.get_sr_assignments_model(sr_no, ASSIGNABLE_PICROLE_IDS)
        current_assignments = _parse_rows(assignments_result)

        return {
            'status': True,
            'data': {
                'sr_detail': sr_detail,
                'picroles': picroles,
                'it_users': it_users,
                'current_assignments': current_assignments,
                'is_locked': is_locked
            }
        }
    except Exception as e:
        Log.error(f'Exception | get_assign_page_data_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def submit_assignments_trx(sr_no: str, nik: str, form_data: dict) -> dict:
    """
    Submit assignment PIC pada SR.

    Validasi:
    1. User harus IT SM pada SR ini
    2. SR harus masih status BACKLOG SCRUM (105)
    3. Minimal 1 user per role (SCM, DEV, QA, RO)
    4. Semua NIK yang di-assign harus valid (ada di daftar IT users)

    form_data format dari HTML form:
    {
        'assign_user[]': ['nik1', 'nik2', 'nik3', ...],
        'assign_role[]': ['4', '5', '6', ...]
    }
    """
    try:
        # 1. Validasi: user harus IT SM pada SR ini
        sm_result = assignment_model.get_sm_on_sr_model(sr_no, nik)
        sm_row = _parse_single_row(sm_result)
        if not sm_row:
            return {'status': False, 'data': [], 'msg': 'Anda bukan IT SM pada SR ini.'}

        # 2. Validasi: SR harus masih BACKLOG SCRUM (105)
        sr_result = assignment_model.get_sr_detail_with_status_model(sr_no)
        sr_detail = _parse_single_row(sr_result)
        if not sr_detail:
            return {'status': False, 'data': [], 'msg': 'SR tidak ditemukan.'}
        if sr_detail.get('smk_id') != STATUS_BACKLOG_SCRUM:
            return {'status': False, 'data': [], 'msg': 'Assignment sudah dikunci. SR tidak lagi dalam status Backlog Scrum.'}

        # 3. Parse form: assign_user[] dan assign_role[] (paired by index)
        user_list = form_data.getlist('assign_user[]') if hasattr(form_data, 'getlist') else form_data.get('assign_user[]', [])
        role_list = form_data.getlist('assign_role[]') if hasattr(form_data, 'getlist') else form_data.get('assign_role[]', [])

        if isinstance(user_list, str):
            user_list = [user_list]
        if isinstance(role_list, str):
            role_list = [role_list]

        assignments = []
        for user_nik, role_id_str in zip(user_list, role_list):
            user_nik = user_nik.strip() if user_nik else ''
            role_id_str = role_id_str.strip() if role_id_str else ''
            if not user_nik or not role_id_str:
                continue
            assignments.append({'nik': user_nik, 'it_role_id': int(role_id_str)})

        if not assignments:
            return {'status': False, 'data': [], 'msg': 'Tidak ada assignment yang diisi.'}

        # 4. Validasi: minimal 1 user per role (SCM=4, DEV=5, QA=6, RO=7)
        role_names = {4: 'IT SCM', 5: 'IT DEV', 6: 'IT QA', 7: 'IT RO'}
        assigned_roles = {a['it_role_id'] for a in assignments}
        for it_role_id in ASSIGNABLE_PICROLE_IDS:
            if it_role_id not in assigned_roles:
                return {
                    'status': False, 'data': [],
                    'msg': f'Minimal 1 user harus di-assign untuk role {role_names.get(it_role_id, it_role_id)}.'
                }

        # 5. Validasi: semua NIK harus ada di daftar IT users
        users_result = assignment_model.get_it_users_model()
        it_users = _parse_rows(users_result)
        valid_niks = {u['nik'] for u in it_users}
        for a in assignments:
            if a['nik'] not in valid_niks:
                return {
                    'status': False, 'data': [],
                    'msg': f"NIK {a['nik']} tidak terdaftar sebagai User IT."
                }

        # 6. Insert assignments + update status (atomic)
        result = assignment_model.insert_assignments_and_update_status_model(sr_no, assignments, nik)
        return result

    except Exception as e:
        Log.error(f'Exception | submit_assignments_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
